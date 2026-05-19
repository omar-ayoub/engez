import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expense import Expense
from app.models.project import Project
from app.models.category import Category

logger = logging.getLogger(__name__)


async def spend_by_project(db: AsyncSession, company_id: str, days: int = 30) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(
            Project.name,
            Project.name_ar,
            Project.budget,
            func.coalesce(func.sum(Expense.amount), 0).label("total_spend"),
            func.count(Expense.id).label("expense_count"),
        )
        .join(Expense, Expense.project_id == Project.id)
        .where(
            Expense.company_id == company_id,
            Expense.status == "approved",
            Expense.created_at >= since,
        )
        .group_by(Project.id, Project.name, Project.name_ar, Project.budget)
        .order_by(func.sum(Expense.amount).desc())
    )
    return [
        {
            "name": row.name,
            "name_ar": row.name_ar,
            "budget": float(row.budget) if row.budget else None,
            "total_spend": float(row.total_spend),
            "expense_count": row.expense_count,
        }
        for row in result.all()
    ]


async def spend_by_category(db: AsyncSession, company_id: str, days: int = 30) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(
            Category.id,
            Category.name,
            Category.name_ar,
            func.coalesce(func.sum(Expense.amount), 0).label("total"),
            func.count(Expense.id).label("count"),
        )
        .join(Expense, Expense.category_id == Category.id)
        .where(
            Expense.company_id == company_id,
            Expense.status == "approved",
            Expense.created_at >= since,
        )
        .group_by(Category.id, Category.name, Category.name_ar)
        .order_by(func.sum(Expense.amount).desc())
    )
    return [
        {
            "category": row.name,
            "category_ar": row.name_ar,
            "total": float(row.total),
            "count": row.count,
        }
        for row in result.all()
    ]


async def spend_trend(db: AsyncSession, company_id: str, days: int = 90) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(Expense.created_at, Expense.amount)
        .where(
            Expense.company_id == company_id,
            Expense.status == "approved",
            Expense.created_at >= since,
        )
        .order_by(Expense.created_at)
    )

    # Group by ISO week in Python (avoids PostgreSQL-only date_trunc)
    weekly: dict[str, dict] = defaultdict(lambda: {"total": 0.0, "count": 0})
    for row in result.all():
        dt = row.created_at
        if dt is None:
            continue
        # Monday-based week start
        week_start = dt - timedelta(days=dt.weekday())
        key = week_start.strftime("%Y-%m-%d")
        weekly[key]["total"] += float(row.amount)
        weekly[key]["count"] += 1

    return [
        {"week": week, "total": round(data["total"], 2), "count": data["count"]}
        for week, data in sorted(weekly.items())
    ]


async def budget_vs_actual(db: AsyncSession, company_id: str) -> list[dict]:
    result = await db.execute(
        select(
            Project.name,
            Project.name_ar,
            Project.budget,
            func.coalesce(func.sum(Expense.amount), 0).label("actual_spend"),
        )
        .join(Expense, Expense.project_id == Project.id)
        .where(
            Expense.company_id == company_id,
            Expense.status == "approved",
            Project.is_active.is_(True),
            Project.budget.isnot(None),
        )
        .group_by(Project.id, Project.name, Project.name_ar, Project.budget)
        .order_by(Project.name_ar)
    )
    return [
        {
            "name": row.name,
            "name_ar": row.name_ar,
            "budget": float(row.budget) if row.budget else None,
            "actual_spend": float(row.actual_spend),
        }
        for row in result.all()
    ]


async def summary(db: AsyncSession, company_id: str, days: int = 30) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(
            func.coalesce(func.sum(Expense.amount), 0).label("total_spend"),
            func.count(Expense.id).label("expense_count"),
        )
        .where(
            Expense.company_id == company_id,
            Expense.status == "approved",
            Expense.created_at >= since,
        )
    )
    row = result.one()

    project_result = await db.execute(
        select(func.count())
        .select_from(Project)
        .where(Project.company_id == company_id, Project.is_active.is_(True))
    )
    project_count = project_result.scalar() or 0

    return {
        "total_spend": float(row.total_spend),
        "expense_count": row.expense_count,
        "project_count": project_count,
        "period_days": days,
    }
