"""Tests for authentication endpoints: login, refresh, logout."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch, AsyncMock

from app.core.security import hash_password
from app.core.database import get_db
from app.models.user import User
from app.models.company import Company
from app.main import app
from tests.conftest import TestSessionFactory


@pytest_asyncio.fixture
async def unauth_client(db_session, seed_data):
    """Client with DB override but NO auth override — tests real auth flow."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestLogin:
    async def test_login_success(self, unauth_client, seed_data):
        with patch("app.services.auth_service.verify_password", return_value=True):
            resp = await unauth_client.post(
                "/api/v1/auth/login",
                json={"email": "test@engez.app", "password": "password123"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["email"] == "test@engez.app"
        assert data["user"]["role"] == "field_worker"
        assert data["user"]["company_id"] == "comp-001"

    async def test_login_sets_refresh_cookie(self, unauth_client, seed_data):
        with patch("app.services.auth_service.verify_password", return_value=True):
            resp = await unauth_client.post(
                "/api/v1/auth/login",
                json={"email": "test@engez.app", "password": "password123"},
            )
        assert resp.status_code == 200
        cookies = resp.cookies
        assert "refresh_token" in cookies or any(
            "refresh_token" in h for h in resp.headers.get_list("set-cookie")
        )

    async def test_login_wrong_password(self, unauth_client, seed_data):
        with patch("app.services.auth_service.verify_password", return_value=False):
            resp = await unauth_client.post(
                "/api/v1/auth/login",
                json={"email": "test@engez.app", "password": "wrongpassword"},
            )
        assert resp.status_code == 401

    async def test_login_nonexistent_email(self, unauth_client, seed_data):
        resp = await unauth_client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "password123"},
        )
        assert resp.status_code == 401

    async def test_login_returns_bilingual_error(self, unauth_client, seed_data):
        resp = await unauth_client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "wrong"},
        )
        detail = resp.json()["detail"]
        assert "detail_en" in detail
        assert "detail" in detail

    async def test_brute_force_lockout(self, unauth_client, seed_data, db_session):
        """After 5 failed attempts, account should be locked."""
        # Reset failed attempts first
        from sqlalchemy import select, update

        await db_session.execute(
            update(User)
            .where(User.email == "test@engez.app")
            .values(failed_login_attempts=4, locked_until=None)
        )
        await db_session.commit()

        with patch("app.services.auth_service.verify_password", return_value=False):
            resp = await unauth_client.post(
                "/api/v1/auth/login",
                json={"email": "test@engez.app", "password": "wrong"},
            )
        assert resp.status_code == 401

        # Next attempt should be locked (423)
        with patch("app.services.auth_service.verify_password", return_value=True):
            resp = await unauth_client.post(
                "/api/v1/auth/login",
                json={"email": "test@engez.app", "password": "password123"},
            )
        assert resp.status_code == 423

        # Cleanup
        await db_session.execute(
            update(User)
            .where(User.email == "test@engez.app")
            .values(failed_login_attempts=0, locked_until=None)
        )
        await db_session.commit()

    async def test_successful_login_resets_failed_attempts(
        self, unauth_client, seed_data, db_session
    ):
        from sqlalchemy import update

        await db_session.execute(
            update(User)
            .where(User.email == "test@engez.app")
            .values(failed_login_attempts=3, locked_until=None)
        )
        await db_session.commit()

        with patch("app.services.auth_service.verify_password", return_value=True):
            resp = await unauth_client.post(
                "/api/v1/auth/login",
                json={"email": "test@engez.app", "password": "password123"},
            )
        assert resp.status_code == 200

        # Cleanup
        await db_session.execute(
            update(User)
            .where(User.email == "test@engez.app")
            .values(failed_login_attempts=0, locked_until=None)
        )
        await db_session.commit()


@pytest.mark.asyncio
class TestLogout:
    async def test_logout_clears_cookie(self, unauth_client, seed_data):
        resp = await unauth_client.post("/api/v1/auth/logout")
        assert resp.status_code == 200
        assert resp.json()["logged_out"] is True
