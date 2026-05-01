"""
Admin Login Routes
"""

from fastapi import APIRouter, Form, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from typing import Optional
import asyncpg

from ..utils import DB_URL, get_admin_user, sign_cookie, verify_cookie, sql_placeholders

router = APIRouter()
api_router = APIRouter()

@router.post("/api/v1/auth/login")
async def api_login(request: LoginRequest):
    from passlib.hash import bcrypt
    
    conn = await asyncpg.connect(DB_DSN)
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
@router.get("/api/v1/auth/me")
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


@router.post("/api/v1/auth/logout")
async def api_logout():
    return {"code": 200, "message": "已登出"}


# ========== Dashboard API ==========
@router.get("/api/v1/dashboard/stats")
async def api_dashboard_stats():
    from datetime import date
    
    conn = await asyncpg.connect(DB_DSN)
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
        await conn.close()
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
@router.get("/api/v1/funds")
async def api_list_funds(page: int = 1, page_size: int = 20, keyword: str = ""):
    
    conn = await asyncpg.connect(DB_DSN)
    try:
        
        offset = (page - 1) * page_size
        
        if keyword:
            count_query = "SELECT COUNT(*) as cnt FROM business.funds WHERE fund_code LIKE $1 OR fund_name LIKE $2"
            count_row = await conn.fetchrow(count_query, f"%{keyword}%", f"%{keyword}%")
            
            data_query = """
                SELECT id, fund_code, fund_name, exchange, ipo_date, nav, status
                FROM business.funds 
                WHERE fund_code LIKE $1 OR fund_name LIKE $2
                LIMIT $3 OFFSET $4
            """
            rows = await conn.fetch(data_query, f"%{keyword}%", f"%{keyword}%", page_size, offset)
        else:
            count_query = "SELECT COUNT(*) as cnt FROM business.funds"
            count_row = await conn.fetchrow(count_query)
            
            data_query = "SELECT id, fund_code, fund_name, exchange, ipo_date, nav, status FROM business.funds LIMIT $1 OFFSET $2"
            rows = await conn.fetch(data_query, page_size, offset)
        
        total = count_row["cnt"] if count_row else 0
        
        return {
            "code": 200,
            "message": "success",
            "data": [
                {
                    "id": row["id"],
                    "fund_code": row["fund_code"],
                    "fund_name": row["fund_name"],
                    "exchange": row["exchange"] or "SH",
                    "ipo_date": row["ipo_date"],
                    "nav": row["nav"],
                    "status": row["status"] or "active"
                }
                for row in rows
            ],
            "total": total,
            "page": page,
            "page_size": page_size
        }


    finally:
        await conn.close()
# ========== 公告 API ==========
@router.get("/api/v1/announcements")
async def api_list_announcements(page: int = 1, page_size: int = 20, fund_code: str = ""):
    
    conn = await asyncpg.connect(DB_DSN)
    try:
        
        offset = (page - 1) * page_size
        
        if fund_code:
            count_query = "SELECT COUNT(*) as cnt FROM business.announcements WHERE fund_code = $1"
            count_row = await conn.fetchrow(count_query, fund_code)
            
            data_query = """
                SELECT id, fund_code, title, publish_date, category, source_url
                FROM business.announcements 
                WHERE fund_code = $1
                ORDER BY publish_date DESC
                LIMIT $2 OFFSET $3
            """
            rows = await conn.fetch(data_query, fund_code, page_size, offset)
        else:
            count_query = "SELECT COUNT(*) as cnt FROM business.announcements"
            count_row = await conn.fetchrow(count_query)
            
            data_query = """
                SELECT id, fund_code, title, publish_date, category, source_url
                FROM business.announcements 
                ORDER BY publish_date DESC
                LIMIT $1 OFFSET $2
            """
            rows = await conn.fetch(data_query, page_size, offset)
        
        total = count_row["cnt"] if count_row else 0
        
        return {
            "code": 200,
            "message": "success",
            "data": [
                {
                    "id": row["id"],
                    "fund_code": row["fund_code"] or "",
                    "title": row["title"],
                    "publish_date": row["publish_date"],
                    "announcement_type": row["category"],
                    "pdf_url": row["source_url"]
                }
                for row in rows
            ],
            "total": total,
            "page": page,
            "page_size": page_size
        }


    finally:
        await conn.close()
# ========== 用户管理 API ==========
@router.get("/api/v1/users")
async def api_list_users(page: int = 1, page_size: int = 10, keyword: str = ""):
    
    conn = await asyncpg.connect(DB_DSN)
    try:
        
        offset = (page - 1) * page_size
        
        if keyword:
            count_query = "SELECT COUNT(*) as cnt FROM admin.users WHERE username LIKE $1 OR email LIKE $2"
            count_row = await conn.fetchrow(count_query, f"%{keyword}%", f"%{keyword}%")
            
            data_query = """
                SELECT id, username, email, is_active, is_superuser, created_at
                FROM admin.users 
                WHERE username LIKE $1 OR email LIKE $2
                LIMIT $3 OFFSET $4
            """
            rows = await conn.fetch(data_query, f"%{keyword}%", f"%{keyword}%", page_size, offset)
        else:
            count_query = "SELECT COUNT(*) as cnt FROM admin.users"
            count_row = await conn.fetchrow(count_query)
            
            data_query = "SELECT id, username, email, is_active, is_superuser, created_at FROM admin.users LIMIT $1 OFFSET $2"
            rows = await conn.fetch(data_query, page_size, offset)
        
        total = count_row["cnt"] if count_row else 0
        
        return {
            "code": 200,
            "message": "success",
            "data": [
                {
                    "id": row["id"],
                    "username": row["username"],
                    "email": row["email"],
                    "role": "admin" if row["is_superuser"] else "user",
                    "is_active": bool(row["is_active"]),
                    "created_at": row["created_at"]
                }
                for row in rows
            ],
            "total": total,
            "page": page,
            "page_size": page_size
        }


    finally:
        await conn.close()
# ========== 角色管理 API ==========
@router.get("/api/v1/roles")
async def api_list_roles():
    return {
        "code": 200,
        "message": "success",
        "data": [
            {"id": 1, "name": "admin", "description": "超级管理员", "permissions": ["*"]},
            {"id": 2, "name": "editor", "description": "编辑", "permissions": ["fund_view", "fund_edit", "announcement_view", "announcement_edit"]},
            {"id": 3, "name": "viewer", "description": "访客", "permissions": ["fund_view", "announcement_view"]}
        ]
    }


# ========== 权限管理 API ==========
@router.get("/api/v1/permissions")
async def api_list_permissions():
    return {
        "code": 200,
        "message": "success",
        "data": [
            {"id": 1, "name": "基金查看", "code": "fund_view", "category": "数据管理"},
            {"id": 2, "name": "基金编辑", "code": "fund_edit", "category": "数据管理"},
            {"id": 3, "name": "公告查看", "code": "announcement_view", "category": "数据管理"},
            {"id": 4, "name": "公告编辑", "code": "announcement_edit", "category": "数据管理"},
            {"id": 5, "name": "用户管理", "code": "user_manage", "category": "系统管理"},
            {"id": 6, "name": "系统配置", "code": "system_config", "category": "系统管理"},
        ]
    }


# ========== 登录页面 ==========
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>REITs Admin - 登录</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-box {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            width: 400px;
        }
        h1 { text-align: center; color: #333; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; color: #555; font-weight: 500; }
        input {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
        }
        input:focus { outline: none; border-color: #667eea; }
        button {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 16px;
            cursor: pointer;
        }
        button:hover { opacity: 0.9; }
        .error { color: #e74c3c; text-align: center; margin-top: 15px; }
    </style>
</head>
<body>
    <div class="login-box">
        <h1>REITs 管理平台</h1>
        <form method="POST" action="/admin/login">
            <div class="form-group">
                <label>用户名</label>
                <input type="text" name="username" placeholder="admin" required>
            </div>
            <div class="form-group">
                <label>密码</label>
                <input type="password" name="password" placeholder="admin123" required>
            </div>
            <button type="submit">登录</button>
            <p style="text-align:center;margin-top:15px;color:#999;font-size:12px;">
                默认账号: admin / admin123
            </p>
        </form>
    </div>
</body>
</html>
    """
    return HTMLResponse(content=html)


@router.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    from admin_models import UserAdmin
    from passlib.hash import bcrypt
    
    user = await UserAdmin.filter(username=username).first()
    if not user or not bcrypt.verify(password, user.password_hash):
        return HTMLResponse(content="<script>alert('用户名或密码错误');history.back();</script>")
    
    response = RedirectResponse(url="/admin/", status_code=302)
    response.set_cookie(key="admin_user", value=_sign_cookie(username), httponly=True, samesite="lax")
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/admin/login", status_code=302)
    response.delete_cookie("admin_user")
    return response


# ========== 管理后台首页 ==========
@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/admin/login")
    
    from admin_models import UserAdmin, FundAdmin, AnnouncementAdmin
    
    users = await UserAdmin.all().count()
    funds = await FundAdmin.all().count()
    announcements = await AnnouncementAdmin.all().count()
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>REITs Admin - 仪表盘</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f7fa;
        }}
        .sidebar {{
            position: fixed;
            left: 0; top: 0;
            width: 220px;
            height: 100vh;
            background: #1a1a2e;
            color: white;
        }}
        .sidebar-header {{
            padding: 20px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            font-size: 18px;
            font-weight: bold;
        }}
        .nav-item {{
            display: block;
            padding: 15px 20px;
            color: rgba(255,255,255,0.8);
            text-decoration: none;
            border-left: 3px solid transparent;
            transition: all 0.3s;
        }}
        .nav-item:hover, .nav-item.active {{
            background: rgba(255,255,255,0.1);
            border-left-color: #667eea;
            color: white;
        }}
        .main {{
            margin-left: 220px;
            padding: 30px;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }}
        .stat-value {{
            font-size: 36px;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }}
        .stat-label {{
            color: #666;
            font-size: 14px;
        }}
        .user-info {{
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        .logout {{
            color: #e74c3c;
            text-decoration: none;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="sidebar-header">REITs 管理平台</div>
        <a href="/admin/" class="nav-item active">仪表盘</a>
        <a href="/admin/users/list" class="nav-item">用户管理</a>
        <a href="/admin/funds/list" class="nav-item">基金管理</a>
        <a href="/admin/announcements/list" class="nav-item">公告管理</a>
        <a href="/admin/roles/list" class="nav-item">角色管理</a>
        <a href="/admin/permissions/list" class="nav-item">权限管理</a>
    </div>
    <div class="main">
        <div class="header">
            <h1>仪表盘</h1>
            <div class="user-info">
                <span>欢迎, {user}</span>
                <a href="/admin/logout" class="logout">退出</a>
            </div>
        </div>
        <div class="stats">
            <div class="stat-card">
                <div class="stat-label">用户总数</div>
                <div class="stat-value">{users}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">基金总数</div>
                <div class="stat-value">{funds}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">公告总数</div>
                <div class="stat-value">{announcements}</div>
            </div>
        </div>
    </div>
</body>
</html>
    """
    return HTMLResponse(content=html)


# ========== 基金列表页面（增强版） ==========
