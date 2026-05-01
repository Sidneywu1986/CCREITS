# Phase 3 — API JWT 认证体系实施计划

> **Goal:** 建立统一的 JWT 认证体系，覆盖管理后台和 API 端点
> **Spec:** `03-AUTH-SPEC.md`

---

## Wave 1: 核心认证基础设施（TDD 模式）

### 目标
建立 JWT 生成/验证/刷新核心模块，完成数据库迁移，所有核心逻辑通过单元测试。

### 任务清单

- [ ] **1.1 创建 `backend/core/auth/` 目录结构**
  - `__init__.py`
  - `jwt.py` — JWT 创建、验证、刷新
  - `password.py` — 密码哈希/验证封装
  - `dependencies.py` — FastAPI Depends（get_current_user, require_admin, optional_user）
  - `permissions.py` — 权限码定义和检查

- [ ] **1.2 实现 `core/auth/jwt.py`**
  - `create_access_token(user_id, username, role, permissions, expires_delta=15min)`
  - `create_refresh_token(user_id, expires_delta=7days)`
  - `verify_access_token(token)` → 返回 UserToken 对象
  - `verify_refresh_token(token)` → 返回用户 ID
  - `refresh_access_token(refresh_token)` → 生成新的 access + refresh token 对
  - `revoke_refresh_token(user_id)` → 清除数据库中的 refresh_token_jti

- [ ] **1.3 实现 `core/auth/password.py`**
  - `hash_password(plain)` → bcrypt hash
  - `verify_password(plain, hashed)` → bool
  - 统一封装，替换路由中分散的 `from passlib.hash import bcrypt`

- [ ] **1.4 实现 `core/auth/dependencies.py`**
  - `get_current_user` — 从 Authorization Header 解析 Access Token
  - `get_current_active_user` — 额外检查 is_active
  - `require_admin` — 检查 is_superuser 或 admin:full 权限
  - `optional_user` — 可选认证，无 Token 返回 None

- [ ] **1.5 实现 `core/auth/permissions.py`**
  - `Permission` 枚举类（fund:read, fund:write, announcement:read 等）
  - `has_permission(user, permission_code)` — 检查用户是否拥有指定权限
  - `RolePermissions` 映射（role → [permissions]）

- [ ] **1.6 数据库迁移**
  - `users` 表新增：`refresh_token_jti`, `refresh_token_expires`, `failed_login_attempts`, `locked_until`
  - 新建 `user_roles` 关联表
  - 新建 `role_permissions` 关联表
  - 创建 Alembic 迁移脚本（或 SQL 脚本）

- [ ] **1.7 Pydantic Schemas**
  - `RegisterRequest` / `RegisterResponse`
  - `LoginRequest` / `LoginResponse`（扩展：添加 access_token, expires_in）
  - `RefreshResponse`
  - `UserInfo`（从 /me 返回）
  - `ChangePasswordRequest`

- [ ] **1.8 TDD 测试套件**
  - `tests/core/test_jwt.py` — JWT 生成/验证/过期/刷新（≥15 用例）
  - `tests/core/test_password.py` — 哈希/验证（≥5 用例）
  - `tests/core/test_dependencies.py` — 依赖注入模拟（≥10 用例）
  - `tests/core/test_permissions.py` — 权限检查（≥8 用例）

### 验收标准
- [ ] `pytest tests/core/test_*.py` 全部通过
- [ ] JWT Token 创建/验证/刷新/撤销流程端到端正确
- [ ] 密码哈希模块与现有 bcrypt 输出兼容
- [ ] 数据库迁移脚本可重复执行（幂等）

---

## Wave 2: 认证 API 与路由接入

### 目标
替换现有 `admin/routes/auth.py` 为完整 JWT 认证 API，为 `api/` 目录端点添加可选认证依赖。

### 任务清单

- [ ] **2.1 重写 `admin/routes/auth.py`**
  - `POST /api/v1/auth/register` — 用户注册（唯一用户名/邮箱校验）
  - `POST /api/v1/auth/login` — 用户登录（生成 Access + Refresh Token，设置 Cookie）
  - `POST /api/v1/auth/refresh` — 刷新 Access Token（读取 Cookie，验证，生成新 Token 对）
  - `POST /api/v1/auth/logout` — 登出（撤销 Refresh Token，删除 Cookie）
  - `GET /api/v1/auth/me` — 获取当前用户信息（解析 Access Token，查数据库）
  - `POST /api/v1/auth/change-password` — 修改密码（撤销所有 Refresh Token）

- [ ] **2.2 速率限制中间件**
  - 登录端点：5 次/15 分钟/IP
  - 注册端点：5 次/小时/IP
  - 使用 `slowapi` 或基于 Redis 的内存实现

- [ ] **2.3 账号锁定机制**
  - 登录失败计数 `failed_login_attempts += 1`
  - 连续 5 次失败 → `locked_until = now + 15min`
  - 登录成功 → 重置失败计数

- [ ] **2.4 为 `api/` 目录添加可选认证**
  - `api/chat_reits.py` — `POST /chat-reits` 添加 `optional_user` 依赖
  - `api/search.py` — `GET /search` 保持 PUBLIC，可选认证用于个性化
  - `api/fund_analysis.py` — `POST /analyze-funds` 添加 `get_current_user`
  - 其余 API 根据 SPEC 中的权限映射表逐步接入

- [ ] **2.5 管理后台路由适配**
  - `admin/routes/dashboard.py` — 统计 API 添加 `require_admin`
  - `admin/routes/funds.py` — 基金管理 API 添加 `require_admin`
  - `admin/routes/users.py` — 用户管理 API 添加 `require_admin`
  - 其他管理路由按需添加权限检查

- [ ] **2.6 测试：认证 API 集成测试**
  - `tests/admin/test_auth_api.py` — 注册/登录/刷新/登出端到端（≥12 用例）
  - `tests/api/test_auth_protected.py` — 受保护 API 访问控制（≥10 用例）

### 验收标准
- [ ] 注册 → 登录 → 访问 API → 刷新 Token → 登出 全流程可运行
- [ ] 速率限制和账号锁定生效
- [ ] 未认证访问受保护 API 返回 401
- [ ] 普通用户访问管理员 API 返回 403
- [ ] `pytest tests/admin/test_auth_api.py` + `tests/api/test_auth_protected.py` 全部通过

---

## Wave 3: 前端接入与集成测试

### 目标
前端实现 Token 管理器，登录页面接入 JWT，全链路集成测试。

### 任务清单

- [ ] **3.1 前端 TokenManager（`js/auth.js`）**
  - `login(username, password)` → 调用 API，存储 access_token
  - `logout()` → 调用 API，清除 localStorage
  - `fetchWithAuth(url, options)` → 自动附加 Authorization Header
  - `refreshToken()` → 自动刷新（在 401 时触发）
  - `getUserInfo()` → 解析 JWT payload（无需 API 调用）

- [ ] **3.2 登录页面更新**
  - `admin-pro/frontend/login.html` 或现有 `/admin/login`
  - 表单提交调用 `/api/v1/auth/login`
  - 成功：存储 token，跳转首页
  - 失败：显示错误信息

- [ ] **3.3 全局请求拦截**
  - `app-core.js` 中的 fetch 调用替换为 `TokenManager.fetchWithAuth`
  - 或在 `app-core.js` 中注入 fetch 拦截器
  - 401 时自动跳转登录页

- [ ] **3.4 用户信息展示**
  - 页面头部显示当前登录用户名
  - 登录/登出按钮状态切换

- [ ] **3.5 集成测试**
  - `tests/integration/test_auth_flow.py` — 浏览器模拟全流程
  - 或 Postman/Newman 集合

### 验收标准
- [ ] 前端可完成注册 → 登录 → 访问受保护页面 → 登出
- [ ] Token 过期后自动刷新，用户无感知
- [ ] 登出后清除 Token，访问受保护页面跳转登录
- [ ] 所有集成测试通过

---

## 依赖与风险

### 依赖
- Wave 1 依赖：`python-jose`（或 `PyJWT`），`passlib`（已安装）
- Wave 2 依赖：Wave 1 核心模块完成
- Wave 3 依赖：Wave 2 API 完成

### 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| JWT Secret 泄露 | 高 | 生产环境强制环境变量，定期轮换 |
| Refresh Token 被盗 | 中 | HttpOnly Cookie + 撤销机制 + 短有效期 |
| 大量 Token 验证影响性能 | 中 | 考虑 Redis 缓存已验证 Token 状态 |
| 现有 API 客户端不兼容 | 中 | 新认证 API 并行运行，逐步迁移 |
| 测试环境 JWT Secret 缺失 | 低 | DEBUG 模式自动生成，CI 注入 |

---

## 工具与库

| 库 | 用途 | 状态 |
|----|------|------|
| `python-jose[cryptography]` | JWT 生成/验证 | 待安装 |
| `passlib[bcrypt]` | 密码哈希（已安装） | ✅ |
| `slowapi` | 速率限制 | 待评估 |
| `pytest-asyncio` | 异步测试 | 待确认 |

---

*Last updated: 2026-04-27*
