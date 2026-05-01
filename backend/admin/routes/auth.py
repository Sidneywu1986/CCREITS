"""
Admin Auth Routes — API & HTML
"""

from fastapi import APIRouter, Request, Form
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from typing import Optional
import asyncpg

from ..utils import DB_URL, get_admin_user, sign_cookie, verify_cookie, get_templates
from ..schemas import LoginRequest, LoginResponse
import secrets

api_router = APIRouter()
router = APIRouter()

@api_router.post("/login")
async def api_login(request: LoginRequest):
    from passlib.hash import bcrypt
    
    conn = await asyncpg.connect(DB_URL)
    try:
        
        user = await conn.fetchrow(
            "SELECT id, username, email, password_hash, is_active, is_superuser FROM admin.users WHERE username = $1",
            request.username
        )
        
        if not user:
            return LoginResponse(code=401, message="用户名或密码错误")
        
        if not user["is_active"]:
            return LoginResponse(code=403, message="账号已被禁用")
        
        try:
            if not bcrypt.verify(request.password, user["password_hash"]):
                return LoginResponse(code=401, message="用户名或密码错误")
        except Exception:
            return LoginResponse(code=401, message="密码验证失败")
        
        token = secrets.token_urlsafe(32)
        
        return LoginResponse(
            code=200,
            message="登录成功",
            data={
                "token": token,
                "token_type": "Bearer",
                "expires_in": 86400,
                "user": {
                    "id": user["id"],
                    "username": user["username"],
                    "email": user["email"],
                    "role": "admin" if user["is_superuser"] else "user"
                },
                "roles": ["admin"] if user["is_superuser"] else ["user"],
                "permissions": ["*"] if user["is_superuser"] else ["fund_view", "announcement_view"]
            }
        )


    finally:
        await conn.close()

@api_router.get("/me")
async def api_get_me():
    return {
        "code": 200,
        "message": "success",
        "data": {
            "id": 1,
            "username": "admin",
            "email": "admin@example.com",
            "role": "admin"
        }
    }



@api_router.post("/logout")
async def api_logout():
    return {"code": 200, "message": "已登出"}


# ========== Dashboard API ==========

