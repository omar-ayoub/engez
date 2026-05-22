"""Edge-case tests for Integration & Analytics (Spec 04) — TDD review pass."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expense import Expense
from app.models.export_record import ExportRecord
from app.models.integration import IntegrationConfig
from app.services.crypto import encrypt


@pytest.fixture
async def integration_config(db_session: AsyncSession, seed_data):
    """Seed an active integration config + approved expense for export tests."""
    company_id = seed_data["company"].id
    user_id = seed_data["user"].id
    project_id = seed_data["project"].id

    from sqlalchemy import select
    existing_result = await db_session.execute(
        select(IntegrationConfig).where(IntegrationConfig.company_id == company_id)
    )
    existing = existing_result.scalar_one_or_none()
    if not existing:
        import json
        creds = json.dumps({"access_token": "t", "organization_id": "o", "expense_account_id": "a"})
        config = IntegrationConfig(
            company_id=company_id,
            system_name="zoho_books",
            encrypted_credentials=encrypt(company_id, creds),
            status="active",
        )
        db_session.add(config)
    elif existing.status != "active":
        existing.status = "active"

    exp_id = "exp-integ-edge-001"
    existing_exp = await db_session.get(Expense, exp_id)
    if not existing_exp:
        exp = Expense(
            id=exp_id,
            user_id=user_id,
            company_id=company_id,
            project_id=project_id,
            amount=500.0,
            currency="EGP",
            vendor="Edge Vendor",
            items="Supplies",
            capture_mode="receipt",
            status="approved",
            review_version=1,
            reviewed_by=seed_data["admin"].id,
        )
        db_session.add(exp)

    await db_session.commit()
    return {"company_id": company_id, "expense_id": exp_id}


# ── CSV Export date validation ───────────────────────────────

@pytest.mark.asyncio
async def test_csv_export_invalid_date_returns_422(admin_client: AsyncClient):
    """Bad date format should return 422, not 500."""
    resp = await admin_client.get(
        "/api/v1/integrations/csv-export?date_from=not-a-date&date_to=2026-12-31"
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_csv_export_inverted_range_returns_422(admin_client: AsyncClient):
    """date_from > date_to should return 422."""
    resp = await admin_client.get(
        "/api/v1/integrations/csv-export?date_from=2026-12-31&date_to=2026-01-01"
    )
    assert resp.status_code == 422


# ── Manual export tenant isolation ───────────────────────────

@pytest.mark.asyncio
async def test_manual_export_duplicate_check_scoped_to_company(
    admin_client: AsyncClient,
    db_session: AsyncSession,
    integration_config,
):
    """ExportRecord duplicate check must include company_id filter."""
    expense_id = integration_config["expense_id"]

    # Plant a "success" export record under a DIFFERENT company
    other_company = f"other-{uuid.uuid4().hex[:8]}"
    foreign_record = ExportRecord(
        id=str(uuid.uuid4()),
        company_id=other_company,
        expense_id=expense_id,  # same expense_id, different company
        system_name="zoho_books",
        status="success",
        attempt_count=1,
    )
    db_session.add(foreign_record)
    await db_session.commit()

    # manual_export should NOT be blocked by the other company's record
    resp = await admin_client.post(f"/api/v1/integrations/export/{expense_id}")
    # Should be 202 (accepted) or exporter error — NOT 409 "Already exported"
    assert resp.status_code != 409, "Duplicate check leaked across tenants"


# ── Retry export actually re-executes ────────────────────────

@pytest.mark.asyncio
async def test_retry_export_does_not_stay_pending(
    admin_client: AsyncClient,
    db_session: AsyncSession,
    integration_config,
):
    """After manual retry, the record should NOT be stuck in 'pending' limbo."""
    company_id = integration_config["company_id"]
    expense_id = integration_config["expense_id"]

    # Create a failed export record
    record = ExportRecord(
        id=str(uuid.uuid4()),
        company_id=company_id,
        expense_id=expense_id,
        system_name="zoho_books",
        status="failed",
        attempt_count=1,
        error_message="Simulated failure",
    )
    db_session.add(record)
    await db_session.commit()

    resp = await admin_client.post(f"/api/v1/integrations/export/{expense_id}/retry")
    assert resp.status_code == 202

    # After retry, status should be either "success" or "failed" (re-executed)
    # — NOT stuck at "pending"
    await db_session.refresh(record)
    assert record.status in ("success", "failed"), (
        f"Retry left record in '{record.status}' — expected re-execution"
    )


# ── Analytics export edge cases ──────────────────────────────

@pytest.mark.asyncio
async def test_analytics_export_missing_params(admin_client: AsyncClient):
    """Export without required params returns 422."""
    resp = await admin_client.get("/api/v1/analytics/export")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_analytics_summary_default_period(admin_client: AsyncClient):
    """Summary endpoint works with default period."""
    resp = await admin_client.get("/api/v1/analytics/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_spend" in data


@pytest.mark.asyncio
async def test_anomaly_metrics_custom_period(admin_client: AsyncClient):
    """Anomaly metrics accepts custom period."""
    resp = await admin_client.get("/api/v1/anomalies/metrics?days=7")
    assert resp.status_code == 200
    data = resp.json()
    assert data["period_days"] == 7


@pytest.mark.asyncio
async def test_anomaly_metrics_exceeds_max_days(admin_client: AsyncClient):
    """days > 365 returns 422."""
    resp = await admin_client.get("/api/v1/anomalies/metrics?days=999")
    assert resp.status_code == 422
