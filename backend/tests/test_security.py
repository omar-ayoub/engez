"""Tests for JWT token creation/verification and password utilities."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_access_token,
    verify_refresh_token,
    hash_password,
    verify_password,
    TokenPayload,
    RefreshPayload,
)


class TestAccessToken:
    def test_create_and_verify_roundtrip(self):
        token = create_access_token("user-1", "comp-1", "field_worker")
        payload = verify_access_token(token)
        assert payload.sub == "user-1"
        assert payload.company_id == "comp-1"
        assert payload.role == "field_worker"
        assert isinstance(payload, TokenPayload)

    def test_contains_expiry(self):
        token = create_access_token("user-1", "comp-1", "admin")
        payload = verify_access_token(token)
        assert payload.exp > datetime.now(timezone.utc)

    def test_invalid_token_raises(self):
        with pytest.raises(ValueError, match="Invalid access token"):
            verify_access_token("garbage.token.value")

    def test_empty_token_raises(self):
        with pytest.raises(ValueError):
            verify_access_token("")

    def test_expired_token_raises(self):
        with patch("app.core.security.settings") as mock_settings:
            mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = -1
            mock_settings.SECRET_KEY = "test-secret"
            from jose import jwt

            payload = {
                "sub": "user-1",
                "company_id": "comp-1",
                "role": "admin",
                "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            }
            expired_token = jwt.encode(payload, "test-secret", algorithm="HS256")
        with pytest.raises(ValueError, match="Invalid access token"):
            verify_access_token(expired_token)

    def test_all_roles_accepted(self):
        for role in ("field_worker", "accountant", "admin"):
            token = create_access_token("u1", "c1", role)
            payload = verify_access_token(token)
            assert payload.role == role


class TestRefreshToken:
    def test_create_and_verify_roundtrip(self):
        token = create_refresh_token("user-1")
        payload = verify_refresh_token(token)
        assert payload.sub == "user-1"
        assert isinstance(payload, RefreshPayload)

    def test_contains_expiry(self):
        token = create_refresh_token("user-1")
        payload = verify_refresh_token(token)
        assert payload.exp > datetime.now(timezone.utc)

    def test_invalid_token_raises(self):
        with pytest.raises(ValueError, match="Invalid refresh token"):
            verify_refresh_token("garbage.token")

    def test_access_token_rejected_as_refresh(self):
        access = create_access_token("user-1", "comp-1", "admin")
        with pytest.raises(ValueError, match="Not a refresh token"):
            verify_refresh_token(access)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        hashed = hash_password("mypassword123")
        assert verify_password("mypassword123", hashed)

    def test_wrong_password_fails(self):
        hashed = hash_password("correctpassword")
        assert not verify_password("wrongpassword", hashed)

    def test_hash_is_not_plaintext(self):
        hashed = hash_password("secret")
        assert hashed != "secret"
        assert hashed.startswith("$2b$")

    def test_different_hashes_for_same_password(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # bcrypt salt makes hashes unique
