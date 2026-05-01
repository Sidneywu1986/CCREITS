# Phase 3 — API JWT 认证体系技术规范

> **Scope:** 为全部 `/api/*` 端点和管理后台添加统一 JWT 认证，建立用户注册/登录/刷新 Token 体系，实现 API 权限分级。
> **Depends on:** Phase 2（UI 整改完成）
> **Estimated Effort:** 3 Waves（~3-4 天）

---

## 1. 现状分析

### 1.1 现有认证机制

| 系统 | 当前认证方式 | 问题 |
|------|-------------|------|
| 管理后台 (`/admin/*`) | Cookie HMAC 签名 (`admin_user` cookie) | 仅管理后台可用，无过期控制，API 端点无法复用 |
| API 端点 (`/api/*`) | **无认证** | 所有 API 完全公开，无用户识别能力 |
| 管理后台 API (`/api/v1/auth/*`) | 随机 Token (`secrets.token_urlsafe(32)`) | 非标准 JWT，无签名验证，/me 返回硬编码数据 |

### 1.2 现有基础设施

- **配置:** `core/config.py` 已有 `JWT_SECRET`, `JWT_ALGORITHM="HS256"`, `JWT_EXPIRE_MINUTES=1440`
- **用户模型:** `admin_models.UserAdmin` 含 `password_hash`, `is_active`, `is_superuser`, `email_verified`, `last_login`
- **密码哈希:** `passlib.hash.bcrypt`（已在使用）
- **数据库:** PostgreSQL + asyncpg + Tortoise ORM
- **角色/权限模型:** `RoleAdmin`, `PermissionAdmin` 表已存在，但无关联关系

---

## 2. 设计目标

1. **统一认证:** 一套 JWT 体系覆盖管理后台和前端 API
2. **双 Token 策略:** Access Token（短时效）+ Refresh Token（长时效），支持自动续期
3. **权限分级:** 公开(PUBLIC) / 普通用户(USER) / 管理员(ADMIN) 三级权限
4. **向后兼容:** 管理后台 Cookie 认证保留，逐步平滑迁移
5. **安全加固:** Token 黑名单、速率限制、HTTPS 强制
6. **测试覆盖:** TDD 模式，所有认证流程 100% 覆盖

---

## 3. 架构设计

### 3.1 模块结构

```
backend/
├── core/
│   └── auth/
│       ├── __init__.py
│       ├── jwt.py          # JWT 生成/验证/刷新
│       ├── dependencies.py # FastAPI Depends: get_current_user, require_admin
│       ├── password.py     # 密码哈希/验证封装
│       └── permissions.py  # 权限检查工具
│
├── admin/
│   └── routes/
│       └── auth.py         # 注册/登录/刷新/登出 API（替换现有）
│
├── api/
│   └── dependencies.py     # API 路由共享的认证依赖
│
└── admin_models.py         # 用户模型扩展（refresh_token 字段）
```

### 3.2 JWT Token 设计

#### Access Token（访问令牌）

```json
{
  "sub": "42",
  "username": "alice",
  "role": "user",
  "permissions": ["fund:read", "announcement:read"],
  "type": "access",
  "iat": 1714214400,
  "exp": 1714215300,
  "iss": "reits-api",
  "aud": "reits-platform"
}
```

- **有效期:** 15 分钟
- **载体:** HTTP Header `Authorization: Bearer <token>`

#### Refresh Token（刷新令牌）

```json
{
  "sub": "42",
  "type": "refresh",
  "jti": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "iat": 1714214400,
  "exp": 1714819200
}
```

- **有效期:** 7 天
- **载体:** HTTP-only Cookie `refresh_token`
  - `SameSite=Lax`
  - `Secure`（生产环境）
  - `Path=/api/v1/auth`
- **存储:** 数据库 `users.refresh_token_jti` 字段（支持 Token 撤销）

### 3.3 认证流程

```
注册:
  Client ──POST /api/v1/auth/register──> Server
  Server <────{user_id, message}─────── Client

登录:
  Client ──POST /api/v1/auth/login───> Server
           {username, password}
  Server <──{access_token, user_info}── Client
            [Set-Cookie: refresh_token]

访问受保护 API:
  Client ──Authorization: Bearer <access>──> Server
  Server <────────────{data}─────────────── Client

Token 过期 → 自动刷新:
  Client ──POST /api/v1/auth/refresh───> Server
           [Cookie: refresh_token]
  Server <────{access_token}─────────── Client

登出:
  Client ──POST /api/v1/auth/logout────> Server
           [Cookie: refresh_token]
  Server 删除 refresh_token 记录
  Server <────{message: "已登出"}──────── Client
```

---

## 4. 数据库变更

### 4.1 users 表扩展

```sql
-- 新增字段
ALTER TABLE admin.users ADD COLUMN refresh_token_jti VARCHAR(64) NULL;
ALTER TABLE admin.users ADD COLUMN refresh_token_expires TIMESTAMPTZ NULL;
ALTER TABLE admin.users ADD COLUMN failed_login_attempts INT DEFAULT 0;
ALTER TABLE admin.users ADD COLUMN locked_until TIMESTAMPTZ NULL;

-- 创建索引
CREATE INDEX idx_users_refresh_token_jti ON admin.users(refresh_token_jti);
```

### 4.2 用户-角色关联表（新建）

```sql
CREATE TABLE admin.user_roles (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES admin.users(id) ON DELETE CASCADE,
    role_id INT NOT NULL REFERENCES admin.roles(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, role_id)
);

CREATE TABLE admin.role_permissions (
    id SERIAL PRIMARY KEY,
    role_id INT NOT NULL REFERENCES admin.roles(id) ON DELETE CASCADE,
    permission_id INT NOT NULL REFERENCES admin.permissions(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(role_id, permission_id)
);
```

---

## 5. API 设计

### 5.1 认证端点

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/api/v1/auth/register` | 无 | 用户注册 |
| POST | `/api/v1/auth/login` | 无 | 用户登录 |
| POST | `/api/v1/auth/refresh` | Refresh Cookie | 刷新 Access Token |
| POST | `/api/v1/auth/logout` | Refresh Cookie | 登出（撤销 Refresh Token） |
| GET | `/api/v1/auth/me` | Access Token | 获取当前用户信息 |
| POST | `/api/v1/auth/change-password` | Access Token | 修改密码 |

### 5.2 请求/响应示例

#### POST /api/v1/auth/register

```json
// Request
{
  "username": "alice",
  "email": "alice@example.com",
  "password": "SecurePass123!"
}

// Response 201
{
  "code": 201,
  "message": "注册成功",
  "data": {
    "id": 42,
    "username": "alice",
    "email": "alice@example.com"
  }
}
```

#### POST /api/v1/auth/login

```json
// Request
{
  "username": "alice",
  "password": "SecurePass123!"
}

// Response 200
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "Bearer",
    "expires_in": 900,
    "user": {
      "id": 42,
      "username": "alice",
      "email": "alice@example.com",
      "role": "user",
      "permissions": ["fund:read", "announcement:read"]
    }
  }
}
// + Set-Cookie: refresh_token=...; HttpOnly; SameSite=Lax; Path=/api/v1/auth; Max-Age=604800
```

#### POST /api/v1/auth/refresh

```json
// Request: Cookie: refresh_token=...
// Response 200
{
  "code": 200,
  "message": "刷新成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "Bearer",
    "expires_in": 900
  }
}
```

### 5.3 错误响应

```json
// 401 Unauthorized
{
  "code": 401,
  "message": "认证失败：Token 已过期或无效"
}

// 403 Forbidden
{
  "code": 403,
  "message": "权限不足：需要管理员权限"
}

// 429 Too Many Requests
{
  "code": 429,
  "message": "登录尝试过多，请 15 分钟后重试"
}
```

---

## 6. 权限分级设计

### 6.1 权限级别

| 级别 | 装饰器 | 说明 |
|------|--------|------|
| PUBLIC | 无 | 无需认证，如基金列表、公告列表 |
| USER | `@require_auth` | 需登录，如收藏、个人设置 |
| ADMIN | `@require_admin` | 需管理员，如用户管理、爬虫控制 |

### 6.2 权限粒度（权限码）

```python
PERMISSIONS = {
    "fund:read":        "查看基金数据",
    "fund:write":       "修改基金数据",
    "announcement:read": "查看公告",
    "announcement:write": "管理公告",
    "crawler:read":     "查看爬虫状态",
    "crawler:write":    "控制爬虫",
    "user:read":        "查看用户信息",
    "user:write":       "管理用户",
    "admin:full":       "全部管理员权限",
}
```

### 6.3 API 端点权限映射（示例）

| API 端点 | 当前状态 | 目标权限 |
|----------|---------|---------|
| GET `/api/search` | PUBLIC | PUBLIC |
| GET `/api/fund-analysis` | PUBLIC | PUBLIC |
| POST `/api/chat-reits` | PUBLIC | USER（限制调用频率） |
| GET `/api/v1/dashboard/stats` | 无 | ADMIN |
| POST `/api/v1/funds` | 无 | ADMIN |
| GET `/api/v1/users` | 无 | ADMIN |

---

## 7. FastAPI 依赖注入设计

### 7.1 core/auth/dependencies.py

```python
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserToken:
    """验证 Access Token，返回用户对象"""
    if not credentials:
        raise HTTPException(status_code=401, detail="缺少认证信息")
    return await jwt.verify_access_token(credentials.credentials)

async def get_current_active_user(
    user: UserToken = Depends(get_current_user)
) -> UserToken:
    """确保用户账号处于激活状态"""
    if user.is_active is False:
        raise HTTPException(status_code=403, detail="账号已被禁用")
    return user

async def require_admin(
    user: UserToken = Depends(get_current_active_user)
) -> UserToken:
    """确保用户具有管理员权限"""
    if user.role != "admin" and "admin:full" not in user.permissions:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user

async def optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[UserToken]:
    """可选认证：有 Token 则解析用户，无则返回 None"""
    if not credentials:
        return None
    try:
        return await jwt.verify_access_token(credentials.credentials)
    except Exception:
        return None
```

### 7.2 路由使用示例

```python
from core.auth.dependencies import get_current_user, require_admin, optional_user

# 公开 API（保持现有行为）
@router.get("/search")
async def search(q: str):
    ...

# 需登录 API
@router.post("/chat-reits")
async def chat_reits(request: ChatRequest, user: UserToken = Depends(get_current_user)):
    # 记录用户调用日志
    ...

# 管理员 API
@router.get("/api/v1/users")
async def list_users(user: UserToken = Depends(require_admin)):
    ...

# 可选认证 API（有登录则个性化，无则默认）
@router.get("/funds/recommended")
async def recommended(user: Optional[UserToken] = Depends(optional_user)):
    if user:
        # 根据用户偏好推荐
        ...
```

---

## 8. 安全策略

### 8.1 速率限制

| 端点 | 限制 | 窗口 |
|------|------|------|
| POST `/auth/register` | 5 次 | 1 小时 |
| POST `/auth/login` | 5 次 | 15 分钟 |
| POST `/auth/refresh` | 20 次 | 1 小时 |
| 其他受保护 API | 100 次 | 1 分钟 |

### 8.2 账号锁定

- 连续 5 次登录失败 → 锁定 15 分钟
- 锁定状态存储在 `users.locked_until` 字段

### 8.3 Token 安全

- Access Token 仅通过 Header 传输（不存 Cookie，防 CSRF）
- Refresh Token 通过 HttpOnly Cookie 传输（防 XSS 窃取）
- 登出时删除数据库中的 `refresh_token_jti`（防重放）
- 密码修改后自动撤销所有 Refresh Token

### 8.4 生产环境强制

- `Secure` Cookie 标志（仅 HTTPS）
- `JWT_SECRET` 环境变量必须设置（DEBUG 模式下允许自动生成）
- Token 签发时检查 `iss` 和 `aud`

---

## 9. 前端接入方案

### 9.1 Token 管理（app-core.js）

```javascript
// TokenManager 单例
class TokenManager {
  getAccessToken() { return localStorage.getItem('access_token'); }
  setAccessToken(token) { localStorage.setItem('access_token', token); }
  clear() { localStorage.removeItem('access_token'); }

  async fetchWithAuth(url, options = {}) {
    const token = this.getAccessToken();
    const headers = {
      ...options.headers,
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    };
    
    let response = await fetch(url, { ...options, headers });
    
    // Token 过期自动刷新
    if (response.status === 401) {
      const refreshed = await this.refreshToken();
      if (refreshed) {
        headers['Authorization'] = `Bearer ${this.getAccessToken()}`;
        response = await fetch(url, { ...options, headers });
      }
    }
    
    return response;
  }

  async refreshToken() {
    const res = await fetch('/api/v1/auth/refresh', {
      method: 'POST',
      credentials: 'include'  // 发送 refresh_token Cookie
    });
    if (res.ok) {
      const data = await res.json();
      this.setAccessToken(data.data.access_token);
      return true;
    }
    this.clear();
    return false;
  }
}
```

### 9.2 登录页面

- 使用现有 `/admin/login` 页面基础
- 成功后存储 `access_token` 到 localStorage
- 调用 `/api/v1/auth/me` 获取用户信息并展示

---

## 10. 测试策略

### 10.1 测试覆盖目标

| 模块 | 测试文件 | 覆盖率目标 |
|------|---------|-----------|
| JWT 生成/验证 | `tests/core/test_jwt.py` | 100% |
| 密码哈希 | `tests/core/test_password.py` | 100% |
| 依赖注入 | `tests/core/test_dependencies.py` | 100% |
| 认证 API | `tests/admin/test_auth_api.py` | 100% |
| 权限检查 | `tests/core/test_permissions.py` | 100% |

### 10.2 关键测试用例

```python
# test_jwt.py
def test_create_access_token():
    token = jwt.create_access_token(user_id="42", username="alice", role="user")
    assert isinstance(token, str)
    payload = jwt.decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["type"] == "access"

def test_expired_token_raises_401():
    expired = jwt.create_access_token(..., expires_delta=timedelta(seconds=-1))
    with pytest.raises(HTTPException) as exc:
        jwt.verify_access_token(expired)
    assert exc.value.status_code == 401

def test_refresh_token_rotation():
    # 刷新后旧 refresh_token 应失效
    old_refresh = jwt.create_refresh_token("42")
    new_access, new_refresh = jwt.refresh_access_token(old_refresh)
    with pytest.raises(HTTPException):
        jwt.refresh_access_token(old_refresh)  # 第二次使用应失败
```

---

## 11. 向后兼容计划

| 阶段 | 操作 | 影响 |
|------|------|------|
| 第1阶段 | 新 JWT 系统上线，管理后台保留 Cookie 认证 | 无影响 |
| 第2阶段 | 管理后台 API（`/api/v1/auth/*`）切换到 JWT | 前端需更新 Token 管理 |
| 第3阶段 | 管理后台 Cookie 认证标记为废弃 | 提醒用户迁移 |
| 第4阶段 | 移除 Cookie HMAC 认证 | 仅影响未迁移客户端 |

---

*Last updated: 2026-04-27*
