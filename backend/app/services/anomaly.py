import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.expense import Expense

logger = logging.getLogger(__name__)


@dataclass
class AnomalyInput:
    amount: float
    company_id: str
    user_id: str | None = None
    category_id: str | None = None
    vendor: str | None = None
    receipt_hash: str | None = None
    check_velocity: bool = True
    exclude_id: str | None = None


async def score(db: AsyncSession, inp: AnomalyInput) -> dict:
    flags: dict = {}

    if inp.receipt_hash:
        dup = await _check_duplicate_receipt(db, inp.company_id, inp.receipt_hash, exclude_id=inp.exclude_id)
        if dup:
            flags["duplicate_receipt"] = dup

    if inp.category_id and inp.user_id:
        outlier = await _check_statistical_outlier(
            db, inp.company_id, inp.user_id, inp.category_id, inp.amount,
            exclude_id=inp.exclude_id,
        )
        if outlier:
            flags["statistical_outlier"] = outlier

    if inp.check_velocity and inp.user_id:
        velocity = await _check_submission_velocity(db, inp.company_id, inp.user_id, exclude_id=inp.exclude_id)
        if velocity:
            flags["high_velocity"] = velocity

    if inp.vendor and inp.category_id:
        mismatch = await _check_vendor_category_mismatch(
            db, inp.company_id, inp.vendor, inp.category_id, exclude_id=inp.exclude_id,
        )
        if mismatch:
            flags["vendor_mismatch"] = mismatch

    return flags


async def check_anomalies_from_request(
    db: AsyncSession,
    data,
    company_id: str,
) -> list[dict]:
    inp = AnomalyInput(
        amount=data.amount,
        company_id=company_id,
        user_id=getattr(data, "user_id", None),
        category_id=getattr(data, "category_id", None),
        vendor=getattr(data, "vendor", None),
        receipt_hash=getattr(data, "receipt_hash", None),
        check_velocity=getattr(data, "check_velocity", False),
    )
    flags = await score(db, inp)
    return list(flags.values())


async def detect_anomalies(
    db: AsyncSession,
    expense_id: str,
    company_id: str,
) -> dict:
    result = await db.execute(
        select(Expense).where(Expense.id == expense_id, Expense.company_id == company_id)
    )
    expense = result.scalar_one_or_none()
    if not expense:
        return {}

    inp = AnomalyInput(
        amount=float(expense.amount),
        company_id=company_id,
        user_id=expense.user_id,
        category_id=expense.category_id,
        vendor=expense.vendor,
        receipt_hash=getattr(expense, "receipt_hash", None),
        check_velocity=True,
        exclude_id=expense.id,
    )
    flags = await score(db, inp)

    if flags:
        expense.anomaly_flags = flags
        await db.commit()
        logger.info("Expense %s flagged with %d anomalies", expense_id, len(flags))

    return flags


async def _check_duplicate_receipt(
    db: AsyncSession, company_id: str, receipt_hash: str, *, exclude_id: str | None = None
) -> dict | None:
    query = select(Expense).where(
        Expense.company_id == company_id,
        Expense.receipt_hash == receipt_hash,
    ).limit(1)
    if exclude_id:
        query = query.where(Expense.id != exclude_id)

    result = await db.execute(query)
    similar = result.scalar_one_or_none()
    if not similar:
        return None

    return {
        "type": "duplicate_receipt",
        "severity": "high",
        "message": "صورة إيصال مشابهة تم إرسالها سابقاً",
        "message_en": "Similar receipt image previously submitted",
        "metadata": {
            "similar_expense_id": similar.id,
            "similarity": 0.95,
        },
    }


async def _check_statistical_outlier(
    db: AsyncSession,
    company_id: str,
    user_id: str,
    category_id: str,
    amount: float,
    *,
    exclude_id: str | None = None,
) -> dict | None:
    query = select(
        func.avg(Expense.amount).label("avg"),
        func.count().label("cnt"),
    ).where(
        Expense.company_id == company_id,
        Expense.user_id == user_id,
        Expense.category_id == category_id,
        Expense.status.in_(["approved", "pending"]),
    )
    if exclude_id:
        query = query.where(Expense.id != exclude_id)

    result = await db.execute(query)
    row = result.one()
    if not row or not row.cnt or row.cnt < 5:
        return None

    avg_val = float(row.avg or 0)

    amounts_q = select(Expense.amount).where(
        Expense.company_id == company_id,
        Expense.user_id == user_id,
        Expense.category_id == category_id,
        Expense.status.in_(["approved", "pending"]),
    )
    if exclude_id:
        amounts_q = amounts_q.where(Expense.id != exclude_id)
    amounts_result = await db.execute(amounts_q)
    values = [float(r[0]) for r in amounts_result.all()]

    n = len(values)
    if n < 2:
        return None
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / (n - 1)
    std_val = variance ** 0.5

    if std_val == 0:
        return None

    if amount > avg_val + 2 * std_val:
        return {
            "type": "statistical_outlier",
            "severity": "medium",
            "message": "المبلغ أعلى بكثير من المعتاد لهذه الفئة",
            "message_en": "Amount significantly above average for this category",
            "metadata": {
                "avg": round(avg_val, 2),
                "std": round(std_val, 2),
            },
        }
    return None


async def _check_submission_velocity(
    db: AsyncSession,
    company_id: str,
    user_id: str,
    *,
    exclude_id: str | None = None,
) -> dict | None:
    ten_min_ago = datetime.now(timezone.utc) - timedelta(minutes=10)
    query = select(func.count()).select_from(Expense).where(
        Expense.company_id == company_id,
        Expense.user_id == user_id,
        Expense.created_at >= ten_min_ago,
    )
    if exclude_id:
        query = query.where(Expense.id != exclude_id)

    result = await db.execute(query)
    count = result.scalar() or 0
    if count >= 3:
        return {
            "type": "high_velocity",
            "severity": "medium",
            "message": f"{count + 1} مصروفات في آخر 10 دقائق",
            "message_en": f"{count + 1} expenses in last 10 minutes",
            "metadata": {},
        }
    return None


async def _check_vendor_category_mismatch(
    db: AsyncSession,
    company_id: str,
    vendor: str,
    category_id: str,
    *,
    exclude_id: str | None = None,
) -> dict | None:
    query = (
        select(Expense.category_id, func.count().label("cnt"))
        .where(
            Expense.company_id == company_id,
            Expense.vendor == vendor,
        )
        .group_by(Expense.category_id)
        .order_by(func.count().desc())
    )
    if exclude_id:
        query = query.where(Expense.id != exclude_id)

    result = await db.execute(query)
    rows = result.all()
    if not rows:
        return None

    total = sum(r.cnt for r in rows)
    if total < 3:
        return None

    top_category = rows[0].category_id
    top_ratio = rows[0].cnt / total
    if top_ratio >= settings.BULK_APPROVE_CONFIDENCE_THRESHOLD and top_category != category_id:
        return {
            "type": "vendor_mismatch",
            "severity": "low",
            "message": "هذا المورد عادة في فئة مختلفة",
            "message_en": "This vendor is usually in a different category",
            "metadata": {
                "expected_category": top_category,
                "actual_category": category_id,
            },
        }
    return None


async def get_anomaly_metrics(db: AsyncSession, company_id: str, days: int = 30) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)

    total_result = await db.execute(
        select(func.count()).select_from(Expense).where(
            Expense.company_id == company_id,
            Expense.anomaly_flags.isnot(None),
            Expense.created_at >= since,
        )
    )
    flagged = total_result.scalar() or 0

    expenses_result = await db.execute(
        select(func.count()).select_from(Expense).where(
            Expense.company_id == company_id,
            Expense.created_at >= since,
        )
    )
    total_expenses = expenses_result.scalar() or 1

    type_counts: dict[str, int] = {
        "duplicate_receipt": 0,
        "statistical_outlier": 0,
        "high_velocity": 0,
        "vendor_mismatch": 0,
    }

    flagged_result = await db.execute(
        select(Expense.anomaly_flags).where(
            Expense.company_id == company_id,
            Expense.anomaly_flags.isnot(None),
            Expense.created_at >= since,
        )
    )
    total_flags = 0
    for (flags,) in flagged_result.all():
        if isinstance(flags, dict):
            for key in flags:
                if key in type_counts:
                    type_counts[key] += 1
                total_flags += 1

    rejected_result = await db.execute(
        select(func.count()).select_from(Expense).where(
            Expense.company_id == company_id,
            Expense.status == "rejected",
            Expense.anomaly_flags.isnot(None),
            Expense.created_at >= since,
        )
    )
    rejected_flagged = rejected_result.scalar() or 0

    rejection_correlation = round(rejected_flagged / flagged, 2) if flagged > 0 else 0.0

    return {
        "total_flags": total_flags,
        "by_type": type_counts,
        "avg_flags_per_expense": round(total_flags / total_expenses, 2) if total_expenses > 0 else 0.0,
        "rejection_correlation": rejection_correlation,
        "period_days": days,
    }
