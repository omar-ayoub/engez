import math
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_active_user, get_tenant_scope
from app.core.tenant import TenantScope
from app.models.correction import CorrectionFeedback
from app.models.expense import Expense
from app.models.user import User
from app.schemas.expense import ExpenseCreate, ExpenseListResponse, ExpensePatch, ExpenseResponse
from app.services.anomaly import detect_anomalies
from app.services.background import run_background
from app.services.push_notifications import send_batched_accountant_notification

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.post("/", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    body: ExpenseCreate,
    background_tasks: BackgroundTasks,
    scope: TenantScope = Depends(get_tenant_scope),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    existing_result = await db.execute(
        select(Expense).where(
            Expense.company_id == scope.company_id,
            Expense.offline_id == body.offline_id,
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "detail": "تم إرسال هذا المصروف مسبقاً",
                "detail_en": "This expense was already submitted",
                "existing_id": str(existing.id),
            },
        )

    expense = Expense(
        user_id=user.id,
        company_id=scope.company_id,
        offline_id=body.offline_id,
        amount=body.amount,
        currency=body.currency,
        vendor=body.vendor,
        vendor_tax_reg=body.vendor_tax_reg,
        items=body.items,
        category_id=body.category_id,
        project_id=body.project_id,
        notes=body.notes,
        capture_mode=body.capture_mode,
        voice_url=body.voice_url,
        voice_transcript=body.voice_transcript,
        receipt_url=body.receipt_url,
        eta_uuid=body.eta_uuid,
        eta_verified=body.eta_verified,
        ai_extraction=body.ai_extraction,
        ai_confidence=body.ai_confidence,
        status="pending",
    )
    db.add(expense)
    await db.commit()
    await db.refresh(expense)

    background_tasks.add_task(
        run_background, send_batched_accountant_notification, scope.company_id, 1,
        task_name="notify_accountants",
    )
    background_tasks.add_task(
        run_background, detect_anomalies, expense.id, scope.company_id,
        task_name="detect_anomalies",
    )

    return expense


@router.get("/", response_model=ExpenseListResponse)
async def list_expenses(
    status_filter: str | None = Query(None, alias="status"),
    capture_mode: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    project_id: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    scope: TenantScope = Depends(get_tenant_scope),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Expense).where(Expense.company_id == scope.company_id)
    count_query = select(func.count()).select_from(Expense).where(Expense.company_id == scope.company_id)

    if status_filter:
        query = query.where(Expense.status == status_filter)
        count_query = count_query.where(Expense.status == status_filter)
    if capture_mode:
        query = query.where(Expense.capture_mode == capture_mode)
        count_query = count_query.where(Expense.capture_mode == capture_mode)
    if project_id:
        query = query.where(Expense.project_id == project_id)
        count_query = count_query.where(Expense.project_id == project_id)
    if from_date:
        try:
            from_dt = datetime.fromisoformat(from_date).replace(hour=0, minute=0, second=0)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"detail": "تنسيق تاريخ غير صالح", "detail_en": "Invalid date format for from_date"},
            )
        query = query.where(Expense.created_at >= from_dt)
        count_query = count_query.where(Expense.created_at >= from_dt)
    if to_date:
        try:
            to_dt = datetime.fromisoformat(to_date).replace(hour=23, minute=59, second=59)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"detail": "تنسيق تاريخ غير صالح", "detail_en": "Invalid date format for to_date"},
            )
        query = query.where(Expense.created_at <= to_dt)
        count_query = count_query.where(Expense.created_at <= to_dt)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    pages = math.ceil(total / per_page) if total > 0 else 1

    query = query.order_by(Expense.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    expenses = result.scalars().all()

    return ExpenseListResponse(
        items=expenses,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.patch("/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: str,
    body: ExpensePatch,
    scope: TenantScope = Depends(get_tenant_scope),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Expense).where(Expense.id == expense_id, Expense.company_id == scope.company_id)
    )
    expense = result.scalar_one_or_none()
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "المصروف غير موجود", "detail_en": "Expense not found"},
        )

    if str(expense.user_id) != str(user.id) and getattr(user, "role", None) != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "detail": "غير مصرح بتعديل هذا المصروف",
                "detail_en": "Not authorized to modify this expense",
            },
        )

    update_data = body.model_dump(exclude_unset=True)

    if expense.ai_extraction and expense.capture_mode in ("voice", "receipt", "combined"):
        ai_fields = {
            "amount": lambda e: e.get("amount"),
            "vendor": lambda e: e.get("vendor"),
            "items": lambda e: e.get("items"),
            "category_id": lambda e: e.get("category"),
            "vendor_tax_reg": lambda e: e.get("vendor_tax_reg"),
        }
        for field, extractor in ai_fields.items():
            if field in update_data:
                ai_val = extractor(expense.ai_extraction)
                if ai_val is not None and str(update_data[field]) != str(ai_val):
                    feedback = CorrectionFeedback(
                        expense_id=expense.id,
                        company_id=scope.company_id,
                        field_name=field,
                        ai_value=str(ai_val),
                        corrected_value=str(update_data[field]),
                        corrected_by=user.id,
                    )
                    db.add(feedback)

    for field, value in update_data.items():
        setattr(expense, field, value)

    await db.commit()
    await db.refresh(expense)
    return expense



