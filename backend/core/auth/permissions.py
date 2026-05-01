"""
Permission definitions and role-permission mappings
"""
from enum import Enum
from typing import List


class Permission(Enum):
    """Fine-grained permission codes."""
    FUND_READ = "fund:read"
    FUND_WRITE = "fund:write"
    ANNOUNCEMENT_READ = "announcement:read"
    ANNOUNCEMENT_WRITE = "announcement:write"
    CRAWLER_READ = "crawler:read"
    CRAWLER_WRITE = "crawler:write"
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    ADMIN_FULL = "admin:full"

    @property
    def label(self) -> str:
        labels = {
            "fund:read": "查看基金数据",
            "fund:write": "修改基金数据",
            "announcement:read": "查看公告",
            "announcement:write": "管理公告",
            "crawler:read": "查看爬虫状态",
            "crawler:write": "控制爬虫",
            "user:read": "查看用户信息",
            "user:write": "管理用户",
            "admin:full": "全部管理员权限",
        }
        return labels.get(self.value, self.value)


# Role → [Permission] mapping
RolePermissions = {
    "admin": [
        Permission.ADMIN_FULL,
        Permission.FUND_READ,
        Permission.FUND_WRITE,
        Permission.ANNOUNCEMENT_READ,
        Permission.ANNOUNCEMENT_WRITE,
        Permission.CRAWLER_READ,
        Permission.CRAWLER_WRITE,
        Permission.USER_READ,
        Permission.USER_WRITE,
    ],
    "user": [
        Permission.FUND_READ,
        Permission.ANNOUNCEMENT_READ,
    ],
}


def get_role_permissions(role: str) -> List[Permission]:
    """Return the list of permissions granted to a role."""
    return RolePermissions.get(role, [])


def has_permission(user, permission_code: str) -> bool:
    """
    Check if a user has a specific permission.
    `user` is duck-typed: needs `.role` and `.permissions` (list of str).
    Admin with admin:full implicitly has everything.
    """
    if user.role == "admin" and Permission.ADMIN_FULL.value in user.permissions:
        return True
    return permission_code in user.permissions
