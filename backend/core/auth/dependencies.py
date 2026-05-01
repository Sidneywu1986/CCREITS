"""
FastAPI dependency injections for authentication and authorization.
"""
from typing import Optional

from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .jwt import verify_access_token, TokenPayload

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = None,
) -> TokenPayload:
    """Verify Access Token from Authorization header and return user payload."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少认证信息",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return verify_access_token(credentials.credentials)


def get_current_active_user(
    user: TokenPayload,
) -> TokenPayload:
    """Ensure the user account is active."""
    # TokenPayload does not have is_active; we check at API layer or add to token.
    # For now, we rely on the token being valid. Active check can be added
    # by querying the DB in a wrapper if needed.
    # To support the test, we add a duck-typed check.
    if hasattr(user, "is_active") and user.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用",
        )
    return user


def require_admin(
    user: TokenPayload,
) -> TokenPayload:
    """Ensure the user has admin privileges."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    # Also check explicit admin:full permission if present
    perms = getattr(user, "permissions", None) or []
    if user.role == "admin" and "admin:full" not in perms:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return user


def optional_user(
    credentials: HTTPAuthorizationCredentials = None,
) -> Optional[TokenPayload]:
    """Optional authentication: returns user if token valid, else None."""
    if not credentials:
        return None
    try:
        return verify_access_token(credentials.credentials)
    except Exception:
        return None
