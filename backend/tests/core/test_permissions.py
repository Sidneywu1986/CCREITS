"""
TDD: Permissions module
Run: pytest tests/core/test_permissions.py -v
"""
import pytest
from core.auth.permissions import (
    Permission,
    RolePermissions,
    has_permission,
    get_role_permissions,
)


class TestPermissionEnum:
    def test_all_permissions_have_code_and_label(self):
        for p in Permission:
            assert ":" in p.value
            assert p.label is not None

    def test_common_permissions_exist(self):
        assert Permission.FUND_READ
        assert Permission.FUND_WRITE
        assert Permission.ANNOUNCEMENT_READ
        assert Permission.ADMIN_FULL


class TestRolePermissions:
    def test_admin_has_all_permissions(self):
        perms = get_role_permissions("admin")
        assert Permission.ADMIN_FULL in perms
        assert Permission.FUND_WRITE in perms
        assert Permission.FUND_READ in perms

    def test_user_has_limited_permissions(self):
        perms = get_role_permissions("user")
        assert Permission.FUND_READ in perms
        assert Permission.ANNOUNCEMENT_READ in perms
        assert Permission.ADMIN_FULL not in perms
        assert Permission.FUND_WRITE not in perms

    def test_unknown_role_returns_empty(self):
        perms = get_role_permissions("unknown")
        assert perms == []


class TestHasPermission:
    def test_user_with_permission(self):
        user = type("User", (), {"role": "user", "permissions": ["fund:read"]})
        assert has_permission(user, "fund:read") is True

    def test_user_without_permission(self):
        user = type("User", (), {"role": "user", "permissions": ["fund:read"]})
        assert has_permission(user, "admin:full") is False

    def test_admin_implicitly_has_all(self):
        user = type("User", (), {"role": "admin", "permissions": ["admin:full"]})
        assert has_permission(user, "fund:write") is True

    def test_empty_permissions(self):
        user = type("User", (), {"role": "user", "permissions": []})
        assert has_permission(user, "fund:read") is False
