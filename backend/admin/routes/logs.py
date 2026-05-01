"""
Admin Logs Routes
"""

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from typing import Optional
import asyncpg

from ..utils import DB_URL, get_admin_user, sign_cookie, verify_cookie, sql_placeholders

router = APIRouter()
api_router = APIRouter()

@router.get("/dashboard", response_class=HTMLResponse)
async def logs_dashboard(request: Request):
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/admin/login")

    # 获取日志统计信息
    logs_stats = get_logs_statistics()

    html = render_admin_page("系统日志", f"""
        <div class="page-header">
            <h2>系统日志查看器</h2>
            <div class="header-actions">
                <button class="btn btn-primary" onclick="refreshLogs()">刷新日志</button>
                <button class="btn btn-secondary" onclick="searchLogs()">搜索日志</button>
                <button class="btn btn-info" onclick="exportLogs()">导出日志</button>
            </div>
        </div>

        <div class="logs-dashboard">
            <div class="logs-summary">
                <div class="logs-stats">
                    <div class="stat-card">
                        <h4>日志文件数</h4>
                        <p class="stat-value">{logs_stats['total_logs']}</p>
                    </div>
                    <div class="stat-card">
                        <h4>总大小</h4>
                        <p class="stat-value">{logs_stats['total_size']}</p>
                    </div>
                    <div class="stat-card">
                        <h4>错误数</h4>
                        <p class="stat-value">{logs_stats['error_count']}</p>
                    </div>
                    <div class="stat-card">
                        <h4>警告数</h4>
                        <p class="stat-value">{logs_stats['warning_count']}</p>
                    </div>
                </div>

                <div class="logs-filter">
                    <div class="filter-group">
                        <label>日志级别</label>
                        <select id="log-level" onchange="filterLogs()">
                            <option value="all">全部</option>
                            <option value="debug">调试</option>
                            <option value="info">信息</option>
                            <option value="warning">警告</option>
                            <option value="error">错误</option>
                        </select>
                    </div>

                    <div class="filter-group">
                        <label>时间范围</label>
                        <select id="time-range" onchange="filterLogs()">
                            <option value="all">全部</option>
                            <option value="today">今天</option>
                            <option value="week">本周</option>
                            <option value="month">本月</option>
                        </select>
                    </div>

                    <div class="filter-group">
                        <label>关键词搜索</label>
                        <input type="text" id="search-keyword" placeholder="输入关键词..." onkeyup="searchLogs()">
                    </div>
                </div>
            </div>

            <div class="logs-list">
                <h3>日志文件列表</h3>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>文件名</th>
                            <th>大小</th>
                            <th>修改时间</th>
                            <th>错误数</th>
                            <th>操作</th>
                        </tr>
                    </thead>
                    <tbody id="logs-tbody">
                        <!-- 动态生成 -->
                    </tbody>
                </table>
            </div>

            <div class="logs-actions">
                <h3>操作选项</h3>
                <div class="action-buttons">
                    <button class="btn btn-warning" onclick="clearOldLogs()">清理旧日志</button>
                    <button class="btn btn-info" onclick="downloadAllLogs()">下载所有日志</button>
                    <button class="btn btn-secondary" onclick="showLogConfig()">日志配置</button>
                    <button class="btn btn-danger" onclick="clearAllLogs()">清空所有日志</button>
                </div>
            </div>
        </div>

        <script>
            function refreshLogs() {{
                location.reload();
            }}

            function searchLogs() {{
                const keyword = document.getElementById('search-keyword').value;
                if (keyword) {{
                    fetch(`/admin/logs/search?keyword=${{keyword}}`)
                        .then(r => r.json())
                        .then(data => {{
                            displaySearchResults(data.results);
                        }});
                }}
            }}

            function filterLogs() {{
                const level = document.getElementById('log-level').value;
                const timeRange = document.getElementById('time-range').value;
                // 实现日志过滤逻辑
            }}

            function displaySearchResults(results) {{
                // 显示搜索结果
                console.log('Search results:', results);
            }}

            function exportLogs() {{
                window.open('/admin/logs/export', '_blank');
            }}

            function clearOldLogs() {{
                fetch('/admin/logs/clear', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ retention_days: 7 }})
                }}).then(r => r.json()).then(data => {{
                    alert(data.message || '清理完成');
                    refreshLogs();
                }});
            }}

            function downloadAllLogs() {{
                window.open('/admin/logs/download', '_blank');
            }}

            function showLogConfig() {{
                window.open('/admin/logs/config', '_blank');
            }}

            function clearAllLogs() {{
                if (confirm('确定要清空所有日志吗？此操作不可恢复。')) {{
                    fetch('/admin/logs/clear', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ clear_all: true }})
                    }}).then(r => r.json()).then(data => {{
                        alert(data.message || '清空完成');
                        refreshLogs();
                    }});
                }}
            }}
        </script>

        <style>
            .logs-dashboard {{ padding: 20px; }}
            .logs-summary {{ margin-bottom: 30px; }}
            .logs-stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px; }}
            .stat-card {{ background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; }}
            .stat-card h4 {{ margin: 0 0 10px 0; color: #333; }}
            .stat-value {{ font-size: 20px; font-weight: bold; margin: 0; }}
            .logs-filter {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
            .filter-group {{ display: inline-block; margin-right: 20px; }}
            .filter-group label {{ display: block; margin-bottom: 5px; font-weight: 500; }}
            .filter-group select, .filter-group input {{ padding: 8px; border: 1px solid #ddd; border-radius: 4px; }}
            .logs-list {{ margin-bottom: 30px; }}
            .logs-actions {{ background: #f8f9fa; padding: 20px; border-radius: 8px; }}
            .action-buttons {{ display: flex; gap: 10px; }}
        </style>
    """, user)
    return HTMLResponse(content=html)


# 日志查看API
@router.get("/view")
async def logs_view(request: Request, log_name: str = "crawler.log", lines: int = 100):
    user = get_admin_user(request)
    if not user:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    try:
        content = read_log_file(log_name, lines)
        return JSONResponse(content={
            "log_name": log_name,
            "content": content,
            "lines": lines,
            "total_lines": get_total_lines(log_name)
        })
    except Exception:
        logger.exception("Admin API error")
        return JSONResponse(status_code=500, content={"error": "操作失败，请稍后重试"})


# 日志搜索API
@router.get("/search")
async def logs_search(request: Request, keyword: str = "", log_name: str = None, max_results: int = 100):
    user = get_admin_user(request)
    if not user:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    try:
        results = search_logs(keyword, log_name, max_results)
        return JSONResponse(content={
            "keyword": keyword,
            "results": results,
            "total_found": len(results)
        })
    except Exception:
        logger.exception("Admin API error")
        return JSONResponse(status_code=500, content={"error": "操作失败，请稍后重试"})


# 日志清除API
@router.post("/clear")
async def logs_clear(request: Request):
    user = get_admin_user(request)
    if not user:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    try:
        data = await request.json()
        cleared = clear_logs(data)
        return JSONResponse(content={
            "success": True,
            "message": f"已清理 {cleared['files']} 个文件，释放 {cleared['space']} 空间",
            "result": cleared
        })
    except Exception:
        logger.exception("Admin API error")
        return JSONResponse(status_code=500, content={"error": "操作失败，请稍后重试"})


# 日志下载API
@router.get("/download")
async def logs_download(request: Request, log_name: str = None, date_range: str = None):
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/admin/login")

    try:
        if log_name:
            # 下载单个日志文件
            log_path = get_log_path(log_name)
            if not os.path.exists(log_path):
                return JSONResponse(status_code=404, content={"error": "日志文件不存在"})

            with open(log_path, 'rb') as f:
                content = f.read()

            return StreamingResponse(
                io.BytesIO(content),
                media_type="application/octet-stream",
                headers={"Content-Disposition": f"attachment; filename={log_name}"}
            )
        else:
            # 下载所有日志文件（ZIP格式）
            zip_buffer = create_logs_zip(date_range)
            return StreamingResponse(
                zip_buffer,
                media_type="application/zip",
                headers={"Content-Disposition": "attachment; filename=logs.zip"}
            )
    except Exception:
        logger.exception("Admin API error")
        return JSONResponse(status_code=500, content={"error": "操作失败，请稍后重试"})


# 日志配置页面
@router.get("/config")
async def logs_config_page(request: Request):
    user = get_admin_user(request)
    if not user:
        return RedirectResponse(url="/admin/login")

    config = get_logs_config()
    html = render_admin_page("日志配置", f"""
        <div class="page-header">
            <h2>日志配置管理</h2>
            <button class="btn btn-primary" onclick="saveConfig()">保存配置</button>
        </div>

        <div class="config-form">
            <div class="form-group">
                <label>最大日志文件大小（MB）</label>
                <input type="number" id="max_size" value="{config['max_size']}" min="10" max="1000">
            </div>

            <div class="form-group">
                <label>日志保留天数</label>
                <input type="number" id="retention_days" value="{config['retention_days']}" min="1" max="365">
            </div>

            <div class="form-group">
                <label>日志级别</label>
                <select id="log_level">
                    <option value="DEBUG" {'selected' if config['level'] == 'DEBUG' else ''}>DEBUG</option>
                    <option value="INFO" {'selected' if config['level'] == 'INFO' else ''}>INFO</option>
                    <option value="WARNING" {'selected' if config['level'] == 'WARNING' else ''}>WARNING</option>
                    <option value="ERROR" {'selected' if config['level'] == 'ERROR' else ''}>ERROR</option>
                </select>
            </div>

            <div class="form-group">
                <label>
                    <input type="checkbox" id="rotation" {'checked' if config['rotation'] else ''}>
                    启用日志轮转
                </label>
            </div>

            <div class="form-group">
                <label>日志格式配置（JSON）</label>
                <textarea id="format_config" rows="10" class="form-control">{config['format_config']}</textarea>
            </div>
        </div>

        <script>
            function saveConfig() {{
                const config = {{
                    max_size: document.getElementById('max_size').value,
                    retention_days: document.getElementById('retention_days').value,
                    level: document.getElementById('log_level').value,
                    rotation: document.getElementById('rotation').checked,
                    format_config: document.getElementById('format_config').value
                }};

                fetch('/admin/logs/config', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(config)
                }}).then(r => r.json()).then(data => {{
                    alert(data.message || '配置已保存');
                }});
            }}
        </script>
    """, user)
    return HTMLResponse(content=html)


@router.post("/config")
async def update_logs_config(request: Request):
    user = get_admin_user(request)
    if not user:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    try:
        config_data = await request.json()
        save_logs_config(config_data)
        return JSONResponse(content={"success": True, "message": "配置已更新"})
    except Exception:
        logger.exception("Admin API error")
        return JSONResponse(status_code=500, content={"error": "操作失败，请稍后重试"})


# 日志统计API
@router.get("/stats")
async def logs_stats_api(request: Request):
    user = get_admin_user(request)
    if not user:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    try:
        stats = get_logs_statistics()
        return JSONResponse(content=stats)
    except Exception:
        logger.exception("Admin API error")
        return JSONResponse(status_code=500, content={"error": "操作失败，请稍后重试"})


# 日志导出API
@router.get("/export")
async def logs_export(request: Request, date_range: str = None, format: str = "zip"):
    user = get_admin_user(request)
    if not user:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    try:
        export_result = export_logs(date_range, format)
        return JSONResponse(content={
            "success": True,
            "message": "导出完成",
            "file_path": export_result['file_path'],
            "size": export_result['size']
        })
    except Exception:
        logger.exception("Admin API error")
        return JSONResponse(status_code=500, content={"error": "操作失败，请稍后重试"})


# ========== 系统日志查看器辅助函数 ==========

def get_logs_statistics():
    """获取日志统计信息"""
    logs_dir = "logs"
    total_logs = 0
    total_size = 0
    error_count = 0
    warning_count = 0

    if os.path.exists(logs_dir):
        for log_file in os.listdir(logs_dir):
            if log_file.endswith('.log'):
                total_logs += 1
                log_path = os.path.join(logs_dir, log_file)
                total_size += os.path.getsize(log_path)

                # 统计错误和警告数量
                try:
                    with open(log_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        error_count += content.lower().count('error')
                        warning_count += content.lower().count('warning')
                except:
                    pass

    return {
        "total_logs": total_logs,
        "total_size": f"{total_size / 1024 / 1024:.2f} MB",
        "error_count": error_count,
        "warning_count": warning_count,
        "last_updated": datetime.now().isoformat()
    }


def read_log_file(log_name, lines=100):
    """读取日志文件内容"""
    log_path = get_log_path(log_name)
    if not os.path.exists(log_path):
        return f"日志文件 {log_name} 不存在"

    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 获取最后N行
        all_lines = content.split('\n')
        if len(all_lines) > lines:
            return '\n'.join(all_lines[-lines:])
        return content
    except Exception:
        logger.exception("读取日志文件失败")
        return "读取日志文件失败，请稍后重试"


def get_total_lines(log_name):
    """获取日志文件总行数"""
    log_path = get_log_path(log_name)
    if not os.path.exists(log_path):
        return 0

    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            return sum(1 for _ in f)
    except:
        return 0


def search_logs(keyword, log_name=None, max_results=100):
    """搜索日志"""
    results = []
    logs_dir = "logs"

    if log_name:
        log_files = [log_name]
    else:
        log_files = [f for f in os.listdir(logs_dir) if f.endswith('.log')]

    for log_file in log_files:
        log_path = os.path.join(logs_dir, log_file)
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if keyword.lower() in line.lower():
                        results.append({
                            "file": log_file,
                            "line": line_num,
                            "content": line.strip(),
                            "timestamp": extract_timestamp(line)
                        })
                        if len(results) >= max_results:
                            break
        except:
            pass

    return results


def extract_timestamp(log_line):
    """从日志行中提取时间戳"""
    import re
    timestamp_pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
    match = re.search(timestamp_pattern, log_line)
    if match:
        return match.group(0)
    return "未知时间"


def clear_logs(options):
    """清理日志"""
    retention_days = options.get('retention_days', 7)
    clear_all = options.get('clear_all', False)
    cleared_files = 0
    freed_space = 0

    logs_dir = "logs"
    if os.path.exists(logs_dir):
        import shutil
        from datetime import datetime, timedelta

        cutoff_date = datetime.now() - timedelta(days=retention_days)

        for log_file in os.listdir(logs_dir):
            if log_file.endswith('.log'):
                log_path = os.path.join(logs_dir, log_file)
                file_mtime = datetime.fromtimestamp(os.path.getmtime(log_path))

                if clear_all or file_mtime < cutoff_date:
                    try:
                        file_size = os.path.getsize(log_path)
                        os.remove(log_path)
                        cleared_files += 1
                        freed_space += file_size
                    except:
                        pass

    return {
        "files": cleared_files,
        "space": f"{freed_space / 1024 / 1024:.2f} MB"
    }


def get_log_path(log_name):
    """获取日志文件路径"""
    logs_dir = "logs"
    # 检查logs目录是否存在
    if os.path.exists(logs_dir) and os.path.isdir(logs_dir):
        log_path = os.path.join(logs_dir, log_name)
        if os.path.exists(log_path):
            return log_path

    # 检查当前目录
    if os.path.exists(log_name):
        return log_name

    # 检查backend目录
    backend_log = os.path.join("..", log_name)
    if os.path.exists(backend_log):
        return backend_log

    return os.path.join(logs_dir, log_name)


def create_logs_zip(date_range=None):
    """创建日志ZIP文件"""
    import io
    import zipfile

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        logs_dir = "logs"
        if os.path.exists(logs_dir):
            for log_file in os.listdir(logs_dir):
                if log_file.endswith('.log'):
                    log_path = os.path.join(logs_dir, log_file)
                    zip_file.write(log_path, log_file)

    zip_buffer.seek(0)
    return zip_buffer


def get_logs_config():
    """获取日志配置"""
    return {
        "max_size": 100,
        "retention_days": 30,
        "level": "INFO",
        "rotation": True,
        "format_config": "{\n  \"format\": \"%(asctime)s - %(name)s - %(levelname)s - %(message)s\",\n  \"datefmt\": \"%Y-%m-%d %H:%M:%S\"\n}"
    }


def save_logs_config(config_data):
    """保存日志配置"""
    config_file = "logs_config.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        import json
        json.dump(config_data, f, indent=2)


def export_logs(date_range, format):
    """导出日志"""
    import shutil

    export_dir = "logs_export"
    if os.path.exists(export_dir):
        shutil.rmtree(export_dir)
    os.makedirs(export_dir)

    logs_dir = "logs"
    if os.path.exists(logs_dir):
        for log_file in os.listdir(logs_dir):
            if log_file.endswith('.log'):
                shutil.copy(os.path.join(logs_dir, log_file), export_dir)

    export_path = f"{export_dir}.{format}"
    if format == "zip":
        shutil.make_archive(export_dir, 'zip', export_dir)
    elif format == "tar":
        shutil.make_archive(export_dir, 'tar', export_dir)

    shutil.rmtree(export_dir)

    return {
        "file_path": export_path,
        "size": os.path.getsize(export_path)
    }


# ========== 告警管理功能 ==========

# 告警仪表盘
