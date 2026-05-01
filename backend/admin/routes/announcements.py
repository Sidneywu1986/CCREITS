"""
Admin Announcements Routes
"""

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from typing import Optional
import asyncpg

from ..utils import DB_URL, get_admin_user, sign_cookie, verify_cookie, sql_placeholders

router = APIRouter()
api_router = APIRouter()

@router.get("/list", response_class=HTMLResponse)
async def announcements_list(request: Request, page: int = 1, limit: int = 20, search: str = ""):
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/admin/login")

    from admin_models import AnnouncementAdmin

    # 搜索功能
    query = AnnouncementAdmin.all()
    if search:
        query = query.filter(
            AnnouncementAdmin.title.contains(search) |
            AnnouncementAdmin.fund_code.contains(search)
        )

    offset = (page - 1) * limit
    announcements = await query.offset(offset).limit(limit).order_by("-publish_date")
    total = await query.count()

    rows = ""
    for a in announcements:
        rows += f"""
        <tr>
            <td>{a.id}</td>
            <td>{a.fund_code}</td>
            <td>{a.title}</td>
            <td>{str(a.publish_date)[:10]}</td>
            <td>{a.announcement_type or '-'}</td>
            <td>
                <a href="/admin/announcements/detail/{a.id}" class="btn btn-sm">查看</a>
                <a href="/admin/announcements/edit/{a.id}" class="btn btn-sm">编辑</a>
                <a href="/admin/announcements/delete/{a.id}" class="btn btn-sm btn-danger" onclick="return confirm('确定删除?')">删除</a>
            </td>
        </tr>
        """

    # 搜索表单
    search_form = f"""
    <div class="search-box">
        <form method="GET" action="/admin/announcements/list">
            <input type="text" name="search" placeholder="搜索公告标题或基金代码" value="{search}">
            <button type="submit" class="btn btn-primary">搜索</button>
            <a href="/admin/announcements/list" class="btn">清空</a>
        </form>
    </div>
    """

    html = render_admin_page("公告管理", f"""
        <div class="page-header">
            <h2>公告管理</h2>
            {search_form}
            <a href="/admin/announcements/create" class="btn btn-primary">+ 新增公告</a>
        </div>
        <table class="data-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>基金代码</th>
                    <th>标题</th>
                    <th>发布日期</th>
                    <th>类型</th>
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


# 创建公告页面
@router.get("/create", response_class=HTMLResponse)
async def announcement_create_page(request: Request):
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/admin/login")

    html = render_admin_page("创建公告", f"""
        <div class="page-header">
            <h2>创建公告</h2>
            <a href="/admin/announcements/list" class="btn">返回列表</a>
        </div>
        <form method="POST" action="/admin/announcements/create" class="data-form">
            <div class="form-group">
                <label>基金代码 *</label>
                <input type="text" name="fund_code" required placeholder="例如: 150050">
            </div>
            <div class="form-group">
                <label>标题 *</label>
                <input type="text" name="title" required placeholder="公告标题">
            </div>
            <div class="form-group">
                <label>发布日期 *</label>
                <input type="date" name="publish_date" required value="{datetime.now().strftime('%Y-%m-%d')}">
            </div>
            <div class="form-group">
                <label>公告类型</label>
                <select name="announcement_type">
                    <option value="">请选择</option>
                    <option value="定期报告">定期报告</option>
                    <option value="季度报告">季度报告</option>
                    <option value="年度报告">年度报告</option>
                    <option value="临时公告">临时公告</option>
                    <option value="分红公告">分红公告</option>
                    <option value="其他">其他</option>
                </select>
            </div>
            <div class="form-group">
                <label>内容</label>
                <textarea name="content" rows="6" placeholder="公告内容"></textarea>
            </div>
            <div class="form-group">
                <label>PDF链接</label>
                <input type="text" name="pdf_url" placeholder="PDF文件链接">
            </div>
            <button type="submit" class="btn btn-primary">提交</button>
        </form>
    """, user)
    return HTMLResponse(content=html)


# 创建公告提交
@router.post("/create")
async def announcement_create_submit(
    fund_code: str = Form(...),
    title: str = Form(...),
    publish_date: str = Form(...),
    announcement_type: str = Form(""),
    content: str = Form(""),
    pdf_url: str = Form("")
):
    from admin_models import AnnouncementAdmin

    await AnnouncementAdmin.create(
        fund_code=fund_code,
        title=title,
        publish_date=publish_date + "T00:00:00",
        announcement_type=announcement_type,
        content=content,
        pdf_url=pdf_url
    )

    return RedirectResponse(url="/admin/announcements/list", status_code=302)


# 公告详情页面
@router.get("/detail/{announcement_id}", response_class=HTMLResponse)
async def announcement_detail(request: Request, announcement_id: int):
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/admin/login")

    from admin_models import AnnouncementAdmin
    announcement = await AnnouncementAdmin.filter(id=announcement_id).first()

    if not announcement:
        return HTMLResponse(content="<script>alert('公告不存在');history.back();</script>")

    html = render_admin_page("公告详情", f"""
        <div class="page-header">
            <h2>公告详情</h2>
            <a href="/admin/announcements/list" class="btn">返回列表</a>
            <a href="/admin/announcements/edit/{announcement.id}" class="btn btn-primary">编辑</a>
        </div>
        <div class="detail-box">
            <div class="detail-row">
                <span class="detail-label">ID:</span>
                <span class="detail-value">{announcement.id}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">基金代码:</span>
                <span class="detail-value">{announcement.fund_code}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">标题:</span>
                <span class="detail-value">{announcement.title}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">发布日期:</span>
                <span class="detail-value">{str(announcement.publish_date)[:19]}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">公告类型:</span>
                <span class="detail-value">{announcement.announcement_type or '-'}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">PDF链接:</span>
                <span class="detail-value">{announcement.pdf_url or '-'}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">内容:</span>
                <span class="detail-value" style="white-space: pre-wrap;">{announcement.content or '-'}</span>
            </div>
        </div>
    """, user)
    return HTMLResponse(content=html)


# 编辑公告页面
@router.get("/edit/{announcement_id}", response_class=HTMLResponse)
async def announcement_edit_page(request: Request, announcement_id: int):
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/admin/login")

    from admin_models import AnnouncementAdmin
    announcement = await AnnouncementAdmin.filter(id=announcement_id).first()

    if not announcement:
        return HTMLResponse(content="<script>alert('公告不存在');history.back();</script>")

    # 格式化日期
    publish_date = str(announcement.publish_date)[:10]

    html = render_admin_page("编辑公告", f"""
        <div class="page-header">
            <h2>编辑公告</h2>
            <a href="/admin/announcements/detail/{announcement.id}" class="btn">取消编辑</a>
        </div>
        <form method="POST" action="/admin/announcements/edit/{announcement.id}" class="data-form">
            <div class="form-group">
                <label>基金代码 *</label>
                <input type="text" name="fund_code" value="{announcement.fund_code}" required>
            </div>
            <div class="form-group">
                <label>标题 *</label>
                <input type="text" name="title" value="{announcement.title}" required>
            </div>
            <div class="form-group">
                <label>发布日期 *</label>
                <input type="date" name="publish_date" value="{publish_date}" required>
            </div>
            <div class="form-group">
                <label>公告类型</label>
                <select name="announcement_type">
                    <option value="">请选择</option>
                    <option value="定期报告" {'selected' if announcement.announcement_type == '定期报告' else ''}>定期报告</option>
                    <option value="季度报告" {'selected' if announcement.announcement_type == '季度报告' else ''}>季度报告</option>
                    <option value="年度报告" {'selected' if announcement.announcement_type == '年度报告' else ''}>年度报告</option>
                    <option value="临时公告" {'selected' if announcement.announcement_type == '临时公告' else ''}>临时公告</option>
                    <option value="分红公告" {'selected' if announcement.announcement_type == '分红公告' else ''}>分红公告</option>
                    <option value="其他" {'selected' if announcement.announcement_type == '其他' else ''}>其他</option>
                </select>
            </div>
            <div class="form-group">
                <label>内容</label>
                <textarea name="content" rows="6">{announcement.content or ''}</textarea>
            </div>
            <div class="form-group">
                <label>PDF链接</label>
                <input type="text" name="pdf_url" value="{announcement.pdf_url or ''}">
            </div>
            <button type="submit" class="btn btn-primary">保存修改</button>
        </form>
    """, user)
    return HTMLResponse(content=html)


# 编辑公告提交
@router.post("/edit/{announcement_id}")
async def announcement_edit_submit(
    announcement_id: int,
    fund_code: str = Form(...),
    title: str = Form(...),
    publish_date: str = Form(...),
    announcement_type: str = Form(""),
    content: str = Form(""),
    pdf_url: str = Form("")
):
    from admin_models import AnnouncementAdmin
    announcement = await AnnouncementAdmin.filter(id=announcement_id).first()

    if not announcement:
        return HTMLResponse(content="<script>alert('公告不存在');history.back();</script>")

    # 更新公告
    announcement.fund_code = fund_code
    announcement.title = title
    announcement.publish_date = publish_date + "T00:00:00"
    announcement.announcement_type = announcement_type
    announcement.content = content
    announcement.pdf_url = pdf_url
    await announcement.save()

    return RedirectResponse(url=f"/admin/announcements/detail/{announcement_id}", status_code=302)


# 删除公告
@router.get("/delete/{announcement_id}")
async def announcement_delete(request: Request, announcement_id: int):
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/admin/login")

    from admin_models import AnnouncementAdmin
    announcement = await AnnouncementAdmin.filter(id=announcement_id).first()

    if not announcement:
        return HTMLResponse(content="<script>alert('公告不存在');history.back();</script>")

    await announcement.delete()
    return RedirectResponse(url="/admin/announcements/list", status_code=302)


# ========== 角色管理页面 ==========

# 角色列表页面
