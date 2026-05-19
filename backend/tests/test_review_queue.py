import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expense import Expense


@pytest.fixture
async def seeded_expenses(db_session: AsyncSession, seed_data):
    company_id = seed_data["company"].id
    user_id = seed_data["user"].id
    project_id = seed_data["project"].id

    for i in range(5):
        existing = await db_session.get(Expense, f"exp-queue-{i:03d}")
        if existing:
            continue
        exp = Expense(
            id=f"exp-queue-{i:03d}",
            user_id=user_id,
            company_id=company_id,
            project_id=project_id,
            amount=100.0 * (i + 1),
            currency="EGP",
            vendor=f"Vendor {i}",
            items="Items",
            capture_mode="receipt",
            status="pending",
            eta_verified=i % 2 == 0,
            ai_confidence={"amount": 0.9, "vendor": 0.85} if i % 2 == 0 else {"amount": 0.5},
            ai_extraction={"amount": 100.0 * (i + 1), "vendor": f"Vendor {i}"},
            anomaly_flags={"unusual_amount": {"severity": "high"}} if i == 0 else None,
            review_version=0,
        )
        db_session.add(exp)

    existing = await db_session.get(Expense, "exp-approved-001")
    if not existing:
        approved = Expense(
            id="exp-approved-001",
            user_id=user_id,
            company_id=company_id,
            amount=500.0,
            currency="EGP",
            vendor="Approved Vendor",
            items="Items",
            capture_mode="manual",
            status="approved",
            review_version=1,
            reviewed_by=seed_data["admin"].id,
        )
        db_session.add(approved)

    existing = await db_session.get(Expense, "exp-rejected-001")
    if not existing:
        rejected = Expense(
            id="exp-rejected-001",
            user_id=user_id,
            company_id=company_id,
            amount=300.0,
            currency="EGP",
            vendor="Rejected Vendor",
            items="Items",
            capture_mode="manual",
            status="rejected",
            rejection_reason="Receipt unreadable",
            review_version=1,
            reviewed_by=seed_data["admin"].id,
        )
        db_session.add(rejected)

    await db_session.commit()


@pytest.mark.asyncio
async def test_queue_returns_pending_by_default(admin_client: AsyncClient, seeded_expenses):
    resp = await admin_client.get("/api/v1/expenses/queue")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "pages" in data
    assert "server_time" in data
    for item in data["items"]:
        assert item["status"] == "pending"


@pytest.mark.asyncio
async def test_queue_pagination(admin_client: AsyncClient, seeded_expenses):
    resp = await admin_client.get("/api/v1/expenses/queue?page=1&page_size=2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["items"]) <= 2


@pytest.mark.asyncio
async def test_queue_filter_by_status_approved(admin_client: AsyncClient, seeded_expenses):
    resp = await admin_client.get("/api/v1/expenses/queue?status=approved")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) >= 1
    for item in data["items"]:
        assert item["status"] == "approved"


@pytest.mark.asyncio
async def test_queue_filter_by_status_all(admin_client: AsyncClient, seeded_expenses):
    resp = await admin_client.get("/api/v1/expenses/queue?status=all")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 7


@pytest.mark.asyncio
async def test_queue_filter_by_project(admin_client: AsyncClient, seeded_expenses, seed_data):
    resp = await admin_client.get(f"/api/v1/expenses/queue?project_id={seed_data['project'].id}")
    assert resp.status_code == 200
    data = resp.json()
    for item in data["items"]:
        assert item["project"] is not None


@pytest.mark.asyncio
async def test_queue_filter_by_amount_range(admin_client: AsyncClient, seeded_expenses):
    resp = await admin_client.get("/api/v1/expenses/queue?amount_min=200&amount_max=400")
    assert resp.status_code == 200
    data = resp.json()
    for item in data["items"]:
        assert 200 <= item["amount"] <= 400


@pytest.mark.asyncio
async def test_queue_sort_by_amount(admin_client: AsyncClient, seeded_expenses):
    resp = await admin_client.get("/api/v1/expenses/queue?sort_by=amount&sort_order=desc")
    assert resp.status_code == 200
    data = resp.json()
    amounts = [item["amount"] for item in data["items"]]
    assert amounts == sorted(amounts, reverse=True)


@pytest.mark.asyncio
async def test_queue_confidence_summary(admin_client: AsyncClient, seeded_expenses):
    resp = await admin_client.get("/api/v1/expenses/queue")
    assert resp.status_code == 200
    data = resp.json()
    for item in data["items"]:
        if item.get("confidence_summary"):
            assert "min" in item["confidence_summary"]
            assert "all_high" in item["confidence_summary"]


@pytest.mark.asyncio
async def test_queue_anomaly_count(admin_client: AsyncClient, seeded_expenses):
    resp = await admin_client.get("/api/v1/expenses/queue")
    assert resp.status_code == 200
    data = resp.json()
    anomaly_items = [i for i in data["items"] if i["anomaly_count"] > 0]
    assert len(anomaly_items) >= 1


@pytest.mark.asyncio
async def test_queue_bulk_eligible_field(admin_client: AsyncClient, seeded_expenses):
    resp = await admin_client.get("/api/v1/expenses/queue")
    assert resp.status_code == 200
    data = resp.json()
    eligible = [i for i in data["items"] if i["bulk_eligible"]]
    assert len(eligible) >= 1
    for item in eligible:
        assert item["eta_verified"] is True


@pytest.mark.asyncio
async def test_queue_requires_accountant_or_admin_role(auth_client: AsyncClient, seeded_expenses):
    resp = await auth_client.get("/api/v1/expenses/queue")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_queue_accessible_by_accountant(accountant_client: AsyncClient, seeded_expenses):
    resp = await accountant_client.get("/api/v1/expenses/queue")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_queue_tenant_isolation(admin_client: AsyncClient, seeded_expenses):
    resp = await admin_client.get("/api/v1/expenses/queue")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 5


@pytest.mark.asyncio
async def test_queue_invalid_status(admin_client: AsyncClient, seeded_expenses):
    resp = await admin_client.get("/api/v1/expenses/queue?status=invalid_status")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_queue_invalid_sort_by(admin_client: AsyncClient, seeded_expenses):
    resp = await admin_client.get("/api/v1/expenses/queue?sort_by=invalid_field")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_queue_invalid_sort_order(admin_client: AsyncClient, seeded_expenses):
    resp = await admin_client.get("/api/v1/expenses/queue?sort_order=sideways")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_queue_reversed_amount_range(admin_client: AsyncClient, seeded_expenses):
    resp = await admin_client.get("/api/v1/expenses/queue?amount_min=400&amount_max=200")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_queue_invalid_date(admin_client: AsyncClient, seeded_expenses):
    resp = await admin_client.get("/api/v1/expenses/queue?date_from=not-a-date")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_queue_negative_amount_min(admin_client: AsyncClient, seeded_expenses):
    resp = await admin_client.get("/api/v1/expenses/queue?amount_min=-10")
    assert resp.status_code == 422
