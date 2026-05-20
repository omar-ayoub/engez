import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expense import Expense
from app.models.correction import CorrectionFeedback


@pytest.fixture
async def seeded_metrics(db_session: AsyncSession, seed_data):
    company_id = seed_data["company"].id
    user_id = seed_data["user"].id

    for i in range(5):
        eid = f"exp-metrics-{i:03d}"
        existing = await db_session.get(Expense, eid)
        if existing:
            continue
        exp = Expense(
            id=eid,
            user_id=user_id,
            company_id=company_id,
            amount=100.0 * (i + 1),
            currency="EGP",
            vendor=f"Vendor {i}",
            items="Items",
            capture_mode="receipt" if i < 3 else "manual",
            status="approved",
            ai_extraction={"amount": 100.0 * (i + 1), "vendor": f"Vendor {i}"} if i < 3 else None,
            ai_confidence={"amount": 0.9} if i < 3 else None,
            review_version=1,
        )
        db_session.add(exp)

    for idx, field_name in enumerate(["vendor", "amount", "items"]):
        fb_id = f"fb-metrics-{field_name}-{idx}"
        existing = await db_session.get(CorrectionFeedback, fb_id)
        if existing:
            continue
        fb = CorrectionFeedback(
            id=fb_id,
            expense_id="exp-metrics-000",
            company_id=company_id,
            field_name=field_name,
            ai_value="AI Value",
            corrected_value="Corrected Value",
            corrected_by=user_id,
        )
        db_session.add(fb)

    extra_fb = await db_session.get(CorrectionFeedback, "fb-metrics-vendor-extra")
    if not extra_fb:
        db_session.add(CorrectionFeedback(
            id="fb-metrics-vendor-extra",
            expense_id="exp-metrics-001",
            company_id=company_id,
            field_name="vendor",
            ai_value="AI Vendor",
            corrected_value="Corrected Vendor",
            corrected_by=user_id,
        ))

    await db_session.commit()


@pytest.mark.asyncio
async def test_ai_metrics_admin_access(admin_client: AsyncClient, seeded_metrics):
    resp = await admin_client.get("/api/v1/expenses/ai-metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_expenses" in data
    assert "total_ai_expenses" in data
    assert "total_corrections" in data
    assert "correction_rate" in data
    assert "corrections_by_field" in data
    assert "daily_trend" in data


@pytest.mark.asyncio
async def test_ai_metrics_non_admin_denied(auth_client: AsyncClient, seeded_metrics):
    resp = await auth_client.get("/api/v1/expenses/ai-metrics")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_ai_metrics_totals(admin_client: AsyncClient, seeded_metrics):
    resp = await admin_client.get("/api/v1/expenses/ai-metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_expenses"] >= 5
    assert data["total_ai_expenses"] >= 3
    assert data["total_corrections"] >= 4


@pytest.mark.asyncio
async def test_ai_metrics_by_field(admin_client: AsyncClient, seeded_metrics):
    resp = await admin_client.get("/api/v1/expenses/ai-metrics")
    assert resp.status_code == 200
    data = resp.json()
    fields = {f["field_name"]: f for f in data["corrections_by_field"]}
    assert "vendor" in fields
    assert fields["vendor"]["count"] >= 2


@pytest.mark.asyncio
async def test_ai_metrics_date_filter(admin_client: AsyncClient, seeded_metrics):
    resp = await admin_client.get("/api/v1/expenses/ai-metrics?date_from=2020-01-01&date_to=2030-12-31")
    assert resp.status_code == 200
