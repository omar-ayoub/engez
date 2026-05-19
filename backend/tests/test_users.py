"""Tests for user management endpoints (admin-only CRUD)."""

import pytest


@pytest.mark.asyncio
class TestListUsers:
    async def test_list_users_returns_paginated(self, admin_client):
        resp = await admin_client.get("/api/v1/users/")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert data["total"] >= 1

    async def test_list_users_filter_by_role(self, admin_client):
        resp = await admin_client.get("/api/v1/users/?role=admin")
        assert resp.status_code == 200
        data = resp.json()
        for user in data["items"]:
            assert user["role"] == "admin"

    async def test_list_users_filter_by_active(self, admin_client):
        resp = await admin_client.get("/api/v1/users/?is_active=true")
        assert resp.status_code == 200
        for user in resp.json()["items"]:
            assert user["is_active"] is True

    async def test_list_users_pagination(self, admin_client):
        resp = await admin_client.get("/api/v1/users/?page=1&per_page=1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 1
        assert data["page"] == 1
        assert data["per_page"] == 1

    async def test_list_users_forbidden_for_field_worker(self, auth_client):
        resp = await auth_client.get("/api/v1/users/")
        assert resp.status_code == 403


@pytest.mark.asyncio
class TestCreateUser:
    async def test_create_user_success(self, admin_client):
        resp = await admin_client.post(
            "/api/v1/users/",
            json={
                "email": "newworker@engez.app",
                "name": "New Worker",
                "name_ar": "عامل جديد",
                "password": "securepass123",
                "role": "field_worker",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "newworker@engez.app"
        assert data["role"] == "field_worker"
        assert data["is_active"] is True
        assert "hashed_password" not in data

    async def test_create_user_duplicate_email(self, admin_client):
        resp = await admin_client.post(
            "/api/v1/users/",
            json={
                "email": "test@engez.app",
                "name": "Duplicate",
                "name_ar": "مكرر",
                "password": "securepass123",
                "role": "field_worker",
            },
        )
        assert resp.status_code == 409

    async def test_create_user_short_password_rejected(self, admin_client):
        resp = await admin_client.post(
            "/api/v1/users/",
            json={
                "email": "short@engez.app",
                "name": "Short Pass",
                "name_ar": "كلمة سر قصيرة",
                "password": "abc",
                "role": "field_worker",
            },
        )
        assert resp.status_code == 422

    async def test_create_user_invalid_role_rejected(self, admin_client):
        resp = await admin_client.post(
            "/api/v1/users/",
            json={
                "email": "badrole@engez.app",
                "name": "Bad Role",
                "name_ar": "صلاحية خاطئة",
                "password": "securepass123",
                "role": "superadmin",
            },
        )
        assert resp.status_code == 422

    async def test_create_user_forbidden_for_field_worker(self, auth_client):
        resp = await auth_client.post(
            "/api/v1/users/",
            json={
                "email": "blocked@engez.app",
                "name": "Blocked",
                "name_ar": "محظور",
                "password": "securepass123",
                "role": "field_worker",
            },
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
class TestUpdateUser:
    async def test_update_user_name(self, admin_client):
        resp = await admin_client.patch(
            "/api/v1/users/user-001",
            json={"name": "Updated Name"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"

    async def test_update_user_not_found(self, admin_client):
        resp = await admin_client.patch(
            "/api/v1/users/nonexistent-id",
            json={"name": "Ghost"},
        )
        assert resp.status_code == 404

    async def test_update_user_role(self, admin_client):
        resp = await admin_client.patch(
            "/api/v1/users/user-001",
            json={"role": "accountant"},
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "accountant"

        # Restore original role
        await admin_client.patch(
            "/api/v1/users/user-001",
            json={"role": "field_worker"},
        )
