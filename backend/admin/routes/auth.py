"""
Admin Auth Routes — JWT Authentication API
Endpoints: register, login, refresh, logout, me, change-password
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
import asyncpg

from ..utils import DB_URL, get_templates
from ..schemas import (
    LoginRequest, LoginResponse,
    RegisterRequest, RegisterResponse,
    RefreshResponse, LogoutResponse,
    MeResponse, ChangePasswordRequest,
)
from core.auth.jwt import (
    create_access_token, create_refresh_token,
    verify_access_token, refresh_access_token, revoke_refresh_token,
)
from core.auth.password import hash_password, verify_password
from core.auth.permissions import get_role_permissions
from core.db_pool import get_pool

api_router = APIRouter()
router = APIRouter()

# ── In-memory rate-limiting store (Wave 2: simple; Wave 4: replace with Redis) ──
_login_attempts: dict = {}  # ip -> [(timestamp, count)]
_register_attempts: dict = {}


def _check_rate_limit(store: dict, key: str, max_attempts: int, window_seconds: int) -> bool:
    now = datetime.now(timezone.utc).timestamp()
    attempts = store.get(key, [])
    attempts = [t for t in attempts if now - t < window_seconds]
    store[key] = attempts
    return len(attempts) < max_attempts


def _record_attempt(store: dict, key: str):
    now = datetime.now(timezone.utc).timestamp()
    store.setdefault(key, []).append(now)


# ── Helper: build user permissions from role ──
def _build_user_permissions(role: str, is_superuser: bool) -> list:
    if is_superuser:
        return ["*"]
    perms = get_role_permissions(role)
    return [p.value for p in perms]


# ── Register ──
@api_router.post("/register", response_model=RegisterResponse)
async def api_register(request: RegisterRequest):
    # Rate limit
    if not _check_rate_limit(_register_attempts, "global", 5, 3600):
        return RegisterResponse(code=429, message="注册尝试过多，请 1 小时后重试")

    pool = await get_pool()
    conn = await pool.acquire()
    try:
        # Check username uniqueness
        existing = await conn.fetchrow(
            "SELECT id FROM admin.users WHERE username = $1", request.username
        )
        if existing:
            return RegisterResponse(code=409, message="用户名已存在")

        # Check email uniqueness
        existing_email = await conn.fetchrow(
            "SELECT id FROM admin.users WHERE email = $1", request.email
        )
        if existing_email:
            return RegisterResponse(code=409, message="邮箱已被注册")

        # Create user
        pwd_hash = hash_password(request.password)
        user_id = await conn.fetchval(
            """INSERT INTO admin.users (username, email, password_hash, is_active, is_superuser)
               VALUES ($1, $2, $3, true, false) RETURNING id""",
            request.username, request.email, pwd_hash
        )

        _record_attempt(_register_attempts, "global")
        return RegisterResponse(
            code=201,
            message="注册成功",
            data={"id": user_id, "username": request.username, "email": request.email}
        )
    finally:
        await pool.release(conn)


# ── Login ──
@api_router.post("/login", response_model=LoginResponse)
async def api_login(request: LoginRequest, response: Response):
    client_ip = "global"  # Simplified; in production use X-Forwarded-For

    pool = await get_pool()
    conn = await pool.acquire()
    try:
        user = await conn.fetchrow(
            """SELECT id, username, email, password_hash, is_active, is_superuser
               FROM admin.users WHERE username = $1""",
            request.username
        )

        if not user:
            _record_attempt(_login_attempts, client_ip)
            return LoginResponse(code=401, message="用户名或密码错误")

        # Check account lock (graceful if columns not migrated yet)
        locked_until = user.get("locked_until")
        if locked_until and locked_until > datetime.now(timezone.utc):
            return LoginResponse(code=403, message="账号已被锁定，请稍后重试")

        if not user["is_active"]:
            return LoginResponse(code=403, message="账号已被禁用")

        # Rate limit check (only count failed attempts in limit)
        if not _check_rate_limit(_login_attempts, client_ip, 5, 900):
            return LoginResponse(code=429, message="登录尝试过多，请 15 分钟后重试")

        # Verify password
        if not verify_password(request.password, user["password_hash"]):
            _record_attempt(_login_attempts, client_ip)
            return LoginResponse(code=401, message="用户名或密码错误")

        # Success: update last_login (graceful if column missing)
        try:
            await conn.execute(
                "UPDATE admin.users SET last_login = NOW() WHERE id = $1",
                user["id"]
            )
        except Exception:
            pass

        # Build permissions
        role = "admin" if user["is_superuser"] else "user"
        permissions = _build_user_permissions(role, user["is_superuser"])

        # Create tokens
        access_token = create_access_token(
            str(user["id"]), user["username"], role, permissions
        )
        refresh_token = create_refresh_token(str(user["id"]))

        # Store refresh token JTI in DB (Wave 2: memory; will use DB in production)
        # For now we rely on in-memory tracking in jwt.py

        # Set refresh token cookie
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            samesite="lax",
            path="/api/v1/auth",
            max_age=604800,
            secure=False,  # TODO: enable in production
        )

        _record_attempt(_login_attempts, client_ip)
        return LoginResponse(
            code=200,
            message="登录成功",
            data={
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 900,
                "user": {
                    "id": user["id"],
                    "username": user["username"],
                    "email": user["email"],
                    "role": role,
                    "permissions": permissions,
                }
            }
        )
    finally:
        await pool.release(conn)


# ── Refresh ──
@api_router.post("/refresh", response_model=RefreshResponse)
async def api_refresh(request: Request, response: Response):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        return RefreshResponse(code=401, message="缺少 Refresh Token")

    try:
        new_access, new_refresh = refresh_access_token(refresh_token)
    except Exception as e:
        return RefreshResponse(code=401, message=str(e))

    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        samesite="lax",
        path="/api/v1/auth",
        max_age=604800,
        secure=False,
    )

    return RefreshResponse(
        code=200,
        message="刷新成功",
        data={"access_token": new_access, "token_type": "Bearer", "expires_in": 900}
    )


# ── Logout ──
@api_router.post("/logout", response_model=LogoutResponse)
async def api_logout(request: Request, response: Response):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        try:
            from core.auth.jwt import verify_refresh_token
            payload = verify_refresh_token(refresh_token)
            revoke_refresh_token(payload.sub)
        except Exception:
            pass

    response.delete_cookie(key="refresh_token", path="/api/v1/auth")
    return LogoutResponse(code=200, message="已登出")


# ── Me ──
@api_router.get("/me", response_model=MeResponse)
async def api_me(request: Request):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return MeResponse(code=401, message="缺少认证信息")

    token = auth_header[7:]
    try:
        payload = verify_access_token(token)
    except Exception as e:
        return MeResponse(code=401, message=str(e))

    pool = await get_pool()
    conn = await pool.acquire()
    try:
        user = await conn.fetchrow(
            "SELECT id, username, email, is_superuser FROM admin.users WHERE id = $1",
            int(payload.sub)
        )
        if not user:
            return MeResponse(code=404, message="用户不存在")

        role = "admin" if user["is_superuser"] else "user"
        permissions = _build_user_permissions(role, user["is_superuser"])

        return MeResponse(
            code=200,
            message="success",
            data={
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "role": role,
                "permissions": permissions,
            }
        )
    finally:
        await pool.release(conn)


# ── Change Password ──
@api_router.post("/change-password")
async def api_change_password(request: Request, body: ChangePasswordRequest):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"code": 401, "message": "缺少认证信息"})

    token = auth_header[7:]
    try:
        payload = verify_access_token(token)
    except Exception as e:
        return JSONResponse(status_code=401, content={"code": 401, "message": str(e)})

    pool = await get_pool()
    conn = await pool.acquire()
    try:
        user = await conn.fetchrow(
            "SELECT id, password_hash FROM admin.users WHERE id = $1",
            int(payload.sub)
        )
        if not user:
            return JSONResponse(status_code=404, content={"code": 404, "message": "用户不存在"})

        if not verify_password(body.old_password, user["password_hash"]):
            return JSONResponse(status_code=401, content={"code": 401, "message": "原密码错误"})

        new_hash = hash_password(body.new_password)
        await conn.execute(
            "UPDATE admin.users SET password_hash = $1 WHERE id = $2",
            new_hash, user["id"]
        )

        # Revoke all refresh tokens for this user
        revoke_refresh_token(str(user["id"]))

        return JSONResponse(status_code=200, content={"code": 200, "message": "密码修改成功，请重新登录"})
    finally:
        await pool.release(conn)
