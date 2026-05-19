"""Tests for category management endpoints (admin-only CRUD)."""

import pytest


@pytest.mark.asyncio
class TestListCategories:
    async def test_list_categories(self, admin_client):
        resp = await admin_client.get("/api/v1/categories/")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert len(data["items"]) >= 1

    async def test_list_categories_forbidden_for_field_worker(self, auth_client):
        resp = await auth_client.get("/api/v1/categories/")
        assert resp.status_code == 403


@pytest.mark.asyncio
class TestCreateCategory:
    async def test_create_category_success(self, admin_client):
        resp = await admin_client.post(
            "/api/v1/categories/",
            json={
                "name": "safety",
                "name_ar": "سلامة",
                "sort_order": 10,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "safety"
        assert data["name_ar"] == "سلامة"
        assert data["sort_order"] == 10

    async def test_create_category_duplicate_name(self, admin_client):
        resp = await admin_client.post(
            "/api/v1/categories/",
            json={
                "name": "materials",
                "name_ar": "مواد مكررة",
            },
        )
        assert resp.status_code == 409

    async def test_create_category_forbidden_for_field_worker(self, auth_client):
        resp = await auth_client.post(
            "/api/v1/categories/",
            json={
                "name": "blocked",
                "name_ar": "محظور",
            },
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
class TestUpdateCategory:
    async def test_update_category_name(self, admin_client):
        resp = await admin_client.patch(
            "/api/v1/categories/cat-001",
            json={"name_ar": "مواد بناء"},
        )
        assert resp.status_code == 200
        assert resp.json()["name_ar"] == "مواد بناء"

        await admin_client.patch(
            "/api/v1/categories/cat-001",
            json={"name_ar": "مواد"},
        )

    async def test_update_category_not_found(self, admin_client):
        resp = await admin_client.patch(
            "/api/v1/categories/nonexistent",
            json={"name": "Ghost"},
        )
        assert resp.status_code == 404

    async def test_deactivate_category(self, admin_client):
        resp = await admin_client.patch(
            "/api/v1/categories/cat-001",
            json={"is_active": False},
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

        await admin_client.patch(
            "/api/v1/categories/cat-001",
            json={"is_active": True},
        )
