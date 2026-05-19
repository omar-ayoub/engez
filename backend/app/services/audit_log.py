import uuid
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review_audit_log import ReviewAuditLog

logger = logging.getLogger(__name__)


async def create_audit_entry(
    db: AsyncSession,
    company_id: str,
    expense_id: str,
    actor_id: str,
    action_type: str,
    value_before: dict | None = None,
    value_after: dict | None = None,
    field_name: str | None = None,
    rejection_reason: str | None = None,
    bulk_operation_id: str | None = None,
) -> ReviewAuditLog:
    entry = ReviewAuditLog(
        id=str(uuid.uuid4()),
        company_id=company_id,
        expense_id=expense_id,
        actor_id=actor_id,
        action_type=action_type,
        field_name=field_name,
        value_before=value_before,
        value_after=value_after,
        rejection_reason=rejection_reason,
        bulk_operation_id=bulk_operation_id,
    )
    db.add(entry)
    await db.flush()
    return entry
