# AI API路由注册修复计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 admin_app.py 中注册 AI API 路由，使 /api/ai/* 端点可访问

**Architecture:** 将 api/__init__.py 导出的 router 对象通过 include_router 注册到主 FastAPI app 实例

**Tech Stack:** FastAPI, Tortoise ORM

---

## 问题诊断

AI API 文件已创建并导出：
- `api/chat_reits.py` → `chat_reits_router` (prefix="/api/ai", 端点 "/chat-reits")
- `api/chat_announcement.py` → `chat_announcement_router` (prefix="/api/ai", 端点 "/chat-announcement")
- `api/research.py` → `research_router` (prefix="/api/ai", 端点 "/research")

但 `admin_app.py` 中的主 `app = FastAPI(...)` 实例**从未导入或注册这些路由**，导致所有 `/api/ai/*` 返回 404。

---

## 文件结构

```
backend/
├── admin_app.py           # 主 FastAPI app，需要添加 include_router
└── api/
    ├── __init__.py        # 导出 chat_reits_router, chat_announcement_router, research_router
    ├── chat_reits.py      # router = APIRouter(prefix="/api/ai", ...)
    ├── chat_announcement.py
    └── research.py
```

---

## 维修任务

### Task 1: 在 admin_app.py 中注册 AI API 路由

**Files:**
- Modify: `backend/admin_app.py:71-80` (在 `app = FastAPI(...)` 定义之后)

- [ ] **Step 1: 确认 app 定义位置**

读取 `admin_app.py` 第 71 行附近，确认 `app = FastAPI(...)` 的确切位置和上下文。

- [ ] **Step 2: 添加路由导入**

在 `app = FastAPI(...)` 之后添加：

```python
# AI API 路由注册
from api import chat_reits_router, chat_announcement_router, research_router

app.include_router(chat_reits_router)
app.include_router(chat_announcement_router)
app.include_router(research_router)
```

**注意**: 由于每个 router 已经定义了 `prefix="/api/ai"`，不需要重复指定 prefix。

- [ ] **Step 3: 验证修改**

修改后 `admin_app.py` 应包含：
```python
app = FastAPI(title="REITs Admin", lifespan=lifespan)

# ... 其他中间代码 ...

# AI API 路由注册
from api import chat_reits_router, chat_announcement_router, research_router

app.include_router(chat_reits_router)
app.include_router(chat_announcement_router)
app.include_router(research_router)
```

- [ ] **Step 4: 重启后端服务验证**

```bash
# 测试端点是否注册
curl -s http://localhost:5074/openapi.json | python -c "import sys,json; d=json.load(sys.stdin); print('AI paths:', [p for p in d.get('paths',{}).keys() if 'ai' in p])"

# 测试实际端点
curl -s -X POST http://localhost:5074/api/ai/chat-reits -H "Content-Type: application/json" -d '{"message":"test"}'
```

预期结果：
- openapi.json 包含 `/api/ai/chat-reits`, `/api/ai/chat-announcement`, `/api/ai/research`
- curl 返回 JSON 响应（可能是错误但不是 404）

- [ ] **Step 5: 提交**

```bash
git add backend/admin_app.py
git commit -m "fix: register AI API routers in main app

- Add include_router for chat_reits_router
- Add include_router for chat_announcement_router
- Add include_router for research_router

Fixes 404 errors on all /api/ai/* endpoints"
```

---

## 验证清单

- [ ] `/api/ai/chat-reits` 返回 200 或有意义的错误（非 404）
- [ ] `/api/ai/chat-announcement` 返回 200 或有意义的错误（非 404）
- [ ] `/api/ai/research` 返回 200 或有意义的错误（非 404）
- [ ] 其他已有端点（如 `/api/funds/list`）仍然正常工作

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | — | — |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | CLEAR | 0 issues, plan complete |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | N/A — no UI scope |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | — |

**VERDICT:** ENG CLEARED — ready to implement
