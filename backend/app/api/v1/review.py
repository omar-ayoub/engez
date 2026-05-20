from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import (
    get_current_active_user,
    get_tenant_scope,
    require_accountant_or_admin,
    require_admin,
)
from app.core.tenant import TenantScope
from app.models.expense import Expense
from app.models.review_audit_log import ReviewAuditLog
from app.models.user import User
from app.schemas.review import (
    ReviewQueueResponse,
    ReviewDetailResponse,
    ReviewQueueEmployee,
    ETAInfoSchema,
    AuditHistoryItemSchema,
    ReceiptUrlResponse,
    ApproveRequest,
    ApproveResponse,
    RejectRequest,
    RejectResponse,
    CorrectExpenseRequest,
    CorrectExpenseResponse,
    BulkApproveRequest,
    BulkApproveResponse,
    BulkSkippedItem,
    BulkConflictItem,
    ResubmitRequest,
    ResubmitResponse,
    AiMetricsResponse,
    CorrectionFieldMetricSchema,
    DailyCorrectionTrendSchema,
)
from app.services.review_queue import get_review_queue, get_review_detail, get_next_pending_id
from app.services.review_actions import (
    approve as approve_action,
    reject as reject_action,
    correct as correct_action,
    bulk_approve as bulk_approve_action,
    resubmit as resubmit_action,
    ReviewConflictError,
    ReviewNotFoundError,
    ReviewFieldNotAllowedError,
    ReviewNotRejectedError,
    ReviewNotAuthorizedError,
)
from app.services.r2_storage import refresh_receipt_signed_url
from app.services.background import run_background
from app.services.push_notifications import send_decision_notification, send_decision_notification_by_expense, send_batched_accountant_notification
from app.services.export_orchestrator import trigger_export

router = APIRouter(prefix="/expenses", tags=["review"])

VALID_QUEUE_STATUSES = ("pending", "approved", "rejected", "all")
VALID_SORT_BY = ("date", "amount", "project")
VALID_SORT_ORDER = ("asc", "desc")


def _parse_date_or_raise(value: str, field_name: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"detail": f"تاريخ غير صالح: {field_name}", "detail_en": f"Invalid date for {field_name}"},
        )


@router.get("/queue", response_model=ReviewQueueResponse)
async def review_queue(
    status_filter: Literal["pending", "approved", "rejected", "all"] = Query("pending", alias="status"),
    project_id: str | None = None,
    employee_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    amount_min: float | None = Query(None, ge=0),
    amount_max: float | None = Query(None, ge=0),
    sort_by: Literal["date", "amount", "project"] = Query("date"),
    sort_order: Literal["asc", "desc"] = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    scope: TenantScope = Depends(get_tenant_scope),
    user: User = Depends(require_accountant_or_admin),
    db: AsyncSession = Depends(get_db),
):
    if amount_min is not None and amount_max is not None and amount_max < amount_min:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"detail": "الحد الأقصى يجب أن يكون أكبر من الحد الأدنى", "detail_en": "amount_max must be >= amount_min"},
        )
    from_dt = _parse_date_or_raise(date_from, "date_from") if date_from else None
    to_dt = _parse_date_or_raise(date_to, "date_to") if date_to else None

    items, total, pages = await get_review_queue(
        db=db,
        company_id=scope.company_id,
        status_filter=status_filter,
        project_id=project_id,
        employee_id=employee_id,
        date_from=from_dt,
        date_to=to_dt,
        amount_min=amount_min,
        amount_max=amount_max,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
    return ReviewQueueResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
        server_time=datetime.now(timezone.utc),
    )


@router.get("/{expense_id}/review-detail", response_model=ReviewDetailResponse)
async def review_detail(
    expense_id: str,
    scope: TenantScope = Depends(get_tenant_scope),
    user: User = Depends(require_accountant_or_admin),
    db: AsyncSession = Depends(get_db),
):
    expense = await get_review_detail(db, scope.company_id, expense_id)
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "المصروف غير موجود", "detail_en": "Expense not found"},
        )

    emp_result = await db.execute(select(User).where(User.id == expense.user_id))
    employee = emp_result.scalar_one_or_none()

    audit_result = await db.execute(
        select(ReviewAuditLog)
        .where(ReviewAuditLog.expense_id == expense_id, ReviewAuditLog.company_id == scope.company_id)
        .order_by(ReviewAuditLog.created_at.desc())
    )
    audit_rows = audit_result.scalars().all()

    eta = None
    if expense.eta_uuid or expense.eta_verified:
        eta = ETAInfoSchema(
            verified=expense.eta_verified,
            uuid=expense.eta_uuid,
            vendor_tax_reg=expense.vendor_tax_reg,
        )

    return ReviewDetailResponse(
        id=expense.id,
        review_version=expense.review_version,
        status=expense.status,
        amount=float(expense.amount),
        currency=expense.currency,
        vendor=expense.vendor,
        vendor_tax_reg=expense.vendor_tax_reg,
        items=expense.items,
        notes=expense.notes,
        category_id=expense.category_id,
        project_id=expense.project_id,
        capture_mode=expense.capture_mode,
        receipt_url=expense.receipt_url,
        voice_transcript=expense.voice_transcript,
        eta=eta,
        ai_extraction=expense.ai_extraction,
        ai_confidence=expense.ai_confidence,
        anomaly_flags=expense.anomaly_flags,
        employee=ReviewQueueEmployee(
            id=employee.id,
            name=employee.name,
            name_ar=employee.name_ar,
        ) if employee else ReviewQueueEmployee(id="", name="", name_ar=""),
        audit_history=[
            AuditHistoryItemSchema(
                id=a.id,
                action_type=a.action_type,
                actor_id=a.actor_id,
                field_name=a.field_name,
                value_before=a.value_before,
                value_after=a.value_after,
                rejection_reason=a.rejection_reason,
                created_at=a.created_at,
            )
            for a in audit_rows
        ],
        created_at=expense.created_at,
        updated_at=expense.updated_at,
    )


@router.post("/{expense_id}/receipt-url", response_model=ReceiptUrlResponse)
async def refresh_receipt_url(
    expense_id: str,
    scope: TenantScope = Depends(get_tenant_scope),
    user: User = Depends(require_accountant_or_admin),
    db: AsyncSession = Depends(get_db),
):
    expense = await get_review_detail(db, scope.company_id, expense_id)
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "المصروف غير موجود", "detail_en": "Expense not found"},
        )
    if not expense.receipt_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "لا يوجد إيصال", "detail_en": "No receipt attached"},
        )
    result = await refresh_receipt_signed_url(expense.receipt_url)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "فشل تحديث رابط الإيصال", "detail_en": "Failed to refresh receipt URL"},
        )
    signed_url, expires_in = result
    return ReceiptUrlResponse(receipt_url=signed_url, expires_in=expires_in)


@router.post("/{expense_id}/approve", response_model=ApproveResponse)
async def approve_expense(
    expense_id: str,
    body: ApproveRequest,
    background_tasks: BackgroundTasks,
    scope: TenantScope = Depends(get_tenant_scope),
    user: User = Depends(require_accountant_or_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        expense, next_id = await approve_action(db, scope.company_id, expense_id, user.id, body.review_version)
    except ReviewNotFoundError:
        raise HTTPException(status_code=404, detail={"detail": "المصروف غير موجود", "detail_en": "Expense not found"})
    except ReviewConflictError as e:
        raise HTTPException(status_code=409, detail={"detail": "النسخة قديمة أو الحالة تغيرت", "detail_en": "Stale review version or status changed", "current_version": e.current_version, "current_status": e.current_status})

    background_tasks.add_task(
        run_background, send_decision_notification,
        scope.company_id, expense.user_id, expense.id, "approved", float(expense.amount), expense.currency,
        task_name="push_approve",
    )
    background_tasks.add_task(
        run_background, trigger_export, expense.id, scope.company_id,
        task_name="export_approved",
    )

    return ApproveResponse(
        id=expense.id,
        status=expense.status,
        review_version=expense.review_version,
        reviewed_at=expense.reviewed_at,
        next_pending_id=next_id,
    )


@router.post("/{expense_id}/reject", response_model=RejectResponse)
async def reject_expense(
    expense_id: str,
    body: RejectRequest,
    background_tasks: BackgroundTasks,
    scope: TenantScope = Depends(get_tenant_scope),
    user: User = Depends(require_accountant_or_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        expense, next_id = await reject_action(db, scope.company_id, expense_id, user.id, body.review_version, body.reason)
    except ReviewNotFoundError:
        raise HTTPException(status_code=404, detail={"detail": "المصروف غير موجود", "detail_en": "Expense not found"})
    except ReviewConflictError as e:
        raise HTTPException(status_code=409, detail={"detail": "النسخة قديمة أو الحالة تغيرت", "detail_en": "Stale review version or status changed", "current_version": e.current_version, "current_status": e.current_status})

    background_tasks.add_task(
        run_background, send_decision_notification,
        scope.company_id, expense.user_id, expense.id, "rejected", float(expense.amount), expense.currency, body.reason,
        task_name="push_reject",
    )

    return RejectResponse(
        id=expense.id,
        status=expense.status,
        review_version=expense.review_version,
        rejection_reason=body.reason,
        reviewed_at=expense.reviewed_at,
        next_pending_id=next_id,
    )


@router.post("/{expense_id}/correct", response_model=CorrectExpenseResponse)
async def correct_expense(
    expense_id: str,
    body: CorrectExpenseRequest,
    scope: TenantScope = Depends(get_tenant_scope),
    user: User = Depends(require_accountant_or_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await correct_action(db, scope.company_id, expense_id, user.id, body.review_version, body.field_name, body.corrected_value)
    except ReviewNotFoundError:
        raise HTTPException(status_code=404, detail={"detail": "المصروف غير موجود", "detail_en": "Expense not found"})
    except ReviewConflictError as e:
        raise HTTPException(status_code=409, detail={"detail": "النسخة قديمة أو الحالة تغيرت", "detail_en": "Stale review version or status changed", "current_version": e.current_version, "current_status": e.current_status})
    except ReviewFieldNotAllowedError as e:
        raise HTTPException(status_code=422, detail={"detail": f"الحقل '{e.field_name}' غير مسموح بتعديله", "detail_en": f"Field '{e.field_name}' is not editable"})

    return CorrectExpenseResponse(
        id=result["expense"].id,
        review_version=result["expense"].review_version,
        field_name=result["field_name"],
        value_before=result["value_before"],
        value_after=result["value_after"],
        correction_feedback_created=result["correction_feedback_created"],
        correction_feedback_id=result["correction_feedback_id"],
    )


@router.post("/bulk-approve", response_model=BulkApproveResponse)
async def bulk_approve(
    body: BulkApproveRequest,
    background_tasks: BackgroundTasks,
    scope: TenantScope = Depends(get_tenant_scope),
    user: User = Depends(require_accountant_or_admin),
    db: AsyncSession = Depends(get_db),
):
    items = [{"id": item.id, "review_version": item.review_version} for item in (body.items or [])]
    result = await bulk_approve_action(db, scope.company_id, user.id, items)

    for eid in result["approved_ids"]:
        background_tasks.add_task(
            run_background, send_decision_notification_by_expense,
            scope.company_id, eid, "approved",
            task_name="push_bulk_approve",
        )
        background_tasks.add_task(
            run_background, trigger_export, eid, scope.company_id,
            task_name="export_bulk_approve",
        )

    return BulkApproveResponse(
        bulk_operation_id=result["bulk_operation_id"],
        approved=len(result["approved_ids"]),
        approved_ids=result["approved_ids"],
        skipped=[BulkSkippedItem(**s) for s in result["skipped"]],
        conflicts=[BulkConflictItem(**c) for c in result["conflicts"]],
    )


@router.post("/{expense_id}/resubmit", response_model=ResubmitResponse)
async def resubmit_expense(
    expense_id: str,
    body: ResubmitRequest,
    background_tasks: BackgroundTasks,
    scope: TenantScope = Depends(get_tenant_scope),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        expense = await resubmit_action(db, scope.company_id, expense_id, user.id, user.role, body.review_version, body.changes)
    except ReviewNotFoundError:
        raise HTTPException(status_code=404, detail={"detail": "المصروف غير موجود", "detail_en": "Expense not found"})
    except ReviewNotRejectedError:
        raise HTTPException(status_code=409, detail={"detail": "المصروف ليس مرفوض", "detail_en": "Expense is not rejected"})
    except ReviewNotAuthorizedError:
        raise HTTPException(status_code=403, detail={"detail": "غير مصرح بإعادة إرسال هذا المصروف", "detail_en": "Not authorized to resubmit this expense"})
    except ReviewConflictError as e:
        raise HTTPException(status_code=409, detail={"detail": "النسخة قديمة", "detail_en": "Stale review version", "current_version": e.current_version, "current_status": e.current_status})

    background_tasks.add_task(
        run_background, send_batched_accountant_notification,
        scope.company_id, 1,
        task_name="notify_resubmit",
    )

    return ResubmitResponse(
        id=expense.id,
        status=expense.status,
        review_version=expense.review_version,
    )


@router.get("/ai-metrics", response_model=AiMetricsResponse)
async def ai_metrics(
    date_from: str | None = None,
    date_to: str | None = None,
    scope: TenantScope = Depends(get_tenant_scope),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from_dt = _parse_date_or_raise(date_from, "date_from") if date_from else None
    to_dt = _parse_date_or_raise(date_to, "date_to") if date_to else None

    base_filter = [Expense.company_id == scope.company_id]
    if from_dt:
        base_filter.append(Expense.created_at >= from_dt)
    if to_dt:
        base_filter.append(Expense.created_at <= to_dt)

    total_result = await db.execute(
        select(func.count()).select_from(Expense).where(*base_filter)
    )
    total_expenses = total_result.scalar() or 0

    ai_filter = base_filter + [Expense.ai_extraction.isnot(None)]
    ai_result = await db.execute(
        select(func.count()).select_from(Expense).where(*ai_filter)
    )
    total_ai_expenses = ai_result.scalar() or 0

    from app.models.correction import CorrectionFeedback
    feedback_base = [CorrectionFeedback.company_id == scope.company_id]
    if from_dt:
        feedback_base.append(CorrectionFeedback.created_at >= from_dt)
    if to_dt:
        feedback_base.append(CorrectionFeedback.created_at <= to_dt)

    total_corr_result = await db.execute(
        select(func.count()).select_from(CorrectionFeedback).where(*feedback_base)
    )
    total_corrections = total_corr_result.scalar() or 0

    correction_rate = round(total_corrections / total_ai_expenses, 4) if total_ai_expenses > 0 else 0.0

    field_result = await db.execute(
        select(
            CorrectionFeedback.field_name,
            func.count().label("count"),
        )
        .where(*feedback_base)
        .group_by(CorrectionFeedback.field_name)
    )
    corrections_by_field = []
    for row in field_result:
        rate = round(row.count / total_ai_expenses, 4) if total_ai_expenses > 0 else 0.0
        corrections_by_field.append(CorrectionFieldMetricSchema(field_name=row.field_name, count=row.count, rate=rate))

    trend_subq = (
        select(
            func.date(CorrectionFeedback.created_at).label("date"),
            func.count().label("corrections"),
        )
        .where(*feedback_base)
        .group_by(func.date(CorrectionFeedback.created_at))
        .subquery()
    )

    ai_expense_subq = (
        select(
            func.date(Expense.created_at).label("date"),
            func.count().label("ai_expenses"),
        )
        .where(
            Expense.company_id == scope.company_id,
            Expense.ai_extraction.isnot(None),
            *([Expense.created_at >= from_dt] if from_dt else []),
            *([Expense.created_at <= to_dt] if to_dt else []),
        )
        .group_by(func.date(Expense.created_at))
        .subquery()
    )

    from sqlalchemy import literal_column
    combined = (
        select(
            func.coalesce(trend_subq.c.date, ai_expense_subq.c.date).label("date"),
            func.coalesce(trend_subq.c.corrections, 0).label("corrections"),
            func.coalesce(ai_expense_subq.c.ai_expenses, 0).label("ai_expenses"),
        )
        .select_from(
            trend_subq.join(ai_expense_subq, trend_subq.c.date == ai_expense_subq.c.date, full=True)
        )
        .order_by(literal_column("date"))
    )
    trend_result = await db.execute(combined)
    daily_trend = [
        DailyCorrectionTrendSchema(
            date=str(row.date),
            corrections=row.corrections,
            ai_expenses=row.ai_expenses,
        )
        for row in trend_result
    ]

    return AiMetricsResponse(
        total_expenses=total_expenses,
        total_ai_expenses=total_ai_expenses,
        total_corrections=total_corrections,
        correction_rate=correction_rate,
        corrections_by_field=corrections_by_field,
        daily_trend=daily_trend,
    )
