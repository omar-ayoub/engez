import uuid
import logging
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.expense import Expense
from app.models.correction import CorrectionFeedback
from app.models.review_audit_log import ReviewAuditLog
from app.services.review_queue import get_review_detail, get_next_pending_id

logger = logging.getLogger(__name__)

ALLOWED_CORRECT_FIELDS = {"amount", "currency", "vendor", "vendor_tax_reg", "items", "category_id", "project_id", "notes"}
ALLOWED_RESUBMIT_FIELDS = ALLOWED_CORRECT_FIELDS | {"receipt_url"}


class ReviewConflictError(Exception):
    def __init__(self, current_version: int, current_status: str):
        self.current_version = current_version
        self.current_status = current_status


class ReviewNotFoundError(Exception):
    pass


class ReviewFieldNotAllowedError(Exception):
    def __init__(self, field_name: str):
        self.field_name = field_name


class ReviewNotRejectedError(Exception):
    pass


class ReviewNotAuthorizedError(Exception):
    pass


async def _atomic_status_check(
    db: AsyncSession, company_id: str, expense_id: str,
    expected_version: int, expected_status: str = "pending",
) -> Expense:
    result = await db.execute(
        update(Expense)
        .where(
            Expense.id == expense_id,
            Expense.company_id == company_id,
            Expense.status == expected_status,
            Expense.review_version == expected_version,
        )
        .values(review_version=Expense.review_version + 1)
        .returning(Expense.id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        expense = await get_review_detail(db, company_id, expense_id)
        if not expense:
            raise ReviewNotFoundError()
        raise ReviewConflictError(expense.review_version, expense.status)
    await db.flush()
    expense = await get_review_detail(db, company_id, expense_id)
    return expense


def _create_audit(
    company_id: str, expense_id: str, actor_id: str,
    action_type: str, **kwargs,
) -> ReviewAuditLog:
    return ReviewAuditLog(
        company_id=company_id,
        expense_id=expense_id,
        actor_id=actor_id,
        action_type=action_type,
        **kwargs,
    )


async def approve(
    db: AsyncSession, company_id: str, expense_id: str,
    reviewer_id: str, review_version: int,
) -> tuple[Expense, str | None]:
    expense = await _atomic_status_check(db, company_id, expense_id, review_version, "pending")
    expense.status = "approved"
    expense.reviewed_by = reviewer_id
    expense.reviewed_at = datetime.now(timezone.utc)

    db.add(_create_audit(
        company_id, expense.id, reviewer_id, "approve",
        value_before={"status": "pending"},
        value_after={"status": "approved"},
    ))
    await db.commit()
    await db.refresh(expense)

    next_id = await get_next_pending_id(db, company_id, expense_id)
    return expense, next_id


async def reject(
    db: AsyncSession, company_id: str, expense_id: str,
    reviewer_id: str, review_version: int, reason: str,
) -> tuple[Expense, str | None]:
    expense = await _atomic_status_check(db, company_id, expense_id, review_version, "pending")
    expense.status = "rejected"
    expense.rejection_reason = reason
    expense.reviewed_by = reviewer_id
    expense.reviewed_at = datetime.now(timezone.utc)

    db.add(_create_audit(
        company_id, expense.id, reviewer_id, "reject",
        rejection_reason=reason,
        value_before={"status": "pending"},
        value_after={"status": "rejected"},
    ))
    await db.commit()
    await db.refresh(expense)

    next_id = await get_next_pending_id(db, company_id, expense.id)
    return expense, next_id


async def correct(
    db: AsyncSession, company_id: str, expense_id: str,
    reviewer_id: str, review_version: int,
    field_name: str, corrected_value: str | float,
) -> dict:
    if field_name not in ALLOWED_CORRECT_FIELDS:
        raise ReviewFieldNotAllowedError(field_name)

    expense = await _atomic_status_check(db, company_id, expense_id, review_version, "pending")

    old_value = getattr(expense, field_name, None)
    old_str = str(old_value) if old_value is not None else ""
    new_str = str(corrected_value)

    setattr(expense, field_name, corrected_value)

    feedback_created = False
    feedback_id = None

    ai_extraction = expense.ai_extraction or {}
    ai_val = ai_extraction.get(field_name)
    if ai_val is not None and str(ai_val) != new_str:
        feedback = CorrectionFeedback(
            expense_id=expense.id,
            company_id=company_id,
            field_name=field_name,
            ai_value=str(ai_val),
            corrected_value=new_str,
            corrected_by=reviewer_id,
        )
        db.add(feedback)
        await db.flush()
        feedback_created = True
        feedback_id = feedback.id

    db.add(_create_audit(
        company_id, expense.id, reviewer_id, "correct",
        field_name=field_name,
        value_before={field_name: old_str},
        value_after={field_name: new_str},
    ))
    await db.commit()
    await db.refresh(expense)

    return {
        "expense": expense,
        "field_name": field_name,
        "value_before": old_str,
        "value_after": new_str,
        "correction_feedback_created": feedback_created,
        "correction_feedback_id": feedback_id,
    }


def _is_bulk_eligible(expense: Expense) -> bool:
    threshold = settings.BULK_APPROVE_CONFIDENCE_THRESHOLD
    if not expense.eta_verified or expense.status != "pending":
        return False
    conf = expense.ai_confidence
    if not conf:
        return False
    values = [v for v in conf.values() if isinstance(v, (int, float))]
    if not values:
        return False
    return all(v >= threshold for v in values)


async def bulk_approve(
    db: AsyncSession, company_id: str, reviewer_id: str,
    items: list[dict],
) -> dict:
    bulk_op_id = str(uuid.uuid4())
    approved_ids: list[str] = []
    skipped: list[dict] = []
    conflicts: list[dict] = []

    for item in items[:50]:
        result = await db.execute(
            select(Expense).where(Expense.id == item["id"], Expense.company_id == company_id)
        )
        expense = result.scalar_one_or_none()

        if not expense:
            skipped.append({"id": item["id"], "reason": "not_found"})
            continue
        if expense.status != "pending":
            skipped.append({"id": item["id"], "reason": "not_pending"})
            continue
        if expense.review_version != item["review_version"]:
            conflicts.append({"id": item["id"], "reason": "stale_version"})
            continue
        if not _is_bulk_eligible(expense):
            skipped.append({"id": item["id"], "reason": "not_eligible"})
            continue

        atomic = await db.execute(
            update(Expense)
            .where(
                Expense.id == expense.id,
                Expense.company_id == company_id,
                Expense.status == "pending",
                Expense.review_version == item["review_version"],
            )
            .values(
                status="approved",
                review_version=Expense.review_version + 1,
                reviewed_by=reviewer_id,
                reviewed_at=datetime.now(timezone.utc),
            )
            .returning(Expense.id)
        )
        if atomic.scalar_one_or_none() is None:
            conflicts.append({"id": item["id"], "reason": "stale_version"})
            continue

        db.add(_create_audit(
            company_id, expense.id, reviewer_id, "bulk_approve",
            bulk_operation_id=bulk_op_id,
            value_before={"status": "pending"},
            value_after={"status": "approved"},
        ))
        approved_ids.append(expense.id)

    await db.commit()
    return {
        "bulk_operation_id": bulk_op_id,
        "approved_ids": approved_ids,
        "skipped": skipped,
        "conflicts": conflicts,
    }


async def resubmit(
    db: AsyncSession, company_id: str, expense_id: str,
    user_id: str, user_role: str, review_version: int,
    changes: dict[str, str | float] | None = None,
) -> Expense:
    expense = await get_review_detail(db, company_id, expense_id)
    if not expense:
        raise ReviewNotFoundError()
    if expense.status != "rejected":
        raise ReviewNotRejectedError()
    if str(expense.user_id) != str(user_id) and user_role != "admin":
        raise ReviewNotAuthorizedError()
    if expense.review_version != review_version:
        raise ReviewConflictError(expense.review_version, expense.status)

    if changes:
        for field, value in changes.items():
            if hasattr(expense, field) and field in ALLOWED_RESUBMIT_FIELDS:
                setattr(expense, field, value)

    expense.status = "pending"
    expense.review_version += 1
    expense.reviewed_by = None
    expense.reviewed_at = None
    expense.rejection_reason = None

    db.add(_create_audit(
        company_id, expense.id, user_id, "resubmit",
        value_before={"status": "rejected"},
        value_after={"status": "pending"},
    ))
    await db.commit()
    await db.refresh(expense)
    return expense
