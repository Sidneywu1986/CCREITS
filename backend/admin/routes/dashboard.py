"""
Admin Dashboard Routes
"""

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from typing import Optional
import asyncpg

from ..utils import DB_URL, get_admin_user, sign_cookie, verify_cookie, sql_placeholders
from core.auth.dependencies import require_admin
from core.auth.jwt import TokenPayload
from core.db_pool import get_pool

router = APIRouter()
api_router = APIRouter()

@router.get("/api/v1/dashboard/stats")
async def api_dashboard_stats(user: TokenPayload = Depends(require_admin)):
    from datetime import date
    
    pool = await get_pool()
    conn = await pool.acquire()
    try:
        
        row = await conn.fetchrow("SELECT COUNT(*) as cnt FROM business.funds")
        fund_count = row["cnt"] if row else 0
        
        row = await conn.fetchrow("SELECT COUNT(*) as cnt FROM business.announcements")
        announcement_count = row["cnt"] if row else 0
        
        today = str(date.today())
        row = await conn.fetchrow("SELECT COUNT(*) as cnt FROM business.announcements WHERE date(publish_date) = $1", today)
        today_announcements = row["cnt"] if row else 0
        
        row = await conn.fetchrow("SELECT COUNT(*) as cnt FROM admin.users")
        user_count = row["cnt"] if row else 0
        
        return {
            "code": 200,
            "message": "success",
            "data": {
                "fund_count": fund_count,
                "announcement_count": announcement_count,
                "today_announcements": today_announcements,
                "user_count": user_count,
                "announcement_trend": []
            }
        }


    finally:
        await pool.release(conn)
# ========== 菜单 API ==========
@router.get("/api/v1/menu/routes")
async def api_menu_routes():
    return {
        "code": 200,
        "message": "success",
        "data": [
            {"name": "仪表盘", "code": "dashboard", "path": "/dashboard", "icon": "DashboardOutlined", "order": 1},
            {"name": "基金管理", "code": "funds", "path": "/funds", "icon": "FundOutlined", "order": 2},
            {"name": "公告管理", "code": "announcements", "path": "/announcements", "icon": "FileTextOutlined", "order": 3},
            {
                "name": "系统管理", 
                "code": "system", 
                "path": "/system", 
                "icon": "SettingOutlined", 
                "order": 4,
                "children": [
                    {"name": "用户管理", "code": "users", "path": "/system/users", "icon": "TeamOutlined", "order": 1},
                    {"name": "角色管理", "code": "roles", "path": "/system/roles", "icon": "SafetyOutlined", "order": 2},
                    {"name": "权限管理", "code": "permissions", "path": "/system/permissions", "icon": "SafetyOutlined", "order": 3},
                ]
            }
        ]
    }


# ========== 基金 API ==========
