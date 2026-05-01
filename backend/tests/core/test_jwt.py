"""
TDD: JWT module
Run: JWT_SECRET=test pytest tests/core/test_jwt.py -v
"""
import os
import pytest
from datetime import datetime, timedelta, timezone

os.environ.setdefault("JWT_SECRET", "test-secret-key-for-unit-tests-only")

from core.auth.jwt import (
    create_access_token,
    create_refresh_token,
    verify_access_token,
    verify_refresh_token,
    refresh_access_token,
    revoke_refresh_token,
    TokenPayload,
)


class TestCreateAccessToken:
    def test_creates_valid_string(self):
        token = create_access_token("42", "alice", "user", ["fund:read"])
        assert isinstance(token, str)
        assert len(token) > 50
        parts = token.split(".")
        assert len(parts) == 3

    def test_payload_contains_expected_fields(self):
        token = create_access_token("42", "alice", "user", ["fund:read"])
        payload = verify_access_token(token)
        assert payload.sub == "42"
        assert payload.username == "alice"
        assert payload.role == "user"
        assert "fund:read" in payload.permissions
        assert payload.type == "access"
        assert payload.iss == "reits-api"
        assert payload.aud == "reits-platform"

    def test_default_expiry_is_15_minutes(self):
        before = datetime.now(timezone.utc)
        token = create_access_token("42", "alice", "user", [])
        payload = verify_access_token(token)
        after = datetime.now(timezone.utc)
        delta = payload.exp - payload.iat
        assert 800 < delta.total_seconds() < 1000  # ~15min ± margin

    def test_custom_expiry(self):
        token = create_access_token("42", "alice", "user", [], expires_delta=timedelta(hours=2))
        payload = verify_access_token(token)
        delta = payload.exp - payload.iat
        assert 7100 < delta.total_seconds() < 7300  # ~2h


class TestCreateRefreshToken:
    def test_creates_valid_string(self):
        token = create_refresh_token("42")
        assert isinstance(token, str)
        assert len(token) > 50

    def test_payload_contains_expected_fields(self):
        token = create_refresh_token("42")
        payload = verify_refresh_token(token)
        assert payload.sub == "42"
        assert payload.type == "refresh"
        assert payload.jti is not None
        assert len(payload.jti) == 36  # UUID v4

    def test_default_expiry_is_7_days(self):
        token = create_refresh_token("42")
        payload = verify_refresh_token(token)
        delta = payload.exp - payload.iat
        assert 6 * 86400 < delta.total_seconds() < 8 * 86400


class TestVerifyAccessToken:
    def test_valid_token_returns_payload(self):
        token = create_access_token("42", "alice", "user", ["fund:read"])
        payload = verify_access_token(token)
        assert payload.sub == "42"

    def test_expired_token_raises_401(self):
        token = create_access_token("42", "alice", "user", [], expires_delta=timedelta(seconds=-1))
        with pytest.raises(Exception) as exc_info:
            verify_access_token(token)
        assert "expired" in str(exc_info.value).lower() or "401" in str(exc_info.value)

    def test_invalid_token_raises(self):
        with pytest.raises(Exception):
            verify_access_token("not.a.token")

    def test_tampered_token_raises(self):
        token = create_access_token("42", "alice", "user", [])
        tampered = token[:-5] + "xxxxx"
        with pytest.raises(Exception):
            verify_access_token(tampered)

    def test_wrong_secret_raises(self):
        token = create_access_token("42", "alice", "user", [])
        # Temporarily change secret
        old_secret = os.environ.get("JWT_SECRET")
        os.environ["JWT_SECRET"] = "different-secret"
        try:
            with pytest.raises(Exception):
                verify_access_token(token)
        finally:
            if old_secret:
                os.environ["JWT_SECRET"] = old_secret


class TestRefreshAccessToken:
    def test_returns_new_access_and_refresh(self):
        refresh = create_refresh_token("42")
        new_access, new_refresh = refresh_access_token(refresh)
        assert isinstance(new_access, str)
        assert isinstance(new_refresh, str)
        # Verify new access token works
        payload = verify_access_token(new_access)
        assert payload.sub == "42"

    def test_revokes_old_refresh_token(self):
        refresh = create_refresh_token("42")
        refresh_access_token(refresh)
        with pytest.raises(Exception) as exc_info:
            refresh_access_token(refresh)
        assert "revoked" in str(exc_info.value).lower() or "invalid" in str(exc_info.value)

    def test_expired_refresh_raises(self):
        refresh = create_refresh_token("42", expires_delta=timedelta(seconds=-1))
        with pytest.raises(Exception):
            refresh_access_token(refresh)


class TestRevokeRefreshToken:
    def test_makes_token_invalid(self):
        refresh = create_refresh_token("42")
        revoke_refresh_token("42")
        with pytest.raises(Exception) as exc_info:
            refresh_access_token(refresh)
        assert "revoked" in str(exc_info.value).lower() or "invalid" in str(exc_info.value)
