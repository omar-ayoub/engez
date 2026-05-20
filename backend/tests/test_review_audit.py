import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review_audit_log import ReviewAuditLog
from app.models.expense import Expense


@pytest.fixture
async def seeded_audit_expense(db_session: AsyncSession, seed_data):
    existing = await db_session.get(Expense, "exp-audit-001")
    if existing:
        return existing

    expense = Expense(
        id="exp-audit-001",
        user_id=seed_data["user"].id,
        company_id=seed_data["company"].id,
        amount=500.0,
        currency="EGP",
        vendor="Audit Vendor",
        items="Items",
        capture_mode="manual",
        status="pending",
        review_version=0,
    )
    db_session.add(expense)
    await db_session.commit()
    return expense


@pytest.mark.asyncio
async def test_approve_creates_audit(admin_client: AsyncClient, db_session, seed_data):
    expense = Expense(
        id="exp-audit-approve-001",
        user_id=seed_data["user"].id,
        company_id=seed_data["company"].id,
        amount=500.0,
        currency="EGP",
        vendor="Audit Approve Vendor",
        items="Items",
        capture_mode="manual",
        status="pending",
        review_version=0,
    )
    db_session.add(expense)
    await db_session.commit()

    resp = await admin_client.post(
        f"/api/v1/expenses/{expense.id}/approve",
        json={"review_version": 0},
    )
    assert resp.status_code == 200

    result = await db_session.execute(
        ReviewAuditLog.__table__.select().where(
            ReviewAuditLog.expense_id == expense.id
        )
    )
    rows = result.fetchall()
    assert len(rows) >= 1
    assert rows[0].action_type == "approve"
    assert rows[0].value_before["status"] == "pending"
    assert rows[0].value_after["status"] == "approved"


@pytest.mark.asyncio
async def test_reject_creates_audit_with_reason(admin_client: AsyncClient, db_session, seed_data):
    expense = Expense(
        id="exp-audit-reject-001",
        user_id=seed_data["user"].id,
        company_id=seed_data["company"].id,
        amount=300.0,
        currency="EGP",
        vendor="Audit Reject Vendor",
        items="Items",
        capture_mode="manual",
        status="pending",
        review_version=0,
    )
    db_session.add(expense)
    await db_session.commit()

    resp = await admin_client.post(
        f"/api/v1/expenses/{expense.id}/reject",
        json={"review_version": 0, "reason": "Documentation incomplete"},
    )
    assert resp.status_code == 200

    result = await db_session.execute(
        ReviewAuditLog.__table__.select().where(
            ReviewAuditLog.expense_id == expense.id
        )
    )
    rows = result.fetchall()
    assert len(rows) >= 1
    assert rows[0].action_type == "reject"
    assert rows[0].rejection_reason == "Documentation incomplete"


@pytest.mark.asyncio
async def test_correct_creates_audit(admin_client: AsyncClient, db_session, seed_data):
    expense = Expense(
        id="exp-audit-correct-001",
        user_id=seed_data["user"].id,
        company_id=seed_data["company"].id,
        amount=100.0,
        currency="EGP",
        vendor="Old Vendor",
        items="Items",
        capture_mode="receipt",
        status="pending",
        ai_extraction={"vendor": "Old Vendor"},
        review_version=0,
    )
    db_session.add(expense)
    await db_session.commit()

    resp = await admin_client.post(
        f"/api/v1/expenses/{expense.id}/correct",
        json={"review_version": 0, "field_name": "vendor", "corrected_value": "New Vendor"},
    )
    assert resp.status_code == 200

    result = await db_session.execute(
        ReviewAuditLog.__table__.select().where(
            ReviewAuditLog.expense_id == expense.id
        )
    )
    rows = result.fetchall()
    assert len(rows) >= 1
    assert rows[0].action_type == "correct"
    assert rows[0].field_name == "vendor"


@pytest.mark.asyncio
async def test_audit_history_in_detail(admin_client: AsyncClient, db_session, seed_data):
    expense = Expense(
        id="exp-audit-detail-001",
        user_id=seed_data["user"].id,
        company_id=seed_data["company"].id,
        amount=100.0,
        currency="EGP",
        vendor="V",
        items="Items",
        capture_mode="manual",
        status="pending",
        review_version=0,
    )
    db_session.add(expense)
    await db_session.commit()

    await admin_client.post(
        f"/api/v1/expenses/{expense.id}/approve",
        json={"review_version": 0},
    )

    resp = await admin_client.get(f"/api/v1/expenses/{expense.id}/review-detail")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["audit_history"]) >= 1
    assert data["audit_history"][0]["action_type"] == "approve"
