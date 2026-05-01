"""
Admin Roles Routes
"""

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from typing import Optional
import asyncpg

from ..utils import DB_URL, get_admin_user, sign_cookie, verify_cookie, sql_placeholders

router = APIRouter()
api_router = APIRouter()

@router.get("/list", response_class=HTMLResponse)
async def roles_list(request: Request, page: int = 1, limit: int = 20, search: str = ""):
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/admin/login")

    from admin_models import RoleAdmin, PermissionAdmin

    # 搜索功能
    query = RoleAdmin.all()
    if search:
        query = query.filter(
            RoleAdmin.name.contains(search) |
            RoleAdmin.description.contains(search)
        )

    offset = (page - 1) * limit
    roles = await query.offset(offset).limit(limit).order_by("-created_at")
    total = await query.count()

    # 获取每个角色的权限数量
    role_permissions = {}
    for role in roles:
        role_permissions[role.id] = await PermissionAdmin.filter(
            id__in=await role.permissions.all().values_list("id", flat=True)
        ).count()

    rows = ""
    for r in roles:
        rows += f"""
        <tr>
            <td>{r.id}</td>
            <td>{r.name}</td>
            <td>{r.description or '-'}</td>
            <td>{role_permissions.get(r.id, 0)} 个权限</td>
            <td>{str(r.created_at)[:19]}</td>
            <td>
                <a href="/admin/roles/edit/{r.id}" class="btn btn-sm">编辑</a>
                <a href="/admin/roles/permissions/{r.id}" class="btn btn-sm btn-info">权限分配</a>
                <a href="/admin/roles/delete/{r.id}" class="btn btn-sm btn-danger" onclick="return confirm('确定删除?')">删除</a>
            </td>
        </tr>
        """

    # 搜索表单
    search_form = f"""
    <div class="search-box">
        <form method="GET" action="/admin/roles/list">
            <input type="text" name="search" placeholder="搜索角色名称或描述" value="{search}">
            <button type="submit" class="btn btn-primary">搜索</button>
            <a href="/admin/roles/list" class="btn">清空</a>
        </form>
    </div>
    """

    html = render_admin_page("角色管理", f"""
        <div class="page-header">
            <h2>角色管理</h2>
            {search_form}
            <a href="/admin/roles/create" class="btn btn-primary">+ 新增角色</a>
        </div>
        <table class="data-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>角色名称</th>
                    <th>描述</th>
                    <th>权限数量</th>
                    <th>创建时间</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
        <div class="pagination">
            <span>共 {total} 条记录</span>
        </div>
    """, user)
    return HTMLResponse(content=html)


# 创建角色页面
@router.get("/create", response_class=HTMLResponse)
async def role_create_page(request: Request):
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/admin/login")

    html = render_admin_page("创建角色", f"""
        <div class="page-header">
            <h2>创建角色</h2>
            <a href="/admin/roles/list" class="btn">返回列表</a>
        </div>
        <form method="POST" action="/admin/roles/create" class="data-form">
            <div class="form-group">
                <label>角色名称 *</label>
                <input type="text" name="name" required placeholder="例如: 编辑员">
            </div>
            <div class="form-group">
                <label>描述</label>
                <textarea name="description" rows="3" placeholder="角色描述"></textarea>
            </div>
            <button type="submit" class="btn btn-primary">提交</button>
        </form>
    """, user)
    return HTMLResponse(content=html)


# 创建角色提交
@router.post("/create")
async def role_create_submit(
    name: str = Form(...),
    description: str = Form("")
):
    from admin_models import RoleAdmin

    await RoleAdmin.create(
        name=name,
        description=description
    )

    return RedirectResponse(url="/admin/roles/list", status_code=302)


# 编辑角色页面
@router.get("/edit/{role_id}", response_class=HTMLResponse)
async def role_edit_page(request: Request, role_id: int):
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/admin/login")

    from admin_models import RoleAdmin
    role = await RoleAdmin.filter(id=role_id).first()

    if not role:
        return HTMLResponse(content="<script>alert('角色不存在');history.back();</script>")

    html = render_admin_page("编辑角色", f"""
        <div class="page-header">
            <h2>编辑角色</h2>
            <a href="/admin/roles/list" class="btn">返回列表</a>
        </div>
        <form method="POST" action="/admin/roles/edit/{role.id}" class="data-form">
            <div class="form-group">
                <label>角色名称 *</label>
                <input type="text" name="name" value="{role.name}" required>
            </div>
            <div class="form-group">
                <label>描述</label>
                <textarea name="description" rows="3">{role.description or ''}</textarea>
            </div>
            <button type="submit" class="btn btn-primary">保存修改</button>
        </form>
    """, user)
    return HTMLResponse(content=html)


# 编辑角色提交
@router.post("/edit/{role_id}")
async def role_edit_submit(
    role_id: int,
    name: str = Form(...),
    description: str = Form("")
):
    from admin_models import RoleAdmin
    role = await RoleAdmin.filter(id=role_id).first()

    if not role:
        return HTMLResponse(content="<script>alert('角色不存在');history.back();</script>")

    role.name = name
    role.description = description
    await role.save()

    return RedirectResponse(url="/admin/roles/list", status_code=302)


# 删除角色
@router.get("/delete/{role_id}")
async def role_delete(request: Request, role_id: int):
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/admin/login")

    from admin_models import RoleAdmin, user_roles
    role = await RoleAdmin.filter(id=role_id).first()

    if not role:
        return HTMLResponse(content="<script>alert('角色不存在');history.back();</script>")

    # 删除用户-角色关联
    await user_roles.filter(role_id=role_id).delete()
    # 删除角色-权限关联
    await role.permissions.clear()
    # 删除角色
    await role.delete()

    return RedirectResponse(url="/admin/roles/list", status_code=302)


# ========== 权限管理页面 ==========

# 权限列表页面
@router.get("/admin/permissions/list", response_class=HTMLResponse)
async def permissions_list(request: Request, page: int = 1, limit: int = 20, search: str = ""):
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/admin/login")

    from admin_models import PermissionAdmin

    # 搜索功能
    query = PermissionAdmin.all()
    if search:
        query = query.filter(
            PermissionAdmin.name.contains(search) |
            PermissionAdmin.code.contains(search) |
            PermissionAdmin.category.contains(search)
        )

    offset = (page - 1) * limit
    permissions = await query.offset(offset).limit(limit).order_by("category", "name")
    total = await query.count()

    # 按分类分组显示
    permissions_by_category = {}
    for p in permissions:
        if p.category not in permissions_by_category:
            permissions_by_category[p.category] = []
        permissions_by_category[p.category].append(p)

    rows = ""
    for category, perms in permissions_by_category.items():
        rows += f'<tr class="category-row"><td colspan="6"><strong>{category}</strong></td></tr>'
        for p in perms:
            rows += f"""
            <tr>
                <td>{p.id}</td>
                <td>{p.name}</td>
                <td>{p.code}</td>
                <td>{p.category}</td>
                <td>{p.description or '-'}</td>
                <td>
                    <a href="/admin/permissions/edit/{p.id}" class="btn btn-sm">编辑</a>
                    <a href="/admin/permissions/delete/{p.id}" class="btn btn-sm btn-danger" onclick="return confirm('确定删除?')">删除</a>
                </td>
            </tr>
            """

    # 搜索表单
    search_form = f"""
    <div class="search-box">
        <form method="GET" action="/admin/permissions/list">
            <input type="text" name="search" placeholder="搜索权限名称、代码或分类" value="{search}">
            <button type="submit" class="btn btn-primary">搜索</button>
            <a href="/admin/permissions/list" class="btn">清空</a>
        </form>
    </div>
    """

    html = render_admin_page("权限管理", f"""
        <div class="page-header">
            <h2>权限管理</h2>
            {search_form}
            <a href="/admin/permissions/create" class="btn btn-primary">+ 新增权限</a>
        </div>
        <table class="data-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>权限名称</th>
                    <th>权限代码</th>
                    <th>分类</th>
                    <th>描述</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
        <div class="pagination">
            <span>共 {total} 条记录</span>
        </div>
    """, user)
    return HTMLResponse(content=html)


# 创建权限页面
@router.get("/admin/permissions/create", response_class=HTMLResponse)
async def permission_create_page(request: Request):
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/admin/login")

    html = render_admin_page("创建权限", f"""
        <div class="page-header">
            <h2>创建权限</h2>
            <a href="/admin/permissions/list" class="btn">返回列表</a>
        </div>
        <form method="POST" action="/admin/permissions/create" class="data-form">
            <div class="form-group">
                <label>权限名称 *</label>
                <input type="text" name="name" required placeholder="例如: 基金管理">
            </div>
            <div class="form-group">
                <label>权限代码 *</label>
                <input type="text" name="code" required placeholder="例如: fund_manage">
            </div>
            <div class="form-group">
                <label>分类 *</label>
                <input type="text" name="category" required placeholder="例如: 系统管理">
            </div>
            <div class="form-group">
                <label>描述</label>
                <textarea name="description" rows="3" placeholder="权限描述"></textarea>
            </div>
            <button type="submit" class="btn btn-primary">提交</button>
        </form>
    """, user)
    return HTMLResponse(content=html)


# 创建权限提交
@router.post("/admin/permissions/create")
async def permission_create_submit(
    name: str = Form(...),
    code: str = Form(...),
    category: str = Form(...),
    description: str = Form("")
):
    from admin_models import PermissionAdmin

    await PermissionAdmin.create(
        name=name,
        code=code,
        category=category,
        description=description
    )

    return RedirectResponse(url="/admin/permissions/list", status_code=302)


# 编辑权限页面
@router.get("/admin/permissions/edit/{permission_id}", response_class=HTMLResponse)
async def permission_edit_page(request: Request, permission_id: int):
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/admin/login")

    from admin_models import PermissionAdmin
    permission = await PermissionAdmin.filter(id=permission_id).first()

    if not permission:
        return HTMLResponse(content="<script>alert('权限不存在');history.back();</script>")

    html = render_admin_page("编辑权限", f"""
        <div class="page-header">
            <h2>编辑权限</h2>
            <a href="/admin/permissions/list" class="btn">返回列表</a>
        </div>
        <form method="POST" action="/admin/permissions/edit/{permission.id}" class="data-form">
            <div class="form-group">
                <label>权限名称 *</label>
                <input type="text" name="name" value="{permission.name}" required>
            </div>
            <div class="form-group">
                <label>权限代码 *</label>
                <input type="text" name="code" value="{permission.code}" required>
            </div>
            <div class="form-group">
                <label>分类 *</label>
                <input type="text" name="category" value="{permission.category}" required>
            </div>
            <div class="form-group">
                <label>描述</label>
                <textarea name="description" rows="3">{permission.description or ''}</textarea>
            </div>
            <button type="submit" class="btn btn-primary">保存修改</button>
        </form>
    """, user)
    return HTMLResponse(content=html)


# 编辑权限提交
@router.post("/admin/permissions/edit/{permission_id}")
async def permission_edit_submit(
    permission_id: int,
    name: str = Form(...),
    code: str = Form(...),
    category: str = Form(...),
    description: str = Form("")
):
    from admin_models import PermissionAdmin
    permission = await PermissionAdmin.filter(id=permission_id).first()

    if not permission:
        return HTMLResponse(content="<script>alert('权限不存在');history.back();</script>")

    permission.name = name
    permission.code = code
    permission.category = category
    permission.description = description
    await permission.save()

    return RedirectResponse(url="/admin/permissions/list", status_code=302)


# 删除权限
@router.get("/admin/permissions/delete/{permission_id}")
async def permission_delete(request: Request, permission_id: int):
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/admin/login")

    from admin_models import PermissionAdmin, role_permissions
    permission = await PermissionAdmin.filter(id=permission_id).first()

    if not permission:
        return HTMLResponse(content="<script>alert('权限不存在');history.back();</script>")

    # 删除角色-权限关联
    await role_permissions.filter(permission_id=permission_id).delete()
    # 删除权限
    await permission.delete()

    return RedirectResponse(url="/admin/permissions/list", status_code=302)


# ========== 权限分配页面 ==========

# 权限分配页面
@router.get("/permissions/{role_id}", response_class=HTMLResponse)
async def role_permissions_page(request: Request, role_id: int):
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/admin/login")

    from admin_models import RoleAdmin, PermissionAdmin
    role = await RoleAdmin.filter(id=role_id).first()

    if not role:
        return HTMLResponse(content="<script>alert('角色不存在');history.back();</script>")

    # 获取所有权限
    all_permissions = await PermissionAdmin.all().order_by("category", "name")
    # 获取角色当前权限
    role_permissions = await role.permissions.all()
    role_permission_ids = [p.id for p in role_permissions]

    # 按分类分组
    permissions_by_category = {}
    for p in all_permissions:
        if p.category not in permissions_by_category:
            permissions_by_category[p.category] = []
        permissions_by_category[p.category].append(p)

    permission_checkboxes = ""
    for category, perms in permissions_by_category.items():
        permission_checkboxes += f'<div class="permission-category"><h4>{category}</h4>'
        for p in perms:
            checked = 'checked' if p.id in role_permission_ids else ''
            permission_checkboxes += f"""
            <div class="permission-item">
                <label>
                    <input type="checkbox" name="permissions" value="{p.id}" {checked}>
                    {p.name} ({p.code})
                    <span class="permission-desc">{p.description or ''}</span>
                </label>
            </div>
            """
        permission_checkboxes += '</div>'

    html = render_admin_page("权限分配", f"""
        <div class="page-header">
            <h2>权限分配 - {role.name}</h2>
            <a href="/admin/roles/list" class="btn">返回角色列表</a>
        </div>
        <form method="POST" action="/admin/roles/permissions/{role.id}" class="permission-form">
            <div class="permission-list">
                {permission_checkboxes}
            </div>
            <button type="submit" class="btn btn-primary">保存权限</button>
        </form>
    """, user)
    return HTMLResponse(content=html)


# 权限分配提交
@router.post("/permissions/{role_id}")
async def role_permissions_submit(
    role_id: int,
    permissions: list = Form(..., list=True)
):
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/admin/login")

    from admin_models import RoleAdmin, PermissionAdmin
    role = await RoleAdmin.filter(id=role_id).first()

    if not role:
        return HTMLResponse(content="<script>alert('角色不存在');history.back();</script>")

    # 获取当前权限
    current_permissions = await role.permissions.all()
    current_permission_ids = [p.id for p in current_permissions]

    # 添加新权限
    for perm_id in permissions:
        if int(perm_id) not in current_permission_ids:
            permission = await PermissionAdmin.filter(id=int(perm_id)).first()
            if permission:
                await role.permissions.add(permission)

    # 移除取消的权限
    for perm in current_permissions:
        if perm.id not in [int(p) for p in permissions]:
            await role.permissions.remove(perm)

    return RedirectResponse(url="/admin/roles/list", status_code=302)


# ========== 基金批量操作 ==========

# 批量删除
