import logging
import json
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)


async def send_decision_notification(
    db: AsyncSession,
    company_id: str,
    user_id: str,
    expense_id: str,
    decision: str,
    amount: float,
    currency: str = "EGP",
    reason: str | None = None,
) -> None:
    if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
        logger.warning("VAPID not configured, skipping push notification")
        return

    result = await db.execute(
        select(User).where(User.id == user_id, User.company_id == company_id)
    )
    user = result.scalar_one_or_none()
    if not user or not user.push_subscription:
        return

    title = "تمت الموافقة على المصروف" if decision == "approved" else "تم رفض المصروف"
    body_text = f"{currency} {amount:,.2f}"
    if decision == "approved":
        body_text = f"{body_text} تمت الموافقة"
    else:
        body_text = f"{body_text} مرفوض"
        if reason:
            body_text = f"{body_text}: {reason}"

    payload = {
        "type": "expense_decision",
        "expense_id": expense_id,
        "status": decision,
        "title": title,
        "body": body_text,
        "url": "/",
    }

    try:
        await _deliver_push(user.push_subscription, payload)
    except Exception as exc:
        await _handle_delivery_failure(db, user, exc)


async def send_batched_accountant_notification(
    db: AsyncSession,
    company_id: str,
    count: int,
) -> None:
    if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
        return

    result = await db.execute(
        select(User).where(
            User.company_id == company_id,
            User.role.in_(["accountant", "admin"]),
            User.is_active == True,
            User.push_subscription.isnot(None),
        )
    )
    accountants = result.scalars().all()

    payload = {
        "type": "review_queue_batch",
        "count": count,
        "title": "مصروفات بانتظار المراجعة",
        "body": f"{count} مصروفات جديدة بانتظار المراجعة",
        "url": "/review",
    }

    for accountant in accountants:
        try:
            await _deliver_push(accountant.push_subscription, payload)
        except Exception as exc:
            await _handle_delivery_failure(db, accountant, exc)


async def send_decision_notification_by_expense(
    db: AsyncSession,
    company_id: str,
    expense_id: str,
    decision: str,
) -> None:
    from app.models.expense import Expense

    result = await db.execute(select(Expense).where(Expense.id == expense_id, Expense.company_id == company_id))
    expense = result.scalar_one_or_none()
    if expense:
        await send_decision_notification(
            db, company_id, expense.user_id, expense.id,
            decision, float(expense.amount), expense.currency,
        )


async def _deliver_push(subscription: dict, payload: dict) -> None:
    try:
        from pywebpush import webpush

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: webpush(
                subscription_info={
                    "endpoint": subscription.get("endpoint", ""),
                    "keys": subscription.get("keys", {}),
                },
                data=json.dumps(payload),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": f"mailto:{settings.VAPID_CLAIMS_EMAIL}"},
            ),
        )
    except Exception as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        if status_code in (404, 410):
            raise PushSubscriptionInvalid(str(exc))
        if status_code == 400:
            raise PushSubscriptionInvalid(str(exc))
        raise


async def _handle_delivery_failure(db: AsyncSession, user: User, exc: Exception) -> None:
    if isinstance(exc, PushSubscriptionInvalid):
        logger.warning("Clearing invalid push subscription for user %s", user.id)
        user.push_subscription = None
        await db.commit()
    else:
        logger.warning("Push delivery failed for user %s: %s", user.id, exc)


class PushSubscriptionInvalid(Exception):
    pass
