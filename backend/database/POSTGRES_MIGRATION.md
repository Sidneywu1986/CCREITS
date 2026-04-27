# CCREITS PostgreSQL 迁移指南

## 概述

本指南说明如何将 CCREITS 项目从 **SQLite** 主业务数据库迁移到 **PostgreSQL**。

> **版本**: 3.0.0  
> **目标**: 统一使用 PostgreSQL（业务数据 + AI 数据），通过 Schema 隔离不同域。

---

## 一、架构变化

### 迁移前 (v2.x)

```
┌─────────────────┐     ┌─────────────────┐
│   SQLite        │     │   PostgreSQL    │
│   reits.db      │     │   ai_db         │
│                 │     │                 │
│  · funds        │     │  · ai_chat_*    │
│  · quotes       │     │  · research_*   │
│  · price_history│     │  · articles     │
│  · announcements│     │  · vector_pending│
│  · dividends    │     └─────────────────┘
│  · daily_data   │
└─────────────────┘
```

### 迁移后 (v3.0)

```
┌──────────────────────────────────────────┐
│           PostgreSQL: reits              │
│                                          │
│  ┌──────────────┐  ┌──────────────────┐ │
│  │  business    │  │       ai         │ │
│  │  schema      │  │     schema       │ │
│  │              │  │                  │ │
│  │ · funds      │  │ · ai_chat_*      │ │
│  │ · quotes     │  │ · research_*     │ │
│  │ · price_hist │  │ · articles       │ │
│  │ · dividends  │  │ · vector_pending │ │
│  │ · reit_*     │  └──────────────────┘ │
│  │ · reits_*    │  ┌──────────────────┐ │
│  │ · announce   │  │      admin       │ │
│  └──────────────┘  │     schema       │ │
│                    │ · users          │ │
│                    │ · roles          │ │
│                    └──────────────────┘ │
└──────────────────────────────────────────┘
```

---

## 二、前置条件

### 1. 安装 PostgreSQL

```bash
# macOS (Homebrew)
brew install postgresql@15
brew services start postgresql@15

# Ubuntu/Debian
sudo apt update && sudo apt install postgresql-15 postgresql-contrib

# 创建数据库
createdb reits
```

### 2. 安装 Python 依赖

```bash
# 新增依赖
pip install psycopg2-binary asyncpg

# 或使用 requirements.txt（已更新）
pip install -r backend/requirements.txt
```

### 3. 确认 SQLite 源数据

```bash
# 检查数据库文件存在
ls -la backend/database/reits.db

# 查看表结构
sqlite3 backend/database/reits.db ".tables"
```

---

## 三、执行迁移

### 步骤 1: 创建 PostgreSQL Schema

```bash
# 使用 psql 执行 schema 文件
psql postgresql://postgres:postgres@localhost:5432/reits \
  -f backend/database/postgres_schema.sql
```

### 步骤 2: 迁移数据

```bash
cd backend/database

# 方式 A: 使用默认配置
python migrate_sqlite_to_postgres.py

# 方式 B: 自定义连接
export SQLITE_PATH="/path/to/reits.db"
export POSTGRES_DSN="postgresql://user:pass@host:5432/reits"
python migrate_sqlite_to_postgres.py

# 方式 C: 仅预览 (不写入)
export DRY_RUN=true
python migrate_sqlite_to_postgres.py
```

### 步骤 3: 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`:

```env
DB_TYPE=postgres
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/reits
PG_HOST=localhost
PG_PORT=5432
PG_USER=postgres
PG_PASSWORD=postgres
PG_DATABASE=reits
```

### 步骤 4: 启动服务验证

```bash
cd backend
python admin_app.py
```

---

## 四、Schema 详解

### business 业务 Schema

| 表名 | 说明 | 来源 |
|------|------|------|
| `funds` | 基金基础信息（兼容原 funds + RSDS product_info） | schema.sql / RSDS |
| `quotes` | 实时行情快照 | schema.sql |
| `price_history` | 日K线（兼容 price_history + daily_data） | schema.sql |
| `fund_prices` | 基金价格（兼容 fund_analysis.py 查询） | 代码查询 |
| `dividends` | 分红派息（兼容 dividends + RSDS） | schema.sql / RSDS |
| `announcements` | 公告 + 微信文章（合并 announcements + wechat_articles） | schema.sql |
| `wechat_articles` | 微信公众号/研报文章 | schema.sql |
| `market_indices` | 大盘指数 | index_schema.sql |
| `data_sources` | 数据源追踪 | schema.sql |
| `update_logs` | 更新日志 | schema.sql |
| `data_lineage` | RSDS 数据血缘 | RSDS v1.1.2 |
| `reit_property_info` | 产权类资产信息 | RSDS v1.1.2 |
| `reit_lease_detail` | 租约明细 | RSDS v1.1.2 |
| `reit_financial_metrics` | 财务指标 | RSDS v1.1.2 |
| `reit_operational_data` | 运营数据 | RSDS v1.1.2 |
| `reit_market_performance` | 市场表现 | RSDS v1.1.2 |
| `reit_investor_structure` | 投资者结构 | RSDS v1.1.2 |
| `reit_risk_metrics` | 风险指标 | RSDS v1.1.2 |
| `reits_operation_detail` | 经营权类运营明细 | RSDS v1.1.2 |
| `reits_financial_recon` | 财务勾稽 | RSDS v1.1.2 |
| `reits_valuation_assumptions` | 估值假设 | RSDS v1.1.2 |
| `reits_competitor_gis` | 同业竞争 | RSDS v1.1.2 |
| `reits_operation_risk` | 运营风险信号 | RSDS v1.1.2 |
| `reits_market_anomaly` | 二级市场异常 | RSDS v1.1.2 |
| `reits_regulatory_inquiry` | 监管问询 | RSDS v1.1.2 |
| `reits_compliance_base` | 合规与权利限制 | RSDS v1.1.2 |

### ai AI Schema

| 表名 | 说明 |
|------|------|
| `ai_chat_sessions` | AI 聊天会话 |
| `ai_chat_messages` | AI 聊天消息（含 tsvector 全文索引） |
| `ai_chat_agents` | AI 智能体配置 |
| `announcement_chat_sessions` | 公告聊天会话 |
| `announcement_chat_messages` | 公告聊天消息 |
| `announcement_chat_contexts` | 公告上下文关联 |
| `research_sessions` | 投研会话 |
| `research_messages` | 投研消息 |
| `research_funds` | 投研基金关联 |
| `research_results` | 投研结果 |
| `announcement_contents` | 公告内容解析 |
| `social_hotspots` | 社会热点 |
| `articles` | 公众号/研报文章 |
| `vector_pending` | 向量待处理队列 |
| `crawl_error_logs` | 爬虫错误日志 |

### admin 管理 Schema

| 表名 | 说明 |
|------|------|
| `users` | 后台用户 |
| `roles` | 角色 |
| `permissions` | 权限 |
| `user_roles` | 用户-角色关联 |
| `role_permissions` | 角色-权限关联 |

---

## 五、代码适配清单

迁移后，以下代码需要逐步从 `sqlite3` 改为 `psycopg2` / `asyncpg`:

| 文件 | 当前方式 | 建议方案 |
|------|---------|---------|
| `api/fund_analysis.py` | `sqlite3.connect(DB_PATH)` | `psycopg2.connect(**settings.PG_CONFIG)` |
| `api/chat_reits.py` | `sqlite3.connect(db_path)` | `psycopg2.connect(**settings.PG_CONFIG)` |
| `api/dividend_calendar.py` | `sqlite3.connect(db_path)` | `psycopg2.connect(**settings.PG_CONFIG)` |
| `api/search.py` | `sqlite3.connect(DB_PATH)` | `psycopg2.connect(**settings.PG_CONFIG)` |
| `api/ws_chat.py` | `sqlite3.connect(db_path)` | `psycopg2.connect(**settings.PG_CONFIG)` |
| `admin_app.py` | `Tortoise + sqlite` | `Tortoise + asyncpg` |

### 快速适配示例

**Before (SQLite):**
```python
import sqlite3
conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.execute("SELECT * FROM funds WHERE fund_code = ?", (code,))
row = cursor.fetchone()
```

**After (PostgreSQL):**
```python
import psycopg2
from psycopg2.extras import RealDictCursor
from core.config import settings

conf = settings.PG_CONFIG
dsn = f"postgresql://{conf['user']}:{conf['password']}@{conf['host']}:{conf['port']}/{conf['database']}"
conn = psycopg2.connect(dsn, cursor_factory=RealDictCursor)
cursor = conn.cursor()
cursor.execute("SELECT * FROM business.funds WHERE fund_code = %s", (code,))
row = cursor.fetchone()
```

---

## 六、回滚方案

如需回退到 SQLite:

```env
# .env
DB_TYPE=sqlite
DATABASE_URL=sqlite:///./database/reits.db
```

无需删除 PostgreSQL 数据，切换环境变量即可。

---

## 七、性能优化建议

1. **分区表**: `price_history` / `fund_prices` 数据量大时按 `trade_date` 范围分区
2. **连接池**: 使用 `psycopg2.pool.ThreadedConnectionPool`
3. **读写分离**: 查询走只读副本，写入走主库
4. **VACUUM**: 定期执行 `VACUUM ANALYZE`

---

## 八、常见问题

**Q1: 迁移后 psycopg2 连接失败？**  
检查 PostgreSQL 服务是否启动，用户密码是否正确，数据库 `reits` 是否已创建。

**Q2: Schema 未找到？**  
确保执行了 `postgres_schema.sql`，或检查 `search_path` 设置。

**Q3: 保留 SQLite 做备份？**  
可以。迁移脚本不会修改 SQLite 原文件，保留作为备份。

**Q4: 需要安装 PostgreSQL 扩展？**  
本 Schema 仅使用标准功能 + `tsvector`（PostgreSQL 内置），无需额外扩展。
