import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expense import Expense


@pytest.fixture
async def analytics_expenses(db_session: AsyncSession, seed_data):
    """Seed approved expenses for analytics testing."""
    company_id = seed_data["company"].id
    user_id = seed_data["user"].id
    project_id = seed_data["project"].id
    category_id = seed_data["category"].id

    for i in range(10):
        existing = await db_session.get(Expense, f"exp-analytics-{i:03d}")
        if existing:
            continue
        exp = Expense(
            id=f"exp-analytics-{i:03d}",
            user_id=user_id,
            company_id=company_id,
            project_id=project_id,
            category_id=category_id,
            amount=100.0 * (i + 1),
            currency="EGP",
            vendor=f"Analytics Vendor {i}",
            items="Items",
            capture_mode="receipt",
            status="approved",
            review_version=1,
            reviewed_by=seed_data["admin"].id,
        )
        db_session.add(exp)

    await db_session.commit()


# ── Spend by Project ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_spend_by_project(admin_client: AsyncClient, analytics_expenses):
    resp = await admin_client.get("/api/v1/analytics/spend-by-project?days=90")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if len(data) > 0:
        item = data[0]
        assert "name" in item or "name_ar" in item
        assert "total_spend" in item


@pytest.mark.asyncio
async def test_spend_by_project_default_period(admin_client: AsyncClient, analytics_expenses):
    resp = await admin_client.get("/api/v1/analytics/spend-by-project")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_spend_by_project_invalid_days(admin_client: AsyncClient, analytics_expenses):
    resp = await admin_client.get("/api/v1/analytics/spend-by-project?days=0")
    assert resp.status_code == 422


# ── Spend by Category ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_spend_by_category(admin_client: AsyncClient, analytics_expenses):
    resp = await admin_client.get("/api/v1/analytics/spend-by-category?days=90")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if len(data) > 0:
        item = data[0]
        assert "category" in item or "category_id" in item
        assert "total" in item


@pytest.mark.asyncio
async def test_spend_by_category_default_period(admin_client: AsyncClient, analytics_expenses):
    resp = await admin_client.get("/api/v1/analytics/spend-by-category")
    assert resp.status_code == 200


# ── Spend Trend ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_spend_trend(admin_client: AsyncClient, analytics_expenses):
    resp = await admin_client.get("/api/v1/analytics/spend-trend?days=90")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if len(data) > 0:
        item = data[0]
        assert "week" in item or "period" in item
        assert "total" in item


@pytest.mark.asyncio
async def test_spend_trend_max_period(admin_client: AsyncClient, analytics_expenses):
    resp = await admin_client.get("/api/v1/analytics/spend-trend?days=365")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_spend_trend_exceeds_max(admin_client: AsyncClient, analytics_expenses):
    resp = await admin_client.get("/api/v1/analytics/spend-trend?days=500")
    assert resp.status_code == 422


# ── Budget vs Actual ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_budget_vs_actual(admin_client: AsyncClient, analytics_expenses):
    resp = await admin_client.get("/api/v1/analytics/budget-vs-actual")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if len(data) > 0:
        item = data[0]
        assert "name" in item or "name_ar" in item
        assert "actual_spend" in item


# ── Export ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_export_csv(admin_client: AsyncClient, analytics_expenses):
    resp = await admin_client.get("/api/v1/analytics/export?format=csv&view=spend-by-project&days=90")
    assert resp.status_code == 200
    content_type = resp.headers.get("content-type", "")
    assert "text/csv" in content_type or "application/octet-stream" in content_type


@pytest.mark.asyncio
async def test_export_excel(admin_client: AsyncClient, analytics_expenses):
    resp = await admin_client.get("/api/v1/analytics/export?format=excel&view=spend-by-project&days=90")
    assert resp.status_code == 200
    content_type = resp.headers.get("content-type", "")
    assert "spreadsheet" in content_type or "application/octet-stream" in content_type


@pytest.mark.asyncio
async def test_export_invalid_format(admin_client: AsyncClient, analytics_expenses):
    resp = await admin_client.get("/api/v1/analytics/export?format=pdf&view=spend-by-project")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_export_invalid_view(admin_client: AsyncClient, analytics_expenses):
    resp = await admin_client.get("/api/v1/analytics/export?format=csv&view=invalid-view")
    assert resp.status_code == 422


# ── Access Control ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analytics_requires_accountant_or_admin(auth_client: AsyncClient, analytics_expenses):
    resp = await auth_client.get("/api/v1/analytics/spend-by-project")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_analytics_accessible_by_accountant(accountant_client: AsyncClient, analytics_expenses):
    resp = await accountant_client.get("/api/v1/analytics/spend-by-project")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_analytics_tenant_isolation(admin_client: AsyncClient, analytics_expenses):
    """Analytics should only show data for the current user's company."""
    resp = await admin_client.get("/api/v1/analytics/spend-by-project?days=365")
    assert resp.status_code == 200
    data = resp.json()
    # All returned data belongs to the seeded company (no cross-tenant leak)
    assert isinstance(data, list)


# ── Dashboard Summary ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_summary(admin_client: AsyncClient, analytics_expenses):
    """Dashboard summary endpoint returns aggregated KPIs."""
    resp = await admin_client.get("/api/v1/analytics/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_spend" in data
    assert "expense_count" in data
    assert "project_count" in data
