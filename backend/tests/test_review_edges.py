"""Edge-case tests for Review Desk (Spec 03) — TDD review pass."""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expense import Expense
from app.models.correction import CorrectionFeedback


# ── Bulk approve schema rejects >50 items ────────────────────────────


@pytest.mark.asyncio
async def test_bulk_approve_over_50_returns_422(admin_client: AsyncClient):
    """Schema enforces max_length=50 on items list."""
    items = [{"id": f"fake-{i}", "review_version": 0} for i in range(51)]
    resp = await admin_client.post("/api/v1/expenses/bulk-approve", json={"items": items})
    assert resp.status_code == 422


# ── Resubmit clears stale anomaly flags ──────────────────────────────


@pytest.mark.asyncio
async def test_resubmit_clears_anomaly_flags(admin_client: AsyncClient, db_session: AsyncSession, seed_data):
    """After resubmit with changed amount, old anomaly_flags should be cleared."""
    expense = Expense(
        id=f"exp-resub-anom-{uuid.uuid4().hex[:8]}",
        user_id=seed_data["admin"].id,
        company_id=seed_data["company"].id,
        amount=50000.0,
        currency="EGP",
        vendor="Overpriced Co",
        items="Gold bolts",
        capture_mode="manual",
        status="rejected",
        rejection_reason="Amount too high",
        review_version=1,
        anomaly_flags={"statistical_outlier": {"severity": "medium", "message": "too high"}},
    )
    db_session.add(expense)
    await db_session.commit()

    resp = await admin_client.post(
        f"/api/v1/expenses/{expense.id}/resubmit",
        json={"review_version": 1, "changes": {"amount": 500.0}},
    )
    assert resp.status_code == 200

    await db_session.refresh(expense)
    # Stale flags from the previous review cycle must be cleared
    assert expense.anomaly_flags is None or expense.anomaly_flags == {}


# ── Resubmit a pending expense must fail ─────────────────────────────


@pytest.mark.asyncio
async def test_resubmit_pending_returns_409(admin_client: AsyncClient, db_session: AsyncSession, seed_data):
    """Only rejected expenses can be resubmitted."""
    expense = Expense(
        id=f"exp-resub-pend-{uuid.uuid4().hex[:8]}",
        user_id=seed_data["admin"].id,
        company_id=seed_data["company"].id,
        amount=100.0,
        currency="EGP",
        vendor="Test",
        items="Items",
        capture_mode="manual",
        status="pending",
        review_version=0,
    )
    db_session.add(expense)
    await db_session.commit()

    resp = await admin_client.post(
        f"/api/v1/expenses/{expense.id}/resubmit",
        json={"review_version": 0},
    )
    assert resp.status_code == 409


# ── Correct amount (numeric path) ────────────────────────────────────


@pytest.mark.asyncio
async def test_correct_amount_field(admin_client: AsyncClient, db_session: AsyncSession, seed_data):
    """Correcting amount exercises the numeric code path and creates feedback if AI disagrees."""
    expense = Expense(
        id=f"exp-corr-amt-{uuid.uuid4().hex[:8]}",
        user_id=seed_data["user"].id,
        company_id=seed_data["company"].id,
        amount=1500.0,
        currency="EGP",
        vendor="Cement Co",
        items="Bags",
        capture_mode="receipt",
        status="pending",
        ai_extraction={"amount": 1500.0, "vendor": "Cement Co"},
        ai_confidence={"amount": 0.85, "vendor": 0.90},
        review_version=0,
    )
    db_session.add(expense)
    await db_session.commit()

    resp = await admin_client.post(
        f"/api/v1/expenses/{expense.id}/correct",
        json={"review_version": 0, "field_name": "amount", "corrected_value": 1200.0},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["field_name"] == "amount"
    assert data["value_after"] == "1200.0"
    assert data["correction_feedback_created"] is True


# ── Correct to same value → no AI feedback created ───────────────────


@pytest.mark.asyncio
async def test_correct_same_value_no_feedback(admin_client: AsyncClient, db_session: AsyncSession, seed_data):
    """Correcting a field to the same value AI predicted should NOT create feedback."""
    expense = Expense(
        id=f"exp-corr-same-{uuid.uuid4().hex[:8]}",
        user_id=seed_data["user"].id,
        company_id=seed_data["company"].id,
        amount=200.0,
        currency="EGP",
        vendor="Same Vendor",
        items="Items",
        capture_mode="receipt",
        status="pending",
        ai_extraction={"vendor": "Same Vendor"},
        ai_confidence={"vendor": 0.95},
        review_version=0,
    )
    db_session.add(expense)
    await db_session.commit()

    resp = await admin_client.post(
        f"/api/v1/expenses/{expense.id}/correct",
        json={"review_version": 0, "field_name": "vendor", "corrected_value": "Same Vendor"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["correction_feedback_created"] is False


# ── AI metrics date filtering ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_ai_metrics_returns_structure(admin_client: AsyncClient):
    """AI metrics endpoint returns expected schema fields."""
    resp = await admin_client.get("/api/v1/expenses/ai-metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_expenses" in data
    assert "total_ai_expenses" in data
    assert "correction_rate" in data
    assert "corrections_by_field" in data
    assert "daily_trend" in data


@pytest.mark.asyncio
async def test_ai_metrics_invalid_date_returns_422(admin_client: AsyncClient):
    """Invalid date format for ai-metrics returns 422."""
    resp = await admin_client.get("/api/v1/expenses/ai-metrics?date_from=not-a-date")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_ai_metrics_with_date_range(admin_client: AsyncClient):
    """Date range params are accepted and don't crash."""
    resp = await admin_client.get(
        "/api/v1/expenses/ai-metrics?date_from=2025-01-01&date_to=2025-12-31"
    )
    assert resp.status_code == 200


# ── Approve already-approved expense → 409 ───────────────────────────


@pytest.mark.asyncio
async def test_approve_already_approved_returns_409(admin_client: AsyncClient, db_session: AsyncSession, seed_data):
    expense = Expense(
        id=f"exp-double-app-{uuid.uuid4().hex[:8]}",
        user_id=seed_data["user"].id,
        company_id=seed_data["company"].id,
        amount=100.0,
        currency="EGP",
        vendor="Test",
        items="Items",
        capture_mode="manual",
        status="approved",
        review_version=1,
    )
    db_session.add(expense)
    await db_session.commit()

    resp = await admin_client.post(
        f"/api/v1/expenses/{expense.id}/approve",
        json={"review_version": 1},
    )
    assert resp.status_code == 409


# ── Queue filters ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_queue_amount_min_greater_than_max_returns_422(admin_client: AsyncClient):
    resp = await admin_client.get("/api/v1/expenses/queue?amount_min=1000&amount_max=100")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_queue_invalid_date_returns_422(admin_client: AsyncClient):
    resp = await admin_client.get("/api/v1/expenses/queue?date_from=bad-date")
    assert resp.status_code == 422
