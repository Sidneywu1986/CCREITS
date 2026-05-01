"""
TDD: FastAPI auth dependencies
Run: JWT_SECRET=test pytest tests/core/test_dependencies.py -v
"""
import os
import pytest
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

os.environ.setdefault("JWT_SECRET", "test-secret-key")

from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials

from core.auth.dependencies import (
    get_current_user,
    get_current_active_user,
    require_admin,
    optional_user,
)
from core.auth.jwt import create_access_token


class DummyCredentials:
    def __init__(self, token):
        self.credentials = token


class TestGetCurrentUser:
    def test_valid_token_returns_user(self):
        token = create_access_token("42", "alice", "user", ["fund:read"])
        creds = DummyCredentials(token)
        user = get_current_user(creds)
        assert user.sub == "42"
        assert user.username == "alice"
        assert user.role == "user"

    def test_missing_credentials_raises_401(self):
        with pytest.raises(HTTPException) as exc:
            get_current_user(None)
        assert exc.value.status_code == 401
        assert "缺少认证信息" in exc.value.detail

    def test_invalid_token_raises_401(self):
        creds = DummyCredentials("not.a.token")
        with pytest.raises(HTTPException) as exc:
            get_current_user(creds)
        assert exc.value.status_code == 401


class TestGetCurrentActiveUser:
    def test_active_user_passes(self):
        user = MagicMock()
        user.is_active = True
        result = get_current_active_user(user)
        assert result == user

    def test_inactive_user_raises_403(self):
        user = MagicMock()
        user.is_active = False
        with pytest.raises(HTTPException) as exc:
            get_current_active_user(user)
        assert exc.value.status_code == 403
        assert "禁用" in exc.value.detail


class TestRequireAdmin:
    def test_admin_passes(self):
        user = MagicMock()
        user.role = "admin"
        user.permissions = ["admin:full"]
        result = require_admin(user)
        assert result == user

    def test_non_admin_raises_403(self):
        user = MagicMock()
        user.role = "user"
        user.permissions = ["fund:read"]
        with pytest.raises(HTTPException) as exc:
            require_admin(user)
        assert exc.value.status_code == 403
        assert "管理员" in exc.value.detail

    def test_admin_without_full_permission_fails(self):
        user = MagicMock()
        user.role = "admin"
        user.permissions = ["fund:read"]  # missing admin:full
        with pytest.raises(HTTPException) as exc:
            require_admin(user)
        assert exc.value.status_code == 403


class TestOptionalUser:
    def test_no_credentials_returns_none(self):
        result = optional_user(None)
        assert result is None

    def test_valid_token_returns_user(self):
        token = create_access_token("42", "alice", "user", ["fund:read"])
        creds = DummyCredentials(token)
        result = optional_user(creds)
        assert result is not None
        assert result.sub == "42"

    def test_invalid_token_returns_none(self):
        creds = DummyCredentials("bad.token")
        result = optional_user(creds)
        assert result is None
