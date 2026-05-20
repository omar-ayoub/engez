import math
import logging
from datetime import datetime

from sqlalchemy import func, select, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.expense import Expense
from app.models.user import User
from app.models.project import Project
from app.schemas.review import (
    ConfidenceSummarySchema,
    ReviewQueueItemSchema,
    ReviewQueueEmployee,
    ReviewQueueProject,
)

logger = logging.getLogger(__name__)


def _compute_confidence_summary(ai_confidence: dict | None) -> ConfidenceSummarySchema | None:
    if not ai_confidence:
        return None
    values = [v for v in ai_confidence.values() if isinstance(v, (int, float))]
    if not values:
        return None
    min_val = min(values)
    threshold = settings.BULK_APPROVE_CONFIDENCE_THRESHOLD
    return ConfidenceSummarySchema(
        min=round(min_val, 4),
        all_high=min_val >= threshold,
        low_count=sum(1 for v in values if v < threshold),
        fields={k: round(v, 4) for k, v in ai_confidence.items() if isinstance(v, (int, float))},
    )


def _count_anomalies(anomaly_flags: dict | None) -> int:
    if not anomaly_flags:
        return 0
    return len(anomaly_flags)


def _is_bulk_eligible(expense: Expense) -> bool:
    threshold = settings.BULK_APPROVE_CONFIDENCE_THRESHOLD
    if not expense.eta_verified:
        return False
    if expense.status != "pending":
        return False
    conf = expense.ai_confidence
    if not conf:
        return False
    values = [v for v in conf.values() if isinstance(v, (int, float))]
    if not values:
        return False
    return all(v >= threshold for v in values)


def _build_queue_item(expense: Expense, employee: User, project: Project | None) -> ReviewQueueItemSchema:
    return ReviewQueueItemSchema(
        id=expense.id,
        review_version=expense.review_version,
        status=expense.status,
        amount=float(expense.amount),
        currency=expense.currency,
        vendor=expense.vendor,
        employee=ReviewQueueEmployee(
            id=employee.id,
            name=employee.name,
            name_ar=employee.name_ar,
        ),
        project=ReviewQueueProject(
            id=project.id,
            name=project.name,
            name_ar=project.name_ar,
            code=project.code,
        ) if project else None,
        capture_mode=expense.capture_mode,
        created_at=expense.created_at,
        eta_verified=expense.eta_verified,
        confidence_summary=_compute_confidence_summary(expense.ai_confidence),
        anomaly_count=_count_anomalies(expense.anomaly_flags),
        bulk_eligible=_is_bulk_eligible(expense),
    )


async def get_review_queue(
    db: AsyncSession,
    company_id: str,
    status_filter: str | None = None,
    project_id: str | None = None,
    employee_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    amount_min: float | None = None,
    amount_max: float | None = None,
    sort_by: str = "date",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[ReviewQueueItemSchema], int, int]:
    query = select(Expense).where(Expense.company_id == company_id)
    count_query = select(func.count()).select_from(Expense).where(Expense.company_id == company_id)

    if status_filter and status_filter != "all":
        query = query.where(Expense.status == status_filter)
        count_query = count_query.where(Expense.status == status_filter)
    if project_id:
        query = query.where(Expense.project_id == project_id)
        count_query = count_query.where(Expense.project_id == project_id)
    if employee_id:
        query = query.where(Expense.user_id == employee_id)
        count_query = count_query.where(Expense.user_id == employee_id)
    if date_from:
        query = query.where(Expense.created_at >= date_from)
        count_query = count_query.where(Expense.created_at >= date_from)
    if date_to:
        query = query.where(Expense.created_at <= date_to)
        count_query = count_query.where(Expense.created_at <= date_to)
    if amount_min is not None:
        query = query.where(Expense.amount >= amount_min)
        count_query = count_query.where(Expense.amount >= amount_min)
    if amount_max is not None:
        query = query.where(Expense.amount <= amount_max)
        count_query = count_query.where(Expense.amount <= amount_max)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    pages = math.ceil(total / page_size) if total > 0 else 1

    sort_col = Expense.created_at
    join_project = False
    if sort_by == "amount":
        sort_col = Expense.amount
    elif sort_by == "project":
        join_project = True

    order_func = desc if sort_order == "desc" else asc

    if join_project:
        query = query.join(Project, Expense.project_id == Project.id, isouter=True)
        query = query.order_by(
            order_func(Project.name_ar),
            order_func(Expense.created_at),
        )
    else:
        query = query.order_by(order_func(sort_col))

    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    expenses = result.scalars().all()

    user_ids = list({e.user_id for e in expenses})
    project_ids = list({e.project_id for e in expenses if e.project_id})

    users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
    users_map = {u.id: u for u in users_result.scalars().all()}

    projects_map: dict[str, Project] = {}
    if project_ids:
        projects_result = await db.execute(select(Project).where(Project.id.in_(project_ids)))
        projects_map = {p.id: p for p in projects_result.scalars().all()}

    items = []
    for expense in expenses:
        employee = users_map.get(expense.user_id)
        if not employee:
            continue

        project = projects_map.get(expense.project_id) if expense.project_id else None

        items.append(_build_queue_item(expense, employee, project))

    return items, total, pages


async def get_review_detail(
    db: AsyncSession,
    company_id: str,
    expense_id: str,
) -> Expense | None:
    result = await db.execute(
        select(Expense).where(
            Expense.id == expense_id,
            Expense.company_id == company_id,
        )
    )
    return result.scalar_one_or_none()


async def get_next_pending_id(
    db: AsyncSession,
    company_id: str,
    current_expense_id: str,
) -> str | None:
    from sqlalchemy import select

    result = await db.execute(
        select(Expense.id)
        .where(
            Expense.company_id == company_id,
            Expense.status == "pending",
            Expense.id != current_expense_id,
        )
        .order_by(Expense.created_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return row if row else None
