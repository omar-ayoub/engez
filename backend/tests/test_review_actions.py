import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expense import Expense


@pytest.fixture
async def seeded_detail_expense(db_session: AsyncSession, seed_data):
    existing = await db_session.get(Expense, "exp-detail-001")
    if existing:
        return existing

    company_id = seed_data["company"].id
    user_id = seed_data["user"].id
    project_id = seed_data["project"].id

    expense = Expense(
        id="exp-detail-001",
        user_id=user_id,
        company_id=company_id,
        project_id=project_id,
        category_id=seed_data["category"].id,
        amount=1500.0,
        currency="EGP",
        vendor="Cement Egypt",
        vendor_tax_reg="123456789",
        items="Cement bags",
        capture_mode="combined",
        receipt_url="https://r2.example.com/comp-001/receipt/test.jpg",
        voice_transcript="Arabic transcript text",
        status="pending",
        eta_verified=True,
        eta_uuid="eta-uuid-001",
        ai_extraction={"amount": 1500.0, "vendor": "Cement Egypt", "items": "Cement bags"},
        ai_confidence={"amount": 0.98, "vendor": 0.91, "items": 0.84},
        anomaly_flags={"unusual_amount": {"severity": "medium"}},
        review_version=0,
    )
    db_session.add(expense)
    await db_session.commit()
    return expense


@pytest.mark.asyncio
async def test_detail_returns_full_evidence(admin_client: AsyncClient, seeded_detail_expense):
    resp = await admin_client.get(f"/api/v1/expenses/{seeded_detail_expense.id}/review-detail")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == seeded_detail_expense.id
    assert data["amount"] == 1500.0
    assert data["vendor"] == "Cement Egypt"
    assert data["voice_transcript"] == "Arabic transcript text"
    assert data["eta"]["verified"] is True
    assert data["eta"]["uuid"] == "eta-uuid-001"
    assert data["ai_confidence"]["amount"] == 0.98
    assert data["anomaly_flags"]["unusual_amount"]["severity"] == "medium"
    assert "audit_history" in data


@pytest.mark.asyncio
async def test_detail_tenant_scope(admin_client: AsyncClient):
    resp = await admin_client.get("/api/v1/expenses/nonexistent-id/review-detail")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_detail_requires_accountant_or_admin(auth_client: AsyncClient, seeded_detail_expense):
    resp = await auth_client.get(f"/api/v1/expenses/{seeded_detail_expense.id}/review-detail")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_receipt_url_refresh(admin_client: AsyncClient, seeded_detail_expense, db_session):
    expense = Expense(
        id="exp-receipt-001",
        user_id=seeded_detail_expense.user_id,
        company_id=seeded_detail_expense.company_id,
        amount=100.0,
        currency="EGP",
        vendor="Test",
        items="Items",
        capture_mode="receipt",
        receipt_url="test-key-path",
        status="pending",
        review_version=0,
    )
    db_session.add(expense)
    await db_session.commit()

    resp = await admin_client.post(f"/api/v1/expenses/{expense.id}/receipt-url")
    assert resp.status_code in (200, 404)


@pytest.mark.asyncio
async def test_receipt_url_no_receipt(admin_client: AsyncClient, db_session, seed_data):
    expense = Expense(
        id="exp-no-receipt-001",
        user_id=seed_data["user"].id,
        company_id=seed_data["company"].id,
        amount=50.0,
        currency="EGP",
        vendor="Test",
        items="Items",
        capture_mode="manual",
        status="pending",
        review_version=0,
    )
    db_session.add(expense)
    await db_session.commit()

    resp = await admin_client.post(f"/api/v1/expenses/{expense.id}/receipt-url")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_approve_expense(admin_client: AsyncClient, seeded_detail_expense, db_session):
    resp = await admin_client.post(
        f"/api/v1/expenses/{seeded_detail_expense.id}/approve",
        json={"review_version": 0},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "approved"
    assert data["review_version"] == 1
    assert data["reviewed_at"] is not None
    assert "next_pending_id" in data


@pytest.mark.asyncio
async def test_approve_nonexistent(admin_client: AsyncClient):
    resp = await admin_client.post("/api/v1/expenses/nonexistent/approve", json={"review_version": 0})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_approve_stale_version(admin_client: AsyncClient, seeded_detail_expense):
    resp = await admin_client.post(
        f"/api/v1/expenses/{seeded_detail_expense.id}/approve",
        json={"review_version": 99},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_reject_expense(admin_client: AsyncClient, seeded_detail_expense, db_session):
    expense2 = Expense(
        id="exp-reject-001",
        user_id=seeded_detail_expense.user_id,
        company_id=seeded_detail_expense.company_id,
        amount=200.0,
        currency="EGP",
        vendor="Test",
        items="Items",
        capture_mode="manual",
        status="pending",
        review_version=0,
    )
    db_session.add(expense2)
    await db_session.commit()

    resp = await admin_client.post(
        f"/api/v1/expenses/{expense2.id}/reject",
        json={"review_version": 0, "reason": "Receipt is unreadable"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "rejected"
    assert data["rejection_reason"] == "Receipt is unreadable"
    assert data["review_version"] == 1


@pytest.mark.asyncio
async def test_reject_short_reason(admin_client: AsyncClient, seeded_detail_expense):
    resp = await admin_client.post(
        f"/api/v1/expenses/{seeded_detail_expense.id}/reject",
        json={"review_version": 0, "reason": "No"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_reject_whitespace_only_reason(admin_client: AsyncClient, db_session, seed_data):
    expense = Expense(
        id="exp-reject-ws-001",
        user_id=seed_data["user"].id,
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
        f"/api/v1/expenses/{expense.id}/reject",
        json={"review_version": 0, "reason": "     No     "},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_resubmit_rejected(admin_client: AsyncClient, db_session, seed_data):
    expense = Expense(
        id="exp-resubmit-001",
        user_id=seed_data["admin"].id,
        company_id=seed_data["company"].id,
        amount=100.0,
        currency="EGP",
        vendor="Test",
        items="Items",
        capture_mode="manual",
        status="rejected",
        rejection_reason="Bad receipt",
        review_version=1,
    )
    db_session.add(expense)
    await db_session.commit()

    resp = await admin_client.post(
        f"/api/v1/expenses/{expense.id}/resubmit",
        json={"review_version": 1},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pending"
    assert data["review_version"] == 2


@pytest.mark.asyncio
async def test_resubmit_stale_version(admin_client: AsyncClient, db_session, seed_data):
    expense = Expense(
        id="exp-resubmit-stale-001",
        user_id=seed_data["admin"].id,
        company_id=seed_data["company"].id,
        amount=100.0,
        currency="EGP",
        vendor="Test",
        items="Items",
        capture_mode="manual",
        status="rejected",
        rejection_reason="Bad receipt",
        review_version=1,
    )
    db_session.add(expense)
    await db_session.commit()

    resp = await admin_client.post(
        f"/api/v1/expenses/{expense.id}/resubmit",
        json={"review_version": 99},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_resubmit_with_receipt_url(admin_client: AsyncClient, db_session, seed_data):
    expense = Expense(
        id="exp-resubmit-url-001",
        user_id=seed_data["admin"].id,
        company_id=seed_data["company"].id,
        amount=100.0,
        currency="EGP",
        vendor="Test",
        items="Items",
        capture_mode="receipt",
        status="rejected",
        rejection_reason="Bad receipt",
        review_version=1,
        receipt_url="old-key",
    )
    db_session.add(expense)
    await db_session.commit()

    resp = await admin_client.post(
        f"/api/v1/expenses/{expense.id}/resubmit",
        json={"review_version": 1, "changes": {"receipt_url": "new-key"}},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_resubmit_not_owner(auth_client: AsyncClient, db_session, seed_data):
    expense = Expense(
        id="exp-resubmit-notowner-001",
        user_id=seed_data["admin"].id,
        company_id=seed_data["company"].id,
        amount=100.0,
        currency="EGP",
        vendor="Test",
        items="Items",
        capture_mode="manual",
        status="rejected",
        rejection_reason="Bad",
        review_version=1,
    )
    db_session.add(expense)
    await db_session.commit()

    resp = await auth_client.post(
        f"/api/v1/expenses/{expense.id}/resubmit",
        json={"review_version": 1},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_correct_expense_field(admin_client: AsyncClient, db_session, seed_data):
    expense = Expense(
        id="exp-correct-001",
        user_id=seed_data["user"].id,
        company_id=seed_data["company"].id,
        amount=1500.0,
        currency="EGP",
        vendor="Cement Egypt",
        items="Cement bags",
        capture_mode="receipt",
        status="pending",
        ai_extraction={"amount": 1500.0, "vendor": "Cement Egypt"},
        ai_confidence={"amount": 0.98, "vendor": 0.91},
        review_version=0,
    )
    db_session.add(expense)
    await db_session.commit()

    resp = await admin_client.post(
        f"/api/v1/expenses/{expense.id}/correct",
        json={"review_version": 0, "field_name": "vendor", "corrected_value": "Correct Cement Co"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["field_name"] == "vendor"
    assert data["value_after"] == "Correct Cement Co"
    assert data["correction_feedback_created"] is True
    assert data["review_version"] == 1


@pytest.mark.asyncio
async def test_correct_disallowed_field(admin_client: AsyncClient, seeded_detail_expense):
    resp = await admin_client.post(
        f"/api/v1/expenses/{seeded_detail_expense.id}/correct",
        json={"review_version": 0, "field_name": "status", "corrected_value": "approved"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_correct_stale_version(admin_client: AsyncClient, seeded_detail_expense):
    resp = await admin_client.post(
        f"/api/v1/expenses/{seeded_detail_expense.id}/correct",
        json={"review_version": 99, "field_name": "vendor", "corrected_value": "New"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_bulk_approve(admin_client: AsyncClient, db_session, seed_data):
    eligible = Expense(
        id="exp-bulk-001",
        user_id=seed_data["user"].id,
        company_id=seed_data["company"].id,
        amount=200.0,
        currency="EGP",
        vendor="Test",
        items="Items",
        capture_mode="receipt",
        status="pending",
        eta_verified=True,
        ai_confidence={"amount": 0.95, "vendor": 0.9},
        ai_extraction={"amount": 200.0, "vendor": "Test"},
        review_version=0,
    )
    ineligible = Expense(
        id="exp-bulk-002",
        user_id=seed_data["user"].id,
        company_id=seed_data["company"].id,
        amount=100.0,
        currency="EGP",
        vendor="Test",
        items="Items",
        capture_mode="manual",
        status="pending",
        eta_verified=False,
        review_version=0,
    )
    db_session.add_all([eligible, ineligible])
    await db_session.commit()

    resp = await admin_client.post(
        "/api/v1/expenses/bulk-approve",
        json={
            "items": [
                {"id": "exp-bulk-001", "review_version": 0},
                {"id": "exp-bulk-002", "review_version": 0},
                {"id": "nonexistent-id", "review_version": 0},
            ]
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["approved"] == 1
    assert "exp-bulk-001" in data["approved_ids"]
    assert len(data["skipped"]) >= 1
    assert data["bulk_operation_id"] is not None


@pytest.mark.asyncio
async def test_bulk_approve_empty(admin_client: AsyncClient):
    resp = await admin_client.post("/api/v1/expenses/bulk-approve", json={"items": []})
    assert resp.status_code == 200
    data = resp.json()
    assert data["approved"] == 0


@pytest.mark.asyncio
async def test_correct_manual_no_feedback(admin_client: AsyncClient, db_session, seed_data):
    expense = Expense(
        id="exp-manual-001",
        user_id=seed_data["user"].id,
        company_id=seed_data["company"].id,
        amount=100.0,
        currency="EGP",
        vendor="Manual Vendor",
        items="Items",
        capture_mode="manual",
        status="pending",
        review_version=0,
    )
    db_session.add(expense)
    await db_session.commit()

    resp = await admin_client.post(
        f"/api/v1/expenses/{expense.id}/correct",
        json={"review_version": 0, "field_name": "vendor", "corrected_value": "New Vendor"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["correction_feedback_created"] is False


@pytest.mark.asyncio
async def test_concurrent_approve_only_one_succeeds(admin_client: AsyncClient, db_session, seed_data):
    import asyncio

    expense = Expense(
        id="exp-concurrent-001",
        user_id=seed_data["user"].id,
        company_id=seed_data["company"].id,
        amount=500.0,
        currency="EGP",
        vendor="Concurrent Test",
        items="Items",
        capture_mode="manual",
        status="pending",
        review_version=0,
    )
    db_session.add(expense)
    await db_session.commit()

    results = await asyncio.gather(
        admin_client.post(
            f"/api/v1/expenses/{expense.id}/approve",
            json={"review_version": 0},
        ),
        admin_client.post(
            f"/api/v1/expenses/{expense.id}/approve",
            json={"review_version": 0},
        ),
    )

    statuses = [r.status_code for r in results]
    ok_count = statuses.count(200)
    conflict_count = statuses.count(409)
    assert ok_count == 1, f"Expected exactly 1 success, got {ok_count}: {statuses}"
    assert conflict_count == 1, f"Expected exactly 1 conflict, got {conflict_count}: {statuses}"


@pytest.mark.asyncio
async def test_concurrent_reject_only_one_succeeds(admin_client: AsyncClient, db_session, seed_data):
    import asyncio

    expense = Expense(
        id="exp-concurrent-rej-001",
        user_id=seed_data["user"].id,
        company_id=seed_data["company"].id,
        amount=300.0,
        currency="EGP",
        vendor="Concurrent Reject",
        items="Items",
        capture_mode="manual",
        status="pending",
        review_version=0,
    )
    db_session.add(expense)
    await db_session.commit()

    results = await asyncio.gather(
        admin_client.post(
            f"/api/v1/expenses/{expense.id}/reject",
            json={"review_version": 0, "reason": "Rejected by concurrent test"},
        ),
        admin_client.post(
            f"/api/v1/expenses/{expense.id}/reject",
            json={"review_version": 0, "reason": "Rejected by concurrent test"},
        ),
    )

    statuses = [r.status_code for r in results]
    ok_count = statuses.count(200)
    conflict_count = statuses.count(409)
    assert ok_count == 1, f"Expected exactly 1 success, got {ok_count}: {statuses}"
    assert conflict_count == 1, f"Expected exactly 1 conflict, got {conflict_count}: {statuses}"
