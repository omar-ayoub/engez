"""Edge-case tests for expense endpoints — date filtering, auth boundaries, schema validation."""

import uuid

import pytest


pytestmark = pytest.mark.asyncio


class TestDateFiltering:
    async def test_filter_by_from_date(self, auth_client, seed_data):
        resp = await auth_client.get("/api/v1/expenses/?from_date=2020-01-01")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 0

    async def test_filter_by_to_date(self, auth_client, seed_data):
        resp = await auth_client.get("/api/v1/expenses/?to_date=2099-12-31")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 0

    async def test_filter_by_date_range(self, auth_client, seed_data):
        resp = await auth_client.get(
            "/api/v1/expenses/?from_date=2020-01-01&to_date=2099-12-31"
        )
        assert resp.status_code == 200

    async def test_invalid_from_date_returns_422(self, auth_client, seed_data):
        resp = await auth_client.get("/api/v1/expenses/?from_date=not-a-date")
        assert resp.status_code == 422

    async def test_invalid_to_date_returns_422(self, auth_client, seed_data):
        resp = await auth_client.get("/api/v1/expenses/?to_date=31-12-2025")
        assert resp.status_code == 422


class TestExpenseProjectFilter:
    async def test_filter_by_project_id(self, auth_client, seed_data):
        await auth_client.post("/api/v1/expenses/", json={
            "offline_id": str(uuid.uuid4()),
            "amount": 90.0,
            "vendor": "Proj Vendor",
            "items": "sand",
            "capture_mode": "manual",
            "project_id": seed_data["project"].id,
        })

        resp = await auth_client.get(
            f"/api/v1/expenses/?project_id={seed_data['project'].id}"
        )
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["project_id"] == seed_data["project"].id

    async def test_filter_by_nonexistent_project(self, auth_client, seed_data):
        resp = await auth_client.get("/api/v1/expenses/?project_id=nonexistent")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


class TestExpenseUpdateAuth:
    async def test_non_owner_non_admin_cannot_update(self, accountant_client, seed_data, db_session):
        """Accountant cannot update a field worker's expense (not owner, not admin)."""
        from app.models.expense import Expense
        expense = Expense(
            id=str(uuid.uuid4()),
            user_id=seed_data["user"].id,
            company_id=seed_data["company"].id,
            offline_id=str(uuid.uuid4()),
            amount=100.0,
            currency="EGP",
            vendor="Worker Vendor",
            items="bolts",
            capture_mode="manual",
            status="pending",
        )
        db_session.add(expense)
        await db_session.commit()

        resp = await accountant_client.patch(
            f"/api/v1/expenses/{expense.id}",
            json={"amount": 999.0},
        )
        assert resp.status_code == 403

    async def test_admin_can_update_any_expense(self, admin_client, seed_data, db_session):
        """Admin can update anyone's expense."""
        from app.models.expense import Expense
        expense = Expense(
            id=str(uuid.uuid4()),
            user_id=seed_data["user"].id,
            company_id=seed_data["company"].id,
            offline_id=str(uuid.uuid4()),
            amount=100.0,
            currency="EGP",
            vendor="Admin Test",
            items="nails",
            capture_mode="manual",
            status="pending",
        )
        db_session.add(expense)
        await db_session.commit()

        resp = await admin_client.patch(
            f"/api/v1/expenses/{expense.id}",
            json={"vendor": "Admin Override"},
        )
        assert resp.status_code == 200
        assert resp.json()["vendor"] == "Admin Override"


class TestExpenseSchemaValidation:
    async def test_negative_amount_rejected(self, auth_client, seed_data):
        resp = await auth_client.post("/api/v1/expenses/", json={
            "offline_id": str(uuid.uuid4()),
            "amount": -50.0,
            "vendor": "Test",
            "items": "test",
            "capture_mode": "manual",
        })
        assert resp.status_code == 422

    async def test_zero_amount_rejected(self, auth_client, seed_data):
        resp = await auth_client.post("/api/v1/expenses/", json={
            "offline_id": str(uuid.uuid4()),
            "amount": 0,
            "vendor": "Test",
            "items": "test",
            "capture_mode": "manual",
        })
        assert resp.status_code == 422

    async def test_invalid_capture_mode_rejected(self, auth_client, seed_data):
        resp = await auth_client.post("/api/v1/expenses/", json={
            "offline_id": str(uuid.uuid4()),
            "amount": 100.0,
            "vendor": "Test",
            "items": "test",
            "capture_mode": "telekinesis",
        })
        assert resp.status_code == 422

    async def test_missing_offline_id_rejected(self, auth_client, seed_data):
        resp = await auth_client.post("/api/v1/expenses/", json={
            "amount": 100.0,
            "vendor": "Test",
            "items": "test",
        })
        assert resp.status_code == 422


class TestExpensePagination:
    async def test_page_beyond_last_returns_empty(self, auth_client, seed_data):
        resp = await auth_client.get("/api/v1/expenses/?page=9999")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 0

    async def test_per_page_boundary(self, auth_client, seed_data):
        resp = await auth_client.get("/api/v1/expenses/?per_page=1")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) <= 1
