import uuid
import logging
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration import IntegrationConfig
from app.models.export_record import ExportRecord
from app.services.exporters import get_exporter

logger = logging.getLogger(__name__)

MAX_RETRIES = 5
BACKOFF_DELAYS = [60, 300, 1800, 7200, 43200]


async def trigger_export(db: AsyncSession, expense_id: str, company_id: str) -> ExportRecord | None:
    config_result = await db.execute(
        select(IntegrationConfig).where(
            IntegrationConfig.company_id == company_id,
            IntegrationConfig.status == "active",
        )
    )
    config = config_result.scalar_one_or_none()
    if not config:
        logger.info("No active integration for company %s, skipping export", company_id)
        return None

    existing = await db.execute(
        select(ExportRecord).where(
            ExportRecord.expense_id == expense_id,
            ExportRecord.system_name == config.system_name,
            ExportRecord.status.in_(["pending", "success"]),
        )
    )
    if existing.scalar_one_or_none():
        logger.info("Export already exists for expense %s", expense_id)
        return None

    record = ExportRecord(
        id=str(uuid.uuid4()),
        company_id=company_id,
        expense_id=expense_id,
        system_name=config.system_name,
        status="pending",
        attempt_count=0,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    await _execute_export(db, record, config)
    return record


async def _execute_export(db: AsyncSession, record: ExportRecord, config: IntegrationConfig) -> None:
    exporter = get_exporter(record.system_name)
    if not exporter:
        record.status = "failed"
        record.error_message = f"Unknown exporter: {record.system_name}"
        await db.commit()
        return

    try:
        record.attempt_count += 1
        external_ref = await exporter.push(db, record.expense_id, record.company_id)
        record.status = "success"
        record.external_ref_id = external_ref
        config.last_sync_at = datetime.now(timezone.utc)
        config.last_error = None
        await db.commit()
        logger.info("Export %s succeeded: %s", record.id, external_ref)
    except Exception as exc:
        logger.warning("Export %s failed (attempt %d): %s", record.id, record.attempt_count, exc)
        record.error_message = str(exc)[:1000]

        record.status = "failed"
        if record.attempt_count >= MAX_RETRIES:
            record.next_retry_at = None
        else:
            delay = BACKOFF_DELAYS[min(record.attempt_count - 1, len(BACKOFF_DELAYS) - 1)]
            jitter = random.randint(0, delay // 4)
            record.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=delay + jitter)
            config.last_error = str(exc)[:500]

        await db.commit()


async def retry_failed_exports(db: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(ExportRecord).where(
            ExportRecord.status == "failed",
            ExportRecord.next_retry_at <= now,
            ExportRecord.attempt_count < MAX_RETRIES,
        )
    )
    records = result.scalars().all()
    count = 0
    for record in records:
        config_result = await db.execute(
            select(IntegrationConfig).where(IntegrationConfig.company_id == record.company_id)
        )
        config = config_result.scalar_one_or_none()
        if config and config.status == "active":
            await _execute_export(db, record, config)
            count += 1
    return count


async def cancel_pending_exports(db: AsyncSession, company_id: str, system_name: str) -> int:
    result = await db.execute(
        select(ExportRecord).where(
            ExportRecord.company_id == company_id,
            ExportRecord.system_name == system_name,
            ExportRecord.status == "pending",
        )
    )
    records = result.scalars().all()
    for record in records:
        record.status = "cancelled_migration"
        record.next_retry_at = None
    await db.commit()
    return len(records)
