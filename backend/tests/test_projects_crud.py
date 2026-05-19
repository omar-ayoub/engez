"""Tests for project management endpoints (admin-only CRUD)."""

import pytest


@pytest.mark.asyncio
class TestListProjects:
    async def test_list_projects(self, admin_client):
        resp = await admin_client.get("/api/v1/projects/")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    async def test_list_projects_filter_active(self, admin_client):
        resp = await admin_client.get("/api/v1/projects/?is_active=true")
        assert resp.status_code == 200
        for proj in resp.json()["items"]:
            assert proj["is_active"] is True

    async def test_list_projects_forbidden_for_field_worker(self, auth_client):
        resp = await auth_client.get("/api/v1/projects/")
        assert resp.status_code == 403


@pytest.mark.asyncio
class TestCreateProject:
    async def test_create_project_success(self, admin_client):
        resp = await admin_client.post(
            "/api/v1/projects/",
            json={
                "name": "Tower B",
                "name_ar": "برج ب",
                "code": "TB",
                "budget": "500000.00",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Tower B"
        assert data["code"] == "TB"
        assert data["is_active"] is True

    async def test_create_project_duplicate_code(self, admin_client):
        resp = await admin_client.post(
            "/api/v1/projects/",
            json={
                "name": "Duplicate",
                "name_ar": "مكرر",
                "code": "TA",
            },
        )
        assert resp.status_code == 409

    async def test_create_project_forbidden_for_field_worker(self, auth_client):
        resp = await auth_client.post(
            "/api/v1/projects/",
            json={
                "name": "Blocked",
                "name_ar": "محظور",
                "code": "BL",
            },
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
class TestUpdateProject:
    async def test_update_project_name(self, admin_client):
        resp = await admin_client.patch(
            "/api/v1/projects/proj-001",
            json={"name": "Tower A Updated"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Tower A Updated"

        await admin_client.patch(
            "/api/v1/projects/proj-001",
            json={"name": "Tower A"},
        )

    async def test_update_project_not_found(self, admin_client):
        resp = await admin_client.patch(
            "/api/v1/projects/nonexistent",
            json={"name": "Ghost"},
        )
        assert resp.status_code == 404

    async def test_deactivate_project(self, admin_client):
        resp = await admin_client.patch(
            "/api/v1/projects/proj-001",
            json={"is_active": False},
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

        await admin_client.patch(
            "/api/v1/projects/proj-001",
            json={"is_active": True},
        )
