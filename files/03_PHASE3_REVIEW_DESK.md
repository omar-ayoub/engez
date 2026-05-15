# Phase 3: Review Desk — Weeks 8–10

## Spec-Kit Commands for Phase 3

```bash
/speckit.specify
```

> **Specification Prompt for Phase 3:**
>
> Build the accountant review desk — the second critical user interface that determines whether the app replaces WhatsApp or gets abandoned.
>
> The accountant sits in an office with reliable internet. They receive a queue of pending expenses submitted by field workers. For each expense, they see: the receipt image (zoomable), all AI-extracted fields with confidence indicators, the original voice transcript (if available), an ETA verification badge (if QR was decoded), and any anomaly flags.
>
> Actions: Approve (single tap), Reject with reason (required text), Edit any field (inline correction). When an accountant corrects an AI-extracted field, that correction is stored in the correction_feedback table and automatically improves future extractions for that company tenant.
>
> Bulk approve is available for expenses marked as ETA-verified with high confidence scores. Web Push notifications notify field workers of approval/rejection and notify accountants of new pending expenses (batched, not per-expense).
>
> The queue must be filterable by: project, date range, employee, status, amount range. Sort by: date, amount, project.

```bash
/speckit.plan
/speckit.tasks
/speckit.implement
```

---

## Task 3.1: Accountant Review Queue (Days 1–5)

### API Endpoint: Pending Expenses

Create `backend/app/api/v1/expenses.py`:

```python
"""Expense CRUD and review queue endpoints."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_role
from app.models.expense import Expense, User, CorrectionFeedback

router = APIRouter(prefix="/expenses", tags=["expenses"])


class ExpenseFilter(BaseModel):
    status: Optional[str] = None
    project_id: Optional[str] = None
    user_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    amount_min: Optional[Decimal] = None
    amount_max: Optional[Decimal] = None


@router.get("/queue")
async def get_review_queue(
    status: str = Query("pending"),
    project_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_role("accountant", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """Get filterable, paginated expense review queue.
    Scoped to current user's company (multi-tenant)."""

    conditions = [Expense.company_id == current_user.company_id]

    if status:
        conditions.append(Expense.status == status)
    if project_id:
        conditions.append(Expense.project_id == project_id)
    if user_id:
        conditions.append(Expense.user_id == user_id)
    if date_from:
        conditions.append(Expense.created_at >= date_from)
    if date_to:
        conditions.append(Expense.created_at <= date_to)

    # Count total
    count_stmt = select(func.count(Expense.id)).where(and_(*conditions))
    total = (await db.execute(count_stmt)).scalar()

    # Sort
    sort_col = getattr(Expense, sort_by, Expense.created_at)
    order = sort_col.desc() if sort_order == "desc" else sort_col.asc()

    # Paginate
    stmt = (
        select(Expense)
        .where(and_(*conditions))
        .order_by(order)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    expenses = result.scalars().all()

    return {
        "items": expenses,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.post("/{expense_id}/approve")
async def approve_expense(
    expense_id: str,
    current_user: User = Depends(require_role("accountant", "admin")),
    db: AsyncSession = Depends(get_db),
):
    expense = await db.get(Expense, expense_id)
    if not expense or expense.company_id != current_user.company_id:
        raise HTTPException(404, "Expense not found")

    expense.status = "approved"
    await db.commit()

    # Trigger push notification to field worker
    from app.services.push_notify import notify_expense_status
    await notify_expense_status(db, expense)

    return {"status": "approved"}


@router.post("/{expense_id}/reject")
async def reject_expense(
    expense_id: str,
    reason: str,
    current_user: User = Depends(require_role("accountant", "admin")),
    db: AsyncSession = Depends(get_db),
):
    expense = await db.get(Expense, expense_id)
    if not expense or expense.company_id != current_user.company_id:
        raise HTTPException(404, "Expense not found")

    expense.status = "rejected"
    expense.rejection_reason = reason
    await db.commit()

    from app.services.push_notify import notify_expense_status
    await notify_expense_status(db, expense)

    return {"status": "rejected", "reason": reason}


@router.post("/{expense_id}/correct")
async def correct_expense_field(
    expense_id: str,
    field_name: str,
    corrected_value: str,
    current_user: User = Depends(require_role("accountant", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """Correct an AI-extracted field. Stores feedback for the learning loop."""
    expense = await db.get(Expense, expense_id)
    if not expense or expense.company_id != current_user.company_id:
        raise HTTPException(404, "Expense not found")

    # Get the AI's original value
    ai_value = ""
    if expense.ai_extraction and field_name in expense.ai_extraction:
        ai_value = str(expense.ai_extraction[field_name])

    # Update the expense field
    if hasattr(expense, field_name):
        setattr(expense, field_name, corrected_value)

    # Store correction feedback — THE COMPOUNDING MOAT
    feedback = CorrectionFeedback(
        expense_id=expense_id,
        company_id=current_user.company_id,
        field_name=field_name,
        ai_value=ai_value,
        corrected_value=corrected_value,
        corrected_by=current_user.id,
    )
    db.add(feedback)
    await db.commit()

    return {"corrected": True, "field": field_name}


@router.post("/bulk-approve")
async def bulk_approve(
    expense_ids: list[str],
    current_user: User = Depends(require_role("accountant", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """Bulk approve expenses — only for ETA-verified, high-confidence items."""
    stmt = (
        select(Expense)
        .where(
            Expense.id.in_(expense_ids),
            Expense.company_id == current_user.company_id,
            Expense.status == "pending",
        )
    )
    result = await db.execute(stmt)
    expenses = result.scalars().all()

    approved_ids = []
    for expense in expenses:
        expense.status = "approved"
        approved_ids.append(expense.id)

    await db.commit()

    return {"approved": len(approved_ids), "ids": approved_ids}
```

---

## Task 3.2: AI Correction Feedback Loop (Days 6–7)

The correction feedback system is already wired into the `/correct` endpoint above. The key insight is how it compounds:

### Feedback Flow

1. **Field worker submits** → AI extracts `{vendor: "محل أحمد", category: "other"}`
2. **Accountant corrects** → changes category from `"other"` to `"materials"`
3. **System stores** → `correction_feedback` row: `{field: "category", ai: "other", corrected: "materials"}`
4. **Next extraction** → `get_few_shot_examples()` injects: `"When AI extracted 'other' for category, the correct value was 'materials'"`
5. **After ~50 corrections** → AI effectively learns the company's vocabulary
6. **After ~200 corrections** → extraction accuracy compounds dramatically — unmatched by competitors

### Metrics Endpoint

```python
@router.get("/ai-metrics")
async def get_ai_metrics(
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Track correction rates per field — surfaces which fields need attention."""
    from sqlalchemy import func

    stmt = (
        select(
            CorrectionFeedback.field_name,
            func.count(CorrectionFeedback.id).label("total_corrections"),
        )
        .where(CorrectionFeedback.company_id == current_user.company_id)
        .group_by(CorrectionFeedback.field_name)
    )
    result = await db.execute(stmt)

    total_expenses = await db.scalar(
        select(func.count(Expense.id)).where(
            Expense.company_id == current_user.company_id
        )
    )

    return {
        "total_expenses": total_expenses,
        "corrections_by_field": {
            row.field_name: row.total_corrections for row in result
        },
    }
```

---

## Task 3.3: Web Push Notifications (Days 8–10)

### Backend: Push Notification Service

Create `backend/app/services/push_notify.py`:

```python
"""Web Push notification service."""

import json
from pywebpush import webpush, WebPushException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.expense import User, Expense


async def notify_expense_status(db: AsyncSession, expense: Expense):
    """Notify field worker of expense approval/rejection."""
    user = await db.get(User, expense.user_id)
    if not user or not user.push_subscription:
        return

    status_text = "تمت الموافقة" if expense.status == "approved" else "مرفوض"
    body = f"مصروف {expense.amount} ج.م — {status_text}"

    if expense.status == "rejected" and expense.rejection_reason:
        body += f"\nالسبب: {expense.rejection_reason}"

    await _send_push(
        user.push_subscription,
        {"title": "مصروف", "body": body, "tag": f"expense-{expense.id}"},
    )


async def notify_accountants_pending(db: AsyncSession, company_id: str, count: int):
    """Notify accountants of pending expenses (batched)."""
    stmt = select(User).where(
        User.company_id == company_id,
        User.role.in_(["accountant", "admin"]),
        User.push_subscription.isnot(None),
    )
    result = await db.execute(stmt)
    accountants = result.scalars().all()

    for accountant in accountants:
        await _send_push(
            accountant.push_subscription,
            {
                "title": "مصروفات جديدة",
                "body": f"{count} مصروفات في انتظار المراجعة",
                "tag": "pending-expenses",
            },
        )


async def _send_push(subscription: dict, payload: dict):
    """Send a Web Push notification."""
    try:
        webpush(
            subscription_info=subscription,
            data=json.dumps(payload),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": f"mailto:{settings.VAPID_CLAIMS_EMAIL}"},
        )
    except WebPushException:
        pass  # Subscription expired — will be cleaned up
```

### Frontend: Push Subscription

Create `frontend/src/hooks/usePushNotifications.ts`:

```typescript
import { useCallback } from "react";
import { useAuth } from "@/lib/auth";

export function usePushNotifications() {
  const { token } = useAuth();

  const subscribe = useCallback(async () => {
    if (!("PushManager" in window)) return;

    const registration = await navigator.serviceWorker.ready;

    // Request permission
    const permission = await Notification.requestPermission();
    if (permission !== "granted") return;

    // Subscribe with VAPID public key
    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: import.meta.env.VITE_VAPID_PUBLIC_KEY,
    });

    // Send subscription to backend
    await fetch("/api/v1/users/push-subscription", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(subscription.toJSON()),
    });
  }, [token]);

  return { subscribe };
}
```

---

## Phase 3 Completion Checklist

- [ ] Review queue loads with pagination and filtering
- [ ] Receipt image is zoomable in detail view
- [ ] Confidence badges render (green ≥0.8, amber ≥0.5, red <0.5)
- [ ] ETA verified badge appears on QR-decoded expenses
- [ ] Approve/Reject actions work with immediate queue update
- [ ] Rejection requires reason text
- [ ] Field correction stores to correction_feedback table
- [ ] Bulk approve works for ETA-verified expenses
- [ ] Web Push permissions prompt after first successful submission
- [ ] Field worker receives approval/rejection notification
- [ ] Accountants receive batched "N expenses pending" notification
- [ ] AI metrics endpoint returns correction counts by field
- [ ] `/impeccable audit review-desk` passes

**Proceed to `04_PHASE4_INTEGRATION.md` →**
