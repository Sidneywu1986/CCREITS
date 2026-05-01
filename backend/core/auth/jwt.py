"""
JWT token creation, verification, refresh, and revocation.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional

from jose import jwt as jose_jwt, JWTError, ExpiredSignatureError
from pydantic import BaseModel

# In-memory store for revoked refresh token JTIs.
# Will be replaced by database lookup in Wave 2.
_revoked_jtis: set = set()

# In-memory store for active refresh token JTIs per user.
# Maps user_id -> current_jti
_user_refresh_jtis: dict = {}


class TokenPayload(BaseModel):
    sub: str
    type: str
    iat: datetime
    exp: datetime
    # access-only fields
    username: Optional[str] = None
    role: Optional[str] = None
    permissions: Optional[list] = None
    iss: Optional[str] = None
    aud: Optional[str] = None
    # refresh-only field
    jti: Optional[str] = None


def _secret() -> str:
    return os.environ.get("JWT_SECRET", "")


def _algorithm() -> str:
    return os.environ.get("JWT_ALGORITHM", "HS256")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_timestamp(dt: datetime) -> int:
    return int(dt.timestamp())


def _from_timestamp(ts: int) -> datetime:
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def create_access_token(
    user_id: str,
    username: str,
    role: str,
    permissions: list,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token."""
    if expires_delta is None:
        expires_delta = timedelta(minutes=15)
    now = _now()
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "permissions": permissions,
        "type": "access",
        "iat": _to_timestamp(now),
        "exp": _to_timestamp(now + expires_delta),
        "iss": "reits-api",
        "aud": "reits-platform",
    }
    return jose_jwt.encode(payload, _secret(), algorithm=_algorithm())


def create_refresh_token(
    user_id: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT refresh token with a unique JTI."""
    if expires_delta is None:
        expires_delta = timedelta(days=7)
    now = _now()
    jti = str(uuid.uuid4())
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": jti,
        "iat": _to_timestamp(now),
        "exp": _to_timestamp(now + expires_delta),
    }
    # Track active JTI for this user
    _user_refresh_jtis[str(user_id)] = jti
    return jose_jwt.encode(payload, _secret(), algorithm=_algorithm())


def _decode(token: str) -> dict:
    """Decode and verify a JWT token."""
    return jose_jwt.decode(
        token,
        _secret(),
        algorithms=[_algorithm()],
        issuer="reits-api",
        audience="reits-platform",
        options={"verify_iss": False, "verify_aud": False},  # refresh tokens don't have iss/aud
    )


def _dict_to_payload(data: dict) -> TokenPayload:
    return TokenPayload(
        sub=data.get("sub", ""),
        type=data.get("type", ""),
        iat=_from_timestamp(data["iat"]),
        exp=_from_timestamp(data["exp"]),
        username=data.get("username"),
        role=data.get("role"),
        permissions=data.get("permissions"),
        iss=data.get("iss"),
        aud=data.get("aud"),
        jti=data.get("jti"),
    )


def verify_access_token(token: str) -> TokenPayload:
    """Verify an access token and return its payload."""
    try:
        data = jose_jwt.decode(
            token,
            _secret(),
            algorithms=[_algorithm()],
            issuer="reits-api",
            audience="reits-platform",
        )
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token 已过期")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token 无效")

    if data.get("type") != "access":
        raise HTTPException(status_code=401, detail="Token 类型错误")
    return _dict_to_payload(data)


def verify_refresh_token(token: str) -> TokenPayload:
    """Verify a refresh token and return its payload."""
    try:
        data = jose_jwt.decode(token, _secret(), algorithms=[_algorithm()])
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh Token 已过期")
    except JWTError:
        raise HTTPException(status_code=401, detail="Refresh Token 无效")

    if data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Token 类型错误")

    jti = data.get("jti")
    if jti and jti in _revoked_jtis:
        raise HTTPException(status_code=401, detail="Refresh Token has been revoked")

    return _dict_to_payload(data)


def refresh_access_token(refresh_token: str) -> Tuple[str, str]:
    """
    Exchange a valid refresh token for a new access + refresh token pair.
    Rotates the refresh token (old one becomes invalid).
    """
    payload = verify_refresh_token(refresh_token)
    user_id = payload.sub

    # Check rotation: current JTI must match the one stored for this user
    current_jti = _user_refresh_jtis.get(user_id)
    if current_jti and payload.jti != current_jti:
        raise HTTPException(status_code=401, detail="Refresh Token has been revoked or is invalid")

    # Revoke old refresh token
    if payload.jti:
        _revoked_jtis.add(payload.jti)

    # Create new token pair
    new_access = create_access_token(user_id, "", "", [])
    new_refresh = create_refresh_token(user_id)
    return new_access, new_refresh


def revoke_refresh_token(user_id: str) -> None:
    """Revoke all refresh tokens for a user."""
    jti = _user_refresh_jtis.pop(str(user_id), None)
    if jti:
        _revoked_jtis.add(jti)


# Need HTTPException for verify functions
from fastapi import HTTPException
