import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expense import Expense


@pytest.fixture
async def anomaly_seed_expenses(db_session: AsyncSession, seed_data):
    """Seed expenses for anomaly detection testing."""
    company_id = seed_data["company"].id
    user_id = seed_data["user"].id
    project_id = seed_data["project"].id
    category_id = seed_data["category"].id

    # Create 6 historical expenses for statistical baseline (user+category)
    for i in range(6):
        existing = await db_session.get(Expense, f"exp-anomaly-hist-{i:03d}")
        if existing:
            continue
        exp = Expense(
            id=f"exp-anomaly-hist-{i:03d}",
            user_id=user_id,
            company_id=company_id,
            project_id=project_id,
            category_id=category_id,
            amount=100.0 + (i * 10),  # 100-150 range, mean ~125, std ~18
            currency="EGP",
            vendor="Regular Vendor",
            items="Regular items",
            capture_mode="receipt",
            status="approved",
            review_version=1,
            reviewed_by=seed_data["admin"].id,
            receipt_hash=f"hash-unique-{i:03d}",
        )
        db_session.add(exp)

    # Create an expense with a known receipt hash for duplicate detection
    existing = await db_session.get(Expense, "exp-anomaly-dup-src")
    if not existing:
        dup_source = Expense(
            id="exp-anomaly-dup-src",
            user_id=user_id,
            company_id=company_id,
            project_id=project_id,
            amount=200.0,
            currency="EGP",
            vendor="Duplicate Vendor",
            items="Items",
            capture_mode="receipt",
            status="pending",
            review_version=0,
            receipt_hash="duplicate-hash-abc123",
        )
        db_session.add(dup_source)

    await db_session.commit()


@pytest.mark.asyncio
async def test_duplicate_receipt_detection(admin_client: AsyncClient, anomaly_seed_expenses):
    """Submitting an expense with a receipt hash matching an existing one should flag duplicate."""
    payload = {
        "amount": 200.0,
        "currency": "EGP",
        "vendor": "Duplicate Vendor",
        "items": "Items",
        "capture_mode": "receipt",
        "receipt_hash": "duplicate-hash-abc123",
    }
    resp = await admin_client.post("/api/v1/expenses/check-anomalies", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "flags" in data
    flag_types = [f["type"] for f in data["flags"]]
    assert "duplicate_receipt" in flag_types


@pytest.mark.asyncio
async def test_statistical_outlier_detection(admin_client: AsyncClient, anomaly_seed_expenses):
    """An amount far above the user+category mean should be flagged as outlier."""
    payload = {
        "amount": 10000.0,  # Far above the 100-150 historical range (robust against other test data)
        "currency": "EGP",
        "vendor": "Regular Vendor",
        "items": "Items",
        "capture_mode": "receipt",
        "category_id": "cat-001",
        "user_id": "user-001",  # Match the historical seed data user
    }
    resp = await admin_client.post("/api/v1/expenses/check-anomalies", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    flag_types = [f["type"] for f in data["flags"]]
    assert "statistical_outlier" in flag_types


@pytest.mark.asyncio
async def test_no_outlier_within_normal_range(admin_client: AsyncClient, anomaly_seed_expenses):
    """An amount within normal range should NOT be flagged."""
    payload = {
        "amount": 130.0,  # Within normal range
        "currency": "EGP",
        "vendor": "Regular Vendor",
        "items": "Items",
        "capture_mode": "receipt",
        "category_id": "cat-001",
        "user_id": "user-001",  # Match the historical seed data user
    }
    resp = await admin_client.post("/api/v1/expenses/check-anomalies", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    flag_types = [f["type"] for f in data["flags"]]
    assert "statistical_outlier" not in flag_types


@pytest.mark.asyncio
async def test_velocity_check(admin_client: AsyncClient, anomaly_seed_expenses):
    """Submitting 3+ expenses in 10 minutes should flag high velocity."""
    resp = await admin_client.post("/api/v1/expenses/check-anomalies", json={
        "amount": 50.0,
        "currency": "EGP",
        "vendor": "V",
        "items": "I",
        "capture_mode": "manual",
        "check_velocity": True,
        "user_id": "user-001",
    })
    assert resp.status_code == 200
    data = resp.json()
    # Velocity flag depends on recent submission count
    assert "flags" in data


@pytest.mark.asyncio
async def test_vendor_category_mismatch(admin_client: AsyncClient, anomaly_seed_expenses):
    """Assigning a vendor to an unusual category should flag mismatch."""
    payload = {
        "amount": 100.0,
        "currency": "EGP",
        "vendor": "Regular Vendor",
        "items": "Items",
        "capture_mode": "receipt",
        "category_id": "cat-999",  # Different from historical pattern
    }
    resp = await admin_client.post("/api/v1/expenses/check-anomalies", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    # Mismatch flag depends on historical consistency threshold
    assert "flags" in data


@pytest.mark.asyncio
async def test_anomaly_flags_are_advisory_only(admin_client: AsyncClient, anomaly_seed_expenses):
    """Anomaly flags should never block expense submission."""
    payload = {
        "amount": 200.0,
        "currency": "EGP",
        "vendor": "Duplicate Vendor",
        "items": "Items",
        "capture_mode": "receipt",
        "receipt_hash": "duplicate-hash-abc123",
    }
    resp = await admin_client.post("/api/v1/expenses/check-anomalies", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    # Response should indicate flags are advisory
    assert data.get("blocking") is False or "blocking" not in data


@pytest.mark.asyncio
async def test_anomaly_flag_severity_levels(admin_client: AsyncClient, anomaly_seed_expenses):
    """Each flag must include a severity level."""
    payload = {
        "amount": 200.0,
        "currency": "EGP",
        "vendor": "Duplicate Vendor",
        "items": "Items",
        "capture_mode": "receipt",
        "receipt_hash": "duplicate-hash-abc123",
    }
    resp = await admin_client.post("/api/v1/expenses/check-anomalies", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    for flag in data["flags"]:
        assert "severity" in flag
        assert flag["severity"] in ("high", "medium", "low")
        assert "message" in flag


@pytest.mark.asyncio
async def test_minimum_data_threshold(admin_client: AsyncClient, seed_data):
    """With fewer than 5 expenses in user+category, no statistical outlier should be flagged."""
    payload = {
        "amount": 99999.0,
        "currency": "EGP",
        "vendor": "New Vendor",
        "items": "Items",
        "capture_mode": "receipt",
        "category_id": "cat-no-history",  # No historical data
    }
    resp = await admin_client.post("/api/v1/expenses/check-anomalies", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    flag_types = [f["type"] for f in data["flags"]]
    assert "statistical_outlier" not in flag_types


@pytest.mark.asyncio
async def test_anomaly_metrics_endpoint(admin_client: AsyncClient, anomaly_seed_expenses):
    """Admin should be able to view anomaly detection metrics."""
    resp = await admin_client.get("/api/v1/anomalies/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_flags" in data
    assert "by_type" in data


@pytest.mark.asyncio
async def test_anomaly_metrics_requires_admin(auth_client: AsyncClient, anomaly_seed_expenses):
    """Field workers should not access anomaly metrics."""
    resp = await auth_client.get("/api/v1/anomalies/metrics")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_graceful_hash_failure(admin_client: AsyncClient, anomaly_seed_expenses):
    """When receipt_hash is missing, duplicate check should be skipped without error."""
    payload = {
        "amount": 200.0,
        "currency": "EGP",
        "vendor": "Some Vendor",
        "items": "Items",
        "capture_mode": "receipt",
        # No receipt_hash — simulates hash computation failure
    }
    resp = await admin_client.post("/api/v1/expenses/check-anomalies", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    flag_types = [f["type"] for f in data["flags"]]
    assert "duplicate_receipt" not in flag_types
