"""
Admin Users Routes
"""

from fastapi import APIRouter, Form, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from typing import Optional
import asyncpg

from ..utils import DB_URL, get_admin_user, sign_cookie, verify_cookie, sql_placeholders

router = APIRouter()
api_router = APIRouter()

@router.get("/list", response_class=HTMLResponse)
async def users_list(request: Request):
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/admin/login")
    
    from admin_models import UserAdmin
    users = await UserAdmin.all().limit(50)
    
    rows = ""
    for u in users:
        status = '<span class="badge badge-success">启用</span>' if u.is_active else '<span class="badge badge-danger">禁用</span>'
        rows += f"""
        <tr>
            <td>{u.id}</td>
            <td>{u.username}</td>
            <td>{u.email}</td>
            <td>{status}</td>
            <td>{str(u.created_at)[:19]}</td>
            <td>
                <a href="/admin/users/edit/{u.id}" class="btn btn-sm">编辑</a>
            </td>
        </tr>
        """
    
    html = render_admin_page("用户管理", f"""
        <div class="page-header">
            <h2>用户管理</h2>
            <a href="/admin/users/create" class="btn btn-primary">+ 新增用户</a>
        </div>
        <table class="data-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>用户名</th>
                    <th>邮箱</th>
                    <th>状态</th>
                    <th>创建时间</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    """, user)
    return HTMLResponse(content=html)


# ========== 用户创建页面 ==========
@router.get("/create", response_class=HTMLResponse)
async def user_create_page(request: Request):
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/admin/login")

    html = render_admin_page("创建用户", f"""
        <div class="page-header">
            <h2>创建用户</h2>
            <a href="/admin/users/list" class="btn">返回列表</a>
        </div>
        <form method="POST" action="/admin/users/create" class="data-form">
            <div class="form-group">
                <label>用户名 *</label>
                <input type="text" name="username" required placeholder="登录用户名" maxlength="50">
            </div>
            <div class="form-group">
                <label>邮箱 *</label>
                <input type="email" name="email" required placeholder="user@example.com" maxlength="100">
            </div>
            <div class="form-group">
                <label>密码 *</label>
                <input type="password" name="password" required placeholder="设置登录密码" minlength="6">
                <div class="help-text">密码长度至少6位</div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>状态</label>
                    <select name="is_active">
                        <option value="1">启用</option>
                        <option value="0">禁用</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>超级用户</label>
                    <select name="is_superuser">
                        <option value="0">否</option>
                        <option value="1">是</option>
                    </select>
                </div>
            </div>
            <button type="submit" class="btn btn-primary">提交</button>
        </form>
    """, user)
    return HTMLResponse(content=html)


# 创建用户提交
@router.post("/create")
async def user_create_submit(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    is_active: str = Form("1"),
    is_superuser: str = Form("0")
):
    from admin_models import UserAdmin
    from passlib.hash import bcrypt

    # 检查用户名是否已存在
    existing = await UserAdmin.filter(username=username).first()
    if existing:
        return HTMLResponse(content="<script>alert('用户名已存在');history.back();</script>")

    # 检查邮箱是否已存在
    existing_email = await UserAdmin.filter(email=email).first()
    if existing_email:
        return HTMLResponse(content="<script>alert('邮箱已被使用');history.back();</script>")

    await UserAdmin.create(
        username=username,
        email=email,
        password_hash=bcrypt.hash(password),
        is_active=is_active == "1",
        is_superuser=is_superuser == "1"
    )

    return RedirectResponse(url="/admin/users/list", status_code=302)


# ========== 用户编辑页面 ==========
@router.get("/edit/{user_id}", response_class=HTMLResponse)
async def user_edit_page(request: Request, user_id: int):
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/admin/login")

    from admin_models import UserAdmin
    u = await UserAdmin.filter(id=user_id).first()

    if not u:
        return HTMLResponse(content="<script>alert('用户不存在');history.back();</script>")

    html = render_admin_page("编辑用户", f"""
        <div class="page-header">
            <h2>编辑用户</h2>
            <a href="/admin/users/list" class="btn">返回列表</a>
        </div>
        <form method="POST" action="/admin/users/edit/{u.id}" class="data-form">
            <div class="form-group">
                <label>用户名 *</label>
                <input type="text" name="username" value="{u.username}" required maxlength="50">
            </div>
            <div class="form-group">
                <label>邮箱 *</label>
                <input type="email" name="email" value="{u.email}" required maxlength="100">
            </div>
            <div class="form-group">
                <label>新密码（留空则不修改）</label>
                <input type="password" name="password" placeholder="不修改请留空" minlength="6">
                <div class="help-text">如需修改密码，输入新密码（至少6位）</div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>状态</label>
                    <select name="is_active">
                        <option value="1" {'selected' if u.is_active else ''}>启用</option>
                        <option value="0" {'selected' if not u.is_active else ''}>禁用</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>超级用户</label>
                    <select name="is_superuser">
                        <option value="1" {'selected' if u.is_superuser else ''}>是</option>
                        <option value="0" {'selected' if not u.is_superuser else ''}>否</option>
                    </select>
                </div>
            </div>
            <button type="submit" class="btn btn-primary">保存修改</button>
        </form>
    """, user)
    return HTMLResponse(content=html)


# 编辑用户提交
@router.post("/edit/{user_id}")
async def user_edit_submit(
    user_id: int,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(""),
    is_active: str = Form("1"),
    is_superuser: str = Form("0")
):
    from admin_models import UserAdmin
    from passlib.hash import bcrypt
    u = await UserAdmin.filter(id=user_id).first()

    if not u:
        return HTMLResponse(content="<script>alert('用户不存在');history.back();</script>")

    # 检查用户名是否被其他用户占用
    existing = await UserAdmin.filter(username=username).exclude(id=user_id).first()
    if existing:
        return HTMLResponse(content="<script>alert('用户名已被其他用户使用');history.back();</script>")

    # 检查邮箱是否被其他用户占用
    existing_email = await UserAdmin.filter(email=email).exclude(id=user_id).first()
    if existing_email:
        return HTMLResponse(content="<script>alert('邮箱已被其他用户使用');history.back();</script>")

    u.username = username
    u.email = email
    u.is_active = is_active == "1"
    u.is_superuser = is_superuser == "1"

    if password:
        u.password_hash = bcrypt.hash(password)

    await u.save()

    return RedirectResponse(url="/admin/users/list", status_code=302)


def render_admin_page(title, content, username):
    """渲染管理页面框架"""
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>REITs Admin - {title}</title>
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
            padding-bottom: 20px;
            border-bottom: 1px solid #eee;
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
        .page-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
        }}
        .btn {{
            padding: 8px 16px;
            border-radius: 6px;
            text-decoration: none;
            font-size: 14px;
            cursor: pointer;
            border: none;
            display: inline-block;
        }}
        .btn-primary {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        .btn-sm {{ padding: 5px 12px; font-size: 12px; }}
        .btn-danger {{ background: #e74c3c; color: white; }}
        .data-table {{
            width: 100%;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            border-collapse: collapse;
        }}
        .data-table th, .data-table td {{
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        .data-table th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #333;
        }}
        .data-table tr:hover {{ background: #f8f9fa; }}
        .badge {{
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 12px;
        }}
        .badge-success {{ background: #d4edda; color: #155724; }}
        .badge-danger {{ background: #f8d7da; color: #721c24; }}
        .pagination {{
            margin-top: 20px;
            text-align: right;
            color: #666;
        }}
        .data-form {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            max-width: 900px;
        }}
        .form-group {{
            margin-bottom: 20px;
        }}
        .form-group label {{
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 500;
        }}
        .form-group input,
        .form-group textarea,
        .form-group select {{
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
            font-family: inherit;
            background: white;
        }}
        .form-group input:focus,
        .form-group textarea:focus,
        .form-group select:focus {{
            outline: none;
            border-color: #667eea;
        }}
        .form-group textarea {{
            resize: vertical;
            min-height: 80px;
        }}
        .form-row {{
            display: flex;
            gap: 20px;
        }}
        .form-row .form-group {{
            flex: 1;
        }}
        .help-text {{
            font-size: 12px;
            color: #999;
            margin-top: 4px;
        }}
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="sidebar-header">REITs 管理平台</div>
        <a href="/admin/" class="nav-item">仪表盘</a>
        <a href="/admin/users/list" class="nav-item{' active' if '用户' in title else ''}">用户管理</a>
        <a href="/admin/funds/list" class="nav-item{' active' if '基金' in title else ''}">基金管理</a>
        <a href="/admin/announcements/list" class="nav-item">公告管理</a>
        <a href="/admin/roles/list" class="nav-item">角色管理</a>
        <a href="/admin/permissions/list" class="nav-item">权限管理</a>
    </div>
    <div class="main">
        <div class="header">
            <h1>{title}</h1>
            <div class="user-info">
                <span>欢迎, {username}</span>
                <a href="/admin/logout" class="logout">退出</a>
            </div>
        </div>
        {content}
    </div>
</body>
</html>
    """


# ========== 公告管理页面 ==========

# 公告根路径重定向到列表
