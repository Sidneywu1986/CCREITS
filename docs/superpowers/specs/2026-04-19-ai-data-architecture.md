# REITs数据平台 AI数据架构设计

## 概述

构建统一的AI数据基础设施，服务于三个独立AI功能：AI聊REITs、AI聊公告、AI投研。数据统一采集、清洗、存储，通过独立AI接口调用。

---

## 数据源架构

```
┌────────────────────────────────────────────────────────────────┐
│                      数据源层                                  │
│  ┌──────────┐  ┌──────────────┐  ┌─────────────────────────┐  │
│  │ 社会热点 │  │ 公众号文章   │  │ REITs基础数据            │  │
│  │ 30分钟   │  │ 每日        │  │ 实时+日更               │  │
│  └────┬─────┘  └──────┬───────┘  └───────────┬─────────────┘  │
│       │              │                      │                 │
└───────┼──────────────┼──────────────────────┼─────────────────┘
        │              │                      │
        ▼              ▼                      ▼
┌────────────────────────────────────────────────────────────────┐
│                     调度层 (APScheduler)                       │
│  统一调度器管理三个爬虫任务的执行时间和频率                      │
└────────────────────────────────────────────────────────────────┘
        │              │                      │
        ▼              ▼                      ▼
┌────────────────────────────────────────────────────────────────┐
│                     清洗层                                      │
│  去重 → 字段标准化 → 异常值处理 → 结构化入库                   │
└────────────────────────────────────────────────────────────────┘
        │              │                      │
        ▼              ▼                      ▼
┌────────────────────────────────────────────────────────────────┐
│                     存储层                                      │
│  ┌────────────┐  ┌──────────────────┐  ┌───────────────────┐  │
│  │ 关系数据库  │  │ Milvus向量库      │  │ 文件存储          │  │
│  │ PostgreSQL │  │ (全文语义检索)   │  │ PDF原文           │  │
│  └────────────┘  └──────────────────┘  └───────────────────┘  │
└────────────────────────────────────────────────────────────────┘
        │              │                      │
        ▼              ▼                      ▼
┌────────────────────────────────────────────────────────────────┐
│                     服务层                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ AI聊REITs  │  │ AI聊公告     │  │ AI投研               │  │
│  │ /api/ai/   │  │ /api/ai/     │  │ /api/ai/research     │  │
│  │ chat-reits │  │ chat-announce│  │                     │  │
│  └─────────────┘  └──────────────┘  └───────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

---

## 一、数据源详情

### 1.1 社会热点爬虫

| 项目 | 说明 |
|------|------|
| **来源** | 微博热搜、东方财富股吧、同花顺社区、雪球 |
| **频率** | 每30分钟轮询 |
| **收集内容** | 帖子标题、正文、发布时间、点赞/评论数、作者 |
| **爬虫技术** | requests + BeautifulSoup + Selenium（需登录） |
| **反爬策略** | 代理IP池、请求延时、Cookie轮换 |

### 1.2 公众号文章爬虫

| 项目 | 说明 |
|------|------|
| **来源** | 巨潮资讯网、证监会指定媒体、机构研报公众号 |
| **频率** | 每日增量爬取 |
| **收集内容** | 文章标题、正文、作者、发布时间、来源媒体 |
| **爬虫技术** | 微信公众号爬虫 + 巨潮资讯API |
| **PDF处理** | pdfplumber解析，提取正文分段存储 |

### 1.3 REITs基础数据

| 项目 | 说明 |
|------|------|
| **来源** | 上交所/深交所API → 巨潮资讯API → 东方财富 |
| **实时行情** | 交易时间3秒轮询 |
| **基础数据** | 日更（基金信息、持仓、季报） |
| **PDF公告** | 入库时解析PDF存文本块 |

---

## 二、数据清洗规则

### 2.1 通用清洗

- **去重**：内容hash（SHA256）排重，过滤完全重复内容
- **广告过滤**：关键词黑名单（"推广"、"广告"、联系方式）
- **异常值标记**：涨跌幅超20%、价格异常等标记待复查

### 2.2 字段标准化

- **基金代码**：统一8位（沪市加0，深市直接）
- **日期格式**：ISO 8601（YYYY-MM-DD）
- **金额单位**：统一"元"，避免万元/亿元混淆

### 2.3 PDF解析规则

1. 下载PDF到本地临时目录
2. pdfplumber解析提取正文
3. 按段落分块，每块500-1500字
4. 超长段落先切分再合并到600字左右
5. 去页眉页脚、空行、特殊字符
6. 存储到 `announcement_content` 表

---

## 三、数据库表结构

### 3.1 AI聊REITs相关表

```sql
-- AI聊天会话
CREATE TABLE ai_chat_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(64),                          -- 用户标识
    session_title VARCHAR(255),                 -- 会话标题
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- AI聊天消息
CREATE TABLE ai_chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    role VARCHAR(20) NOT NULL,                  -- user/assistant/system
    content TEXT NOT NULL,
    agent_name VARCHAR(50),                     -- AI智能体名称（老李/小陈/王博士）
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES ai_chat_sessions(id)
);

-- AI智能体配置
CREATE TABLE ai_chat_agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE,           -- 角色名称
    persona TEXT NOT NULL,                       -- 角色设定
    avatar_url VARCHAR(255),
    system_prompt TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 3.2 AI聊公告相关表

```sql
-- 公告聊天会话
CREATE TABLE announcement_chat_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(64),
    session_title VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 公告聊天消息
CREATE TABLE announcement_chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES announcement_chat_sessions(id)
);

-- 会话关联的公告
CREATE TABLE announcement_chat_contexts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    announcement_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES announcement_chat_sessions(id),
    FOREIGN KEY (announcement_id) REFERENCES announcements(id)
);
```

### 3.3 AI投研相关表

```sql
-- 投研会话
CREATE TABLE research_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(64),
    session_title VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 投研消息
CREATE TABLE research_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES research_sessions(id)
);

-- 投研选中的基金
CREATE TABLE research_funds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    fund_code VARCHAR(10) NOT NULL,
    fund_name VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES research_sessions(id)
);

-- 投研结果（结构化分段存储）
CREATE TABLE research_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    analysis_type VARCHAR(50),                   -- financial/operation/industry/...
    conclusion TEXT,                              -- 核心结论
    supporting_data TEXT,                        -- 支撑数据（JSON数组）
    references TEXT,                             -- 参考来源（JSON数组）
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES research_sessions(id)
);
```

### 3.4 数据内容表（PDF解析）

```sql
-- PDF解析内容表
CREATE TABLE announcement_content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    announcement_id INTEGER NOT NULL,
    chunk_index INTEGER DEFAULT 0,
    content_text TEXT NOT NULL,
    char_count INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (announcement_id) REFERENCES announcements(id)
);

CREATE INDEX idx_content_announcement ON announcement_content(announcement_id);
```

### 3.5 热点数据表

```sql
-- 社会热点
CREATE TABLE social_hotspots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source VARCHAR(50) NOT NULL,                 -- weibo/tonghuashun/xueqiu/...
    title VARCHAR(500),
    content TEXT,
    url VARCHAR(1000),
    author VARCHAR(100),
    publish_time DATETIME,
    sentiment_score FLOAT,                        -- -1到1，正面/负面/中性
    entity_tags TEXT,                             -- JSON，提取的基金代码、板块等
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_hotspot_publish ON social_hotspots(publish_time);
CREATE INDEX idx_hotspot_source ON social_hotspots(source);
```

### 3.6 文章内容表

```sql
-- 公众号/研报文章
CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(500) NOT NULL,
    content TEXT,
    author VARCHAR(200),
    source VARCHAR(200),                         -- 媒体/公众号名称
    source_url VARCHAR(1000),
    publish_time DATETIME,
    category VARCHAR(50),                        -- policy/earnings/industry/research
    related_funds TEXT,                          -- JSON，关联的基金代码列表
    content_hash VARCHAR(64) UNIQUE,             -- 去重
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_article_publish ON articles(publish_time);
CREATE INDEX idx_article_category ON articles(category);
```

---

## 四、向量数据库

### 4.1 Milvus 部署

- **模式**：Milvus Standalone（Docker）
- **维度**：1536维（text-embedding-3-small）
- **存储估算**：2GB原始文档 → 约200-400MB向量

### 4.2 Collection 设计

```python
# 社会热点向量集合
{
    "collection_name": "social_hotspots",
    "fields": [
        {"name": "id", "type": "int64"},
        {"name": "title", "type": "varchar", "max_length": 500},
        {"name": "content", "type": "varchar", "max_length": 4000},
        {"name": "embedding", "type": "float_vector", "dim": 1536},
        {"name": "source", "type": "varchar", "max_length": 50},
        {"name": "publish_time", "type": "datetime"}
    ]
}

# 公告文章向量集合
{
    "collection_name": "announcement_content",
    "fields": [
        {"name": "id", "type": "int64"},
        {"name": "announcement_id", "type": "int64"},
        {"name": "chunk_index", "type": "int32"},
        {"name": "content_text", "type": "varchar", "max_length": 2000},
        {"name": "embedding", "type": "float_vector", "dim": 1536}
    ]
}

# 研报文章向量集合
{
    "collection_name": "articles",
    "fields": [
        {"name": "id", "type": "int64"},
        {"name": "title", "type": "varchar", "max_length": 500},
        {"name": "content", "type": "varchar", "max_length": 4000},
        {"name": "embedding", "type": "float_vector", "dim": 1536},
        {"name": "category", "type": "varchar", "max_length": 50}
    ]
}
```

### 4.3 向量化时机

- **策略**：**异步队列向量化**（入库优先，向量化后台处理）
- **流程**：爬取/解析 → 清洗 → 入库（标记`vectorized=false`）→ 后台队列调用embedding API → 存入Milvus → 更新`vectorized=true`
- **失败处理**：未向量化记录入`vector_pending`队列表，支持重试，不丢数据
- **降级策略**：向量服务不可用时，AI查询降级到PostgreSQL全文检索（`to_tsvector`）

### 4.4 向量待处理队列表

```sql
-- 向量待处理队列
CREATE TABLE vector_pending (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type VARCHAR(20) NOT NULL,           -- hotspot/article/announcement
    source_id INTEGER NOT NULL,
    retry_count INTEGER DEFAULT 0,
    last_retry_at DATETIME,
    status VARCHAR(20) DEFAULT 'pending',        -- pending/processing/failed/done
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_pending_status ON vector_pending(status);
CREATE INDEX idx_pending_retry ON vector_pending(retry_count);
```

### 4.5 Milvus降级策略

**降级触发条件**：Milvus服务不可用（连接超时、查询失败）
**降级方案**：切换到PostgreSQL全文检索
- `announcement_content` 表添加 `fulltext_vector tsvector` 索引
- `social_hotspots` 表添加 `fulltext_vector tsvector` 索引
- `articles` 表添加 `fulltext_vector tsvector` 索引
- AI查询时优先Milvus，失败则自动降级到全文检索
- 降级期间的数据仍正常入库，向量化在Milvus恢复后补处理

---

## 五、爬虫调度

### 5.1 调度器架构

**分离调度策略**：每个数据源独立调度器，故障隔离，互不影响。

```
独立调度器（各自进程）
    │
    ├── HotspotScheduler (30分钟)
    │       └── weibo → tonghuashun → xueqiu
    │
    ├── ArticleScheduler (每日 8:00)
    │       └── wechat → cninfo → other_media
    │
    └── AnnouncementScheduler (每日 6:00, 18:00)
            └── sse → szse → cninfo
```

### 5.2 APScheduler 配置

```python
from apscheduler.schedulers.blocking import BlockingScheduler

scheduler = BlockingScheduler()

# 社会热点 - 30分钟
scheduler.add_job(
    run_hotspot_spider,
    'interval',
    minutes=30,
    id='hotspot_spider',
    name='社会热点爬虫'
)

# 公众号文章 - 每日8点
scheduler.add_job(
    run_article_spider,
    'cron',
    hour=8,
    minute=0,
    id='article_spider',
    name='公众号文章爬虫'
)

# PDF公告 - 每日6点、18点
scheduler.add_job(
    run_announcement_spider,
    'cron',
    hour='6,18',
    minute=0,
    id='announcement_spider',
    name='PDF公告爬虫'
)

scheduler.start()
```

### 5.3 异常处理

- 爬虫失败自动重试（3次，指数退避）
- 失败记录到 `crawl_error_log` 表
- 告警机制：连续失败5次发送通知

---

## 六、AI接口设计

### 6.1 三个独立接口

| 接口 | 用途 | 输入 | 输出 |
|------|------|------|------|
| `POST /api/ai/chat-reits` | AI聊REITs | session_id, message | AI回复 |
| `POST /api/ai/chat-announcement` | AI聊公告 | session_id, message, announcement_ids[] | AI回复 |
| `POST /api/ai/research` | AI投研 | session_id, fund_codes[], analysis_type | 投研报告 |

### 6.2 统一会话响应格式

```json
{
    "success": true,
    "data": {
        "session_id": "xxx",
        "message_id": "xxx",
        "role": "assistant",
        "content": "AI回复内容",
        "agent_name": "老李",        // AI聊REITs时返回
        "sources": [                // 引用来源
            {"type": "hotspot", "id": 1, "title": "..."},
            {"type": "announcement", "id": 2, "title": "..."}
        ],
        "created_at": "2026-04-19T10:00:00Z"
    }
}
```

---

## 七、数据共享策略

### 7.1 共享原则

- **热点数据**：三个AI服务均可查询，用于增强上下文
- **公告PDF内容**：AI聊公告、AI投研使用，不用于AI聊REITs
- **基金基础数据**：三个服务均可用，只读不写
- **向量数据库**：三个集合分属不同collection，通过 `source` 字段区分用途

### 7.2 数据流向

```
爬虫入库 → 文本块存储 → 同步向量化 → Milvus
                              │
                              ▼
                    ┌─────────┴──────────┐
                    │  social_hotspots   │
                    │  announcement_content │
                    │  articles          │
                    └─────────┬──────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
    AI聊REITs          AI聊公告            AI投研
```

---

## 八、实施优先级

| 优先级 | 任务 | 原因 |
|--------|------|------|
| P0 | 现有数据库表梳理 | 基础，稳定优先 |
| P0 | 热点数据爬虫 + 调度 | 数据源补充 |
| P1 | PDF公告解析入库 | 已有pdf_url，改造成本低 |
| P1 | Milvus部署 | 向量检索基础设施 |
| P2 | 公众号文章爬虫 | 增量数据源 |
| P3 | 向量化全量数据 | 后期优化 |
