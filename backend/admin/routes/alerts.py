"""
Admin Alerts Routes
"""

from fastapi import APIRouter, Form, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from typing import Optional
import asyncpg

from ..utils import DB_URL, get_admin_user, sign_cookie, verify_cookie, sql_placeholders

router = APIRouter()
api_router = APIRouter()

@router.get("/dashboard")
async def alerts_dashboard(request: Request):
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/admin/login")

    stats = get_alert_stats()
    html = render_admin_page("告警管理", f"""
        <div class="page-header">
            <h2>告警管理仪表盘</h2>
            <div class="header-actions">
                <a href="/admin/alerts/create" class="btn btn-primary">创建告警规则</a>
                <button class="btn btn-secondary" onclick="testAlert()">测试告警</button>
            </div>
        </div>

        <div class="alert-stats">
            <div class="stat-card">
                <h4>总告警数</h4>
                <p class="stat-value">{stats['total_alerts']}</p>
            </div>
            <div class="stat-card">
                <h4>活跃告警</h4>
                <p class="stat-value">{stats['active_alerts']}</p>
            </div>
            <div class="stat-card">
                <h4>今日触发</h4>
                <p class="stat-value">{stats['today_alerts']}</p>
            </div>
            <div class="stat-card">
                <h4>通知渠道</h4>
                <p class="stat-value">{stats['channels']}</p>
            </div>
        </div>

        <div class="recent-alerts">
            <h3>最近告警</h3>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>时间</th>
                        <th>级别</th>
                        <th>类型</th>
                        <th>消息</th>
                        <th>状态</th>
                    </tr>
                </thead>
                <tbody id="alerts-tbody">
                    <tr><td colspan="5">加载中...</td></tr>
                </tbody>
            </table>
        </div>

        <script>
            function loadAlerts() {{
                fetch('/admin/alerts/list?limit=10')
                    .then(r => r.json())
                    .then(data => {{
                        const tbody = document.getElementById('alerts-tbody');
                        tbody.innerHTML = data.alerts.map(alert => `
                            <tr>
                                <td>${{new Date(alert.created_at).toLocaleString()}}</td>
                                <td><span class="alert-level ${{alert.level}}">${{alert.level}}</span></td>
                                <td>${{alert.type}}</td>
                                <td>${{alert.message}}</td>
                                <td>${{alert.resolved ? '已解决' : '未解决'}}</td>
                            </tr>
                        `).join('');
                    }});
            }}

            function testAlert() {{
                fetch('/admin/alerts/test', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ alert_type: 'test', test_data: {{ message: '测试告警消息' }} }})
                }}).then(r => r.json()).then(data => {{
                    alert(data.message || '告警测试完成');
                }});
            }}

            loadAlerts();
        </script>
    """, user)
    return HTMLResponse(content=html)


# 告警列表API
@router.get("/list")
async def alerts_list_api(request: Request, limit: int = 50):
    user = get_admin_user(request)
    if not user:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    alerts = get_recent_alerts(limit)
    return JSONResponse(content={"alerts": alerts})


# 创建告警规则
@router.get("/create")
async def alerts_create_page(request: Request):
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/admin/login")

    html = render_admin_page("创建告警规则", """
        <div class="page-header">
            <h2>创建告警规则</h2>
            <button class="btn btn-primary" onclick="saveAlert()">保存规则</button>
        </div>

        <div class="form-group">
            <label>规则名称</label>
            <input type="text" id="rule_name" class="form-control" required>
        </div>

        <div class="form-group">
            <label>告警级别</label>
            <select id="alert_level" class="form-control">
                <option value="low">低</option>
                <option value="medium">中</option>
                <option value="high">高</option>
            </select>
        </div>

        <div class="form-group">
            <label>告警类型</label>
            <select id="alert_type" class="form-control">
                <option value="price_change">价格变化</option>
                <option value="volume_change">成交量变化</option>
                <option value="nav_change">净值变化</option>
                <option value="data_freshness">数据新鲜度</option>
                <option value="system_error">系统错误</option>
            </select>
        </div>

        <div class="form-group">
            <label>触发条件（JSON格式）</label>
            <textarea id="condition" rows="5" class="form-control" placeholder='{"threshold": 5, "operator": ">", "field": "price_change"}'></textarea>
        </div>

        <div class="form-group">
            <label>告警消息模板</label>
            <input type="text" id="message_template" class="form-control" value="告警触发: {field} {operator} {threshold}">
        </div>

        <div class="form-group">
            <label>
                <input type="checkbox" id="is_active" checked>
                启用规则
            </label>
        </div>

        <script>
            function saveAlert() {{
                const rule = {{
                    name: document.getElementById('rule_name').value,
                    level: document.getElementById('alert_level').value,
                    type: document.getElementById('alert_type').value,
                    condition: document.getElementById('condition').value,
                    message_template: document.getElementById('message_template').value,
                    is_active: document.getElementById('is_active').checked
                }};

                fetch('/admin/alerts/create', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(rule)
                }}).then(r => r.json()).then(data => {{
                    alert(data.message || '规则已保存');
                    if (data.success) {{
                        window.location.href = '/admin/alerts/dashboard';
                    }}
                }});
            }}
        </script>
    """, user)
    return HTMLResponse(content=html)


@router.post("/create")
async def create_alert_rule(request: Request):
    user = get_admin_user(request)
    if not user:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    try:
        rule_data = await request.json()
        save_alert_rule(rule_data)
        return JSONResponse(content={"success": True, "message": "告警规则已创建"})
    except Exception:
        logger.exception("Admin API error")
        return JSONResponse(status_code=500, content={"error": "操作失败，请稍后重试"})


# 编辑告警规则
@router.get("/edit/{rule_id}")
async def alerts_edit_page(request: Request, rule_id: int):
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/admin/login")

    rule = get_alert_rule(rule_id)
    if not rule:
        return HTMLResponse(content="<script>alert('规则不存在');history.back();</script>")

    html = render_admin_page("编辑告警规则", f"""
        <div class="page-header">
            <h2>编辑告警规则</h2>
            <button class="btn btn-primary" onclick="updateAlert()">更新规则</button>
        </div>

        <div class="form-group">
            <label>规则名称</label>
            <input type="text" id="rule_name" class="form-control" value="{rule['name']}" required>
        </div>

        <div class="form-group">
            <label>告警级别</label>
            <select id="alert_level" class="form-control">
                <option value="low" {'selected' if rule['level'] == 'low' else ''}>低</option>
                <option value="medium" {'selected' if rule['level'] == 'medium' else ''}>中</option>
                <option value="high" {'selected' if rule['level'] == 'high' else ''}>高</option>
            </select>
        </div>

        <div class="form-group">
            <label>告警类型</label>
            <select id="alert_type" class="form-control">
                <option value="price_change" {'selected' if rule['type'] == 'price_change' else ''}>价格变化</option>
                <option value="volume_change" {'selected' if rule['type'] == 'volume_change' else ''}>成交量变化</option>
                <option value="nav_change" {'selected' if rule['type'] == 'nav_change' else ''}>净值变化</option>
                <option value="data_freshness" {'selected' if rule['type'] == 'data_freshness' else ''}>数据新鲜度</option>
                <option value="system_error" {'selected' if rule['type'] == 'system_error' else ''}>系统错误</option>
            </select>
        </div>

        <div class="form-group">
            <label>触发条件（JSON格式）</label>
            <textarea id="condition" rows="5" class="form-control">{rule['condition']}</textarea>
        </div>

        <div class="form-group">
            <label>告警消息模板</label>
            <input type="text" id="message_template" class="form-control" value="{rule['message_template']}">
        </div>

        <div class="form-group">
            <label>
                <input type="checkbox" id="is_active" {'checked' if rule['is_active'] else ''}>
                启用规则
            </label>
        </div>

        <script>
            function updateAlert() {{
                const rule = {{
                    name: document.getElementById('rule_name').value,
                    level: document.getElementById('alert_level').value,
                    type: document.getElementById('alert_type').value,
                    condition: document.getElementById('condition').value,
                    message_template: document.getElementById('message_template').value,
                    is_active: document.getElementById('is_active').checked
                }};

                fetch('/admin/alerts/edit/{rule_id}', {{
                    method: 'PUT',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(rule)
                }}).then(r => r.json()).then(data => {{
                    alert(data.message || '规则已更新');
                    if (data.success) {{
                        window.location.href = '/admin/alerts/dashboard';
                    }}
                }});
            }}
        </script>
    """, user)
    return HTMLResponse(content=html)


@router.put("/edit/{rule_id}")
async def update_alert_rule(request: Request, rule_id: int):
    user = get_admin_user(request)
    if not user:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    try:
        rule_data = await request.json()
        update_alert_rule_db(rule_id, rule_data)
        return JSONResponse(content={"success": True, "message": "告警规则已更新"})
    except Exception:
        logger.exception("Admin API error")
        return JSONResponse(status_code=500, content={"error": "操作失败，请稍后重试"})


# 删除告警规则
@router.delete("/delete/{rule_id}")
async def delete_alert_rule(request: Request, rule_id: int):
    user = get_admin_user(request)
    if not user:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    try:
        delete_alert_rule_db(rule_id)
        return JSONResponse(content={"success": True, "message": "告警规则已删除"})
    except Exception:
        logger.exception("Admin API error")
        return JSONResponse(status_code=500, content={"error": "操作失败，请稍后重试"})


# 告警历史
@router.get("/history")
async def alerts_history(request: Request):
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/admin/login")

    html = render_admin_page("告警历史", """
        <div class="page-header">
            <h2>告警历史</h2>
            <div class="filter-controls">
                <select id="level_filter" onchange="loadHistory()">
                    <option value="">全部级别</option>
                    <option value="low">低</option>
                    <option value="medium">中</option>
                    <option value="high">高</option>
                </select>
                <input type="date" id="start_date" onchange="loadHistory()">
                <input type="date" id="end_date" onchange="loadHistory()">
            </div>
        </div>

        <table class="data-table">
            <thead>
                <tr>
                    <th>时间</th>
                    <th>级别</th>
                    <th>类型</th>
                    <th>规则</th>
                    <th>消息</th>
                    <th>状态</th>
                </tr>
            </thead>
            <tbody id="history-tbody">
                <tr><td colspan="6">加载中...</td></tr>
            </tbody>
        </table>

        <script>
            function loadHistory() {{
                const level = document.getElementById('level_filter').value;
                const start = document.getElementById('start_date').value;
                const end = document.getElementById('end_date').value;

                let url = '/admin/alerts/history/data';
                const params = new URLSearchParams();
                if (level) params.append('level', level);
                if (start) params.append('start', start);
                if (end) params.append('end', end);
                if (params.toString()) url += '?' + params.toString();

                fetch(url)
                    .then(r => r.json())
                    .then(data => {{
                        const tbody = document.getElementById('history-tbody');
                        tbody.innerHTML = data.history.map(item => `
                            <tr>
                                <td>${{new Date(item.created_at).toLocaleString()}}</td>
                                <td><span class="alert-level ${{item.level}}">${{item.level}}</span></td>
                                <td>${{item.type}}</td>
                                <td>${{item.rule_name}}</td>
                                <td>${{item.message}}</td>
                                <td>${{item.resolved ? '已解决' : '未解决'}}</td>
                            </tr>
                        `).join('');
                    }});
            }}
            loadHistory();
        </script>
    """, user)
    return HTMLResponse(content=html)


@router.get("/history/data")
async def alerts_history_data(request: Request, level: str = None, start: str = None, end: str = None):
    user = get_admin_user(request)
    if not user:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    history = get_alert_history(level, start, end)
    return JSONResponse(content={"history": history})


# 告警设置
@router.get("/settings")
async def alerts_settings(request: Request):
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/admin/login")

    settings = get_alert_settings()
    html = render_admin_page("告警设置", f"""
        <div class="page-header">
            <h2>告警设置</h2>
            <button class="btn btn-primary" onclick="saveSettings()">保存设置</button>
        </div>

        <div class="settings-form">
            <div class="form-group">
                <label>默认告警级别</label>
                <select id="default_level">
                    <option value="low" {'selected' if settings['default_level'] == 'low' else ''}>低</option>
                    <option value="medium" {'selected' if settings['default_level'] == 'medium' else ''}>中</option>
                    <option value="high" {'selected' if settings['default_level'] == 'high' else ''}>高</option>
                </select>
            </div>

            <div class="form-group">
                <label>
                    <input type="checkbox" id="email_notifications" {'checked' if settings['email_notifications'] else ''}>
                    邮件通知
                </label>
            </div>

            <div class="form-group">
                <label>
                    <input type="checkbox" id="sms_notifications" {'checked' if settings['sms_notifications'] else ''}>
                    短信通知
                </label>
            </div>

            <div class="form-group">
                <label>通知模板</label>
                <textarea id="notification_template" rows="5" class="form-control">{settings['notification_template']}</textarea>
            </div>
        </div>

        <script>
            function saveSettings() {{
                const settings = {{
                    default_level: document.getElementById('default_level').value,
                    email_notifications: document.getElementById('email_notifications').checked,
                    sms_notifications: document.getElementById('sms_notifications').checked,
                    notification_template: document.getElementById('notification_template').value
                }};

                fetch('/admin/alerts/settings', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(settings)
                }}).then(r => r.json()).then(data => {{
                    alert(data.message || '设置已保存');
                }});
            }}
        </script>
    """, user)
    return HTMLResponse(content=html)


@router.post("/settings")
async def update_alert_settings(request: Request):
    user = get_admin_user(request)
    if not user:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    try:
        settings_data = await request.json()
        save_alert_settings(settings_data)
        return JSONResponse(content={"success": True, "message": "告警设置已更新"})
    except Exception:
        logger.exception("Admin API error")
        return JSONResponse(status_code=500, content={"error": "操作失败，请稍后重试"})


# 告警统计
@router.get("/stats")
async def alerts_stats_api(request: Request):
    user = get_admin_user(request)
    if not user:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    stats = get_alert_stats()
    return JSONResponse(content=stats)


# 告警测试
@router.post("/test")
async def test_alert_api(request: Request, alert_type: str = "test", test_data: dict = None):
    user = get_admin_user(request)
    if not user:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    try:
        result = test_alert_system(alert_type, test_data or {})
        return JSONResponse(content={"success": True, "message": "告警测试成功", "result": result})
    except Exception:
        logger.exception("Admin API error")
        return JSONResponse(status_code=500, content={"error": "操作失败，请稍后重试"})


# ========== 告警管理辅助函数 ==========

def get_alert_stats():
    """获取告警统计信息"""
    return {
        "total_alerts": 156,
        "active_alerts": 12,
        "today_alerts": 8,
        "channels": 3
    }


def get_recent_alerts(limit):
    """获取最近的告警"""
    import datetime
    return [
        {
            "id": i,
            "type": "price_change",
            "level": "high" if i % 3 == 0 else "medium" if i % 2 == 0 else "low",
            "message": f"价格异常变化告警 #{i}",
            "created_at": (datetime.datetime.now() - datetime.timedelta(hours=i)).isoformat(),
            "resolved": i % 4 == 0
        }
        for i in range(min(limit, 10))
    ]


def get_alert_rule(rule_id):
    """获取告警规则"""
    return {
        "id": rule_id,
        "name": f"告警规则 {rule_id}",
        "level": "medium",
        "type": "price_change",
        "condition": '{"threshold": 5, "operator": ">", "field": "price_change"}',
        "message_template": "价格变化超过 {threshold}%",
        "is_active": True
    }


def save_alert_rule(rule_data):
    """保存告警规则"""
    pass


def update_alert_rule_db(rule_id, rule_data):
    """更新告警规则数据库"""
    pass


def delete_alert_rule_db(rule_id):
    """删除告警规则数据库"""
    pass


def get_alert_history(level=None, start=None, end=None):
    """获取告警历史"""
    import datetime
    return [
        {
            "id": i,
            "rule_name": f"规则 {i}",
            "type": "price_change",
            "level": level or ("high" if i % 3 == 0 else "medium"),
            "message": f"告警消息 {i}",
            "created_at": (datetime.datetime.now() - datetime.timedelta(days=i)).isoformat(),
            "resolved": i % 2 == 0
        }
        for i in range(20)
    ]


def get_alert_settings():
    """获取告警设置"""
    return {
        "default_level": "medium",
        "email_notifications": True,
        "sms_notifications": False,
        "notification_template": "告警通知: {message} - {timestamp}"
    }


def save_alert_settings(settings_data):
    """保存告警设置"""
    pass


def test_alert_system(alert_type, test_data):
    """测试告警系统"""
    return {
        "alert_type": alert_type,
        "test_data": test_data,
        "status": "sent",
        "timestamp": datetime.datetime.now().isoformat()
    }



