"""Tests for company management endpoints (admin-only)."""

import pytest


@pytest.mark.asyncio
class TestGetCompany:
    async def test_get_my_company(self, admin_client):
        resp = await admin_client.get("/api/v1/companies/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "comp-001"
        assert data["name"] == "Test Company"
        assert data["name_ar"] == "شركة اختبار"
        assert data["is_active"] is True

    async def test_get_company_forbidden_for_field_worker(self, auth_client):
        resp = await auth_client.get("/api/v1/companies/me")
        assert resp.status_code == 403


@pytest.mark.asyncio
class TestUpdateCompany:
    async def test_update_company_name(self, admin_client):
        resp = await admin_client.patch(
            "/api/v1/companies/me",
            json={"name": "Updated Company"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Company"

        # Restore
        await admin_client.patch(
            "/api/v1/companies/me",
            json={"name": "Test Company"},
        )

    async def test_update_company_arabic_name(self, admin_client):
        resp = await admin_client.patch(
            "/api/v1/companies/me",
            json={"name_ar": "شركة محدثة"},
        )
        assert resp.status_code == 200
        assert resp.json()["name_ar"] == "شركة محدثة"

        await admin_client.patch(
            "/api/v1/companies/me",
            json={"name_ar": "شركة اختبار"},
        )

    async def test_update_tax_registration(self, admin_client):
        resp = await admin_client.patch(
            "/api/v1/companies/me",
            json={"tax_registration": "TAX-123-456"},
        )
        assert resp.status_code == 200
        assert resp.json()["tax_registration"] == "TAX-123-456"

    async def test_update_company_forbidden_for_field_worker(self, auth_client):
        resp = await auth_client.patch(
            "/api/v1/companies/me",
            json={"name": "Hacked"},
        )
        assert resp.status_code == 403
