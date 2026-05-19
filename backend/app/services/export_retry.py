import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration import IntegrationConfig
from app.services.export_orchestrator import retry_failed_exports

logger = logging.getLogger(__name__)


async def run_retry_task() -> int:
    from app.core.database import async_session_factory
    try:
        async with async_session_factory() as db:
            count = await retry_failed_exports(db)
            if count > 0:
                logger.info("Retried %d failed exports", count)
            return count
    except Exception as exc:
        logger.error("Retry task failed: %s", exc)
        return 0


async def handle_credential_expiry(db: AsyncSession, company_id: str) -> None:
    result = await db.execute(
        select(IntegrationConfig).where(IntegrationConfig.company_id == company_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        return

    config.status = "needs_reauth"
    config.last_error = "Credential expired or revoked"
    await db.commit()

    try:
        from app.models.user import User
        admin_result = await db.execute(
            select(User).where(
                User.company_id == company_id,
                User.role == "admin",
                User.is_active.is_(True),
            )
        )
        admins = admin_result.scalars().all()
        for admin in admins:
            if admin.push_subscription:
                from app.services.push_notifications import _deliver_push
                await _deliver_push(admin.push_subscription, {
                    "type": "integration_needs_reauth",
                    "title": "يحتاج ربط النظام لإعادة مصادقة",
                    "body": f"ربط {config.system_name} يحتاج إعادة تسجيل الدخول",
                    "url": "/settings/integrations",
                })
    except Exception:
        pass
