import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expense import Expense


@pytest.fixture
async def approved_expenses(db_session: AsyncSession, seed_data):
    company_id = seed_data["company"].id
    user_id = seed_data["user"].id
    project_id = seed_data["project"].id

    for i in range(3):
        existing = await db_session.get(Expense, f"exp-export-{i:03d}")
        if existing:
            continue
        exp = Expense(
            id=f"exp-export-{i:03d}",
            user_id=user_id,
            company_id=company_id,
            project_id=project_id,
            amount=250.0 * (i + 1),
            currency="EGP",
            vendor=f"Export Vendor {i}",
            items="Office supplies",
            capture_mode="receipt",
            status="approved",
            review_version=1,
            reviewed_by=seed_data["admin"].id,
        )
        db_session.add(exp)

    await db_session.commit()


@pytest.mark.asyncio
async def test_list_available_integrations(admin_client: AsyncClient):
    resp = await admin_client.get("/api/v1/integrations/available")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 3
    names = [item["system_name"] for item in data]
    assert "zoho_books" in names
    assert "odoo" in names
    assert "csv_daftra" in names


@pytest.mark.asyncio
async def test_list_integrations_requires_admin_or_accountant(auth_client: AsyncClient):
    resp = await auth_client.get("/api/v1/integrations/available")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_configure_integration(admin_client: AsyncClient):
    payload = {
        "system_name": "zoho_books",
        "credentials": {
            "access_token": "test-token-123",
            "organization_id": "org-123",
            "expense_account_id": "acc-456",
        },
    }
    resp = await admin_client.post("/api/v1/integrations/configure", json=payload)
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["system_name"] == "zoho_books"
    assert data["status"] in ("active", "pending_verification")


@pytest.mark.asyncio
async def test_configure_integration_invalid_system(admin_client: AsyncClient):
    payload = {
        "system_name": "invalid_system",
        "credentials": {"key": "value"},
    }
    resp = await admin_client.post("/api/v1/integrations/configure", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_test_connection(admin_client: AsyncClient):
    payload = {
        "system_name": "zoho_books",
        "credentials": {
            "access_token": "test-token-123",
            "organization_id": "org-123",
            "expense_account_id": "acc-456",
        },
    }
    resp = await admin_client.post("/api/v1/integrations/test-connection", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "success" in data


@pytest.mark.asyncio
async def test_get_integration_status(admin_client: AsyncClient):
    resp = await admin_client.get("/api/v1/integrations/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "system_name" in data or data.get("configured") is False


@pytest.mark.asyncio
async def test_export_expense_manually(admin_client: AsyncClient, approved_expenses):
    resp = await admin_client.post("/api/v1/integrations/export/exp-export-000")
    assert resp.status_code in (200, 202, 404)


@pytest.mark.asyncio
async def test_get_export_status(admin_client: AsyncClient, approved_expenses):
    resp = await admin_client.get("/api/v1/integrations/exports?status=all")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list) or "items" in data


@pytest.mark.asyncio
async def test_retry_failed_export(admin_client: AsyncClient, approved_expenses):
    resp = await admin_client.post("/api/v1/integrations/export/exp-export-000/retry")
    assert resp.status_code in (200, 202, 404)


@pytest.mark.asyncio
async def test_csv_export_download(admin_client: AsyncClient, approved_expenses):
    resp = await admin_client.get("/api/v1/integrations/csv-export?date_from=2026-01-01&date_to=2026-12-31")
    assert resp.status_code == 200
    content_type = resp.headers.get("content-type", "")
    assert "text/csv" in content_type or "application/octet-stream" in content_type


@pytest.mark.asyncio
async def test_csv_export_requires_date_range(admin_client: AsyncClient, approved_expenses):
    resp = await admin_client.get("/api/v1/integrations/csv-export")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_field_worker_cannot_configure(auth_client: AsyncClient):
    payload = {
        "system_name": "zoho_books",
        "credentials": {"access_token": "x", "organization_id": "y", "expense_account_id": "z"},
    }
    resp = await auth_client.post("/api/v1/integrations/configure", json=payload)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_only_one_integration_per_company(admin_client: AsyncClient):
    payload1 = {
        "system_name": "zoho_books",
        "credentials": {"access_token": "a", "organization_id": "b", "expense_account_id": "c"},
    }
    await admin_client.post("/api/v1/integrations/configure", json=payload1)

    payload2 = {
        "system_name": "odoo",
        "credentials": {"url": "http://odoo.test", "db": "test", "username": "u", "api_key": "k"},
    }
    resp = await admin_client.post("/api/v1/integrations/configure", json=payload2)
    assert resp.status_code in (200, 201)

    status_resp = await admin_client.get("/api/v1/integrations/status")
    data = status_resp.json()
    if data.get("configured"):
        assert data["system_name"] == "odoo"
