"""
Admin Login Routes — HTML pages only
API endpoints moved to auth.py
"""
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ..utils import sign_cookie

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
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
            width: 100%;
            max-width: 400px;
            margin: 20px;
        }
        h1 { text-align: center; color: #333; margin-bottom: 30px; font-size: 24px; }
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
        button:disabled { opacity: 0.6; cursor: not-allowed; }
        .error { color: #e74c3c; text-align: center; margin-top: 15px; font-size: 14px; }
        .success { color: #27ae60; text-align: center; margin-top: 15px; font-size: 14px; }
    </style>
</head>
<body>
    <div class="login-box">
        <h1>REITs 管理平台</h1>
        <form id="loginForm">
            <div class="form-group">
                <label>用户名</label>
                <input type="text" id="username" name="username" placeholder="admin" required autocomplete="username">
            </div>
            <div class="form-group">
                <label>密码</label>
                <input type="password" id="password" name="password" placeholder="admin123" required autocomplete="current-password">
            </div>
            <button type="submit" id="submitBtn">登录</button>
            <p id="message" class="error"></p>
        </form>
    </div>
    <script>
    document.getElementById('loginForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        const btn = document.getElementById('submitBtn');
        const msg = document.getElementById('message');
        btn.disabled = true;
        msg.textContent = '';
        msg.className = 'error';
        try {
            const res = await fetch('/api/v1/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username: document.getElementById('username').value,
                    password: document.getElementById('password').value
                })
            });
            const data = await res.json();
            if (data.code === 200 && data.data && data.data.access_token) {
                localStorage.setItem('access_token', data.data.access_token);
                msg.className = 'success';
                msg.textContent = '登录成功，跳转中...';
                window.location.href = '/admin/';
            } else {
                msg.textContent = data.message || '登录失败';
            }
        } catch (err) {
            msg.textContent = '网络错误，请重试';
        } finally {
            btn.disabled = false;
        }
    });
    </script>
</body>
</html>"""
    return HTMLResponse(content=html)


@router.post("/login")
async def login_legacy(username: str = Form(...), password: str = Form(...)):
    """Legacy form login — redirects to new API."""
    return RedirectResponse(url="/admin/login", status_code=302)


@router.get("/logout")
async def logout():
    html = """<!DOCTYPE html>
<html><head><script>
    localStorage.removeItem('access_token');
    fetch('/api/v1/auth/logout', { method: 'POST', credentials: 'include' })
        .finally(() => window.location.href = '/admin/login');
</script></head></html>"""
    return HTMLResponse(content=html)


@router.get("/", response_class=HTMLResponse)
async def admin_index(request: Request):
    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>REITs Admin</title>
    <script>
    (function(){
        const token = localStorage.getItem('access_token');
        if (!token) {
            window.location.href = '/admin/login';
            return;
        }
        // Verify token validity by calling /me
        fetch('/api/v1/auth/me', {
            headers: { 'Authorization': 'Bearer ' + token }
        }).then(r => r.json()).then(data => {
            if (data.code !== 200) {
                localStorage.removeItem('access_token');
                window.location.href = '/admin/login';
            }
        }).catch(() => {
            localStorage.removeItem('access_token');
            window.location.href = '/admin/login';
        });
    })();
    </script>
</head>
<body>
    <h1>REITs 管理后台</h1>
    <p>正在加载...</p>
</body>
</html>"""
    return HTMLResponse(content=html)
