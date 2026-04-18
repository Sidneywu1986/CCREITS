# REITs数据平台 AI数据系统实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建统一的AI数据基础设施，服务于三个独立AI功能：AI聊REITs、AI聊公告、AI投研

**Architecture:** 分离调度策略（每个数据源独立进程）+ 异步向量化队列 + PostgreSQL全文检索降级

**Tech Stack:** Python/Flask, PostgreSQL, Milvus (Docker), APScheduler, pdfplumber

---

## 一、文件结构

```
backend/
├── ai_db/
│   ├── __init__.py
│   ├── models.py              # Tortoise ORM模型（AI相关9张表）
│   ├── schemas.py             # Pydantic schemas
│   └── migrations/             # 数据库迁移脚本
├── vector/
│   ├── __init__.py
│   ├── milvus_client.py       # Milvus连接管理
│   ├── embedding_service.py    # Embedding API调用（国产）
│   ├── vector_queue.py         # 异步向量化队列
│   └── fulltext_index.py      # PostgreSQL全文索引降级
├── crawlers/
│   ├── __init__.py
│   ├── base_scheduler.py      # 调度器基类
│   ├── hotspot_scheduler.py    # 社会热点调度器（30分钟）
│   ├── article_scheduler.py    # 公众号文章调度器（每日8点）
│   └── announcement_scheduler.py  # PDF公告调度器（每日6/18点）
├── api/
│   ├── __init__.py
│   ├── chat_reits.py          # POST /api/ai/chat-reits
│   ├── chat_announcement.py   # POST /api/ai/chat-announcement
│   └── research.py            # POST /api/ai/research
├── cleaners/
│   ├── __init__.py
│   ├── deduplication.py       # SHA256去重
│   ├── field_normalizer.py    # 字段标准化
│   └── pdf_parser.py          # PDF解析（pdfplumber）
└── config.py                 # 统一配置（DB/ Milvus/ API keys）
```

---

## 二、任务清单

### Task 1: 数据库迁移 - SQLite到PostgreSQL + 新表创建

**Files:**
- Create: `backend/ai_db/migrations/001_initial_ai_schema.sql`
- Create: `backend/ai_db/__init__.py`
- Create: `backend/ai_db/models.py`
- Modify: `backend/config.py`

- [ ] **Step 1: 创建PostgreSQL迁移脚本**

```sql
-- backend/ai_db/migrations/001_initial_ai_schema.sql

-- 1. AI聊天会话表
CREATE TABLE IF NOT EXISTS ai_chat_sessions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(64),
    session_title VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. AI聊天消息表
CREATE TABLE IF NOT EXISTS ai_chat_messages (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES ai_chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    agent_name VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. AI智能体配置表
CREATE TABLE IF NOT EXISTS ai_chat_agents (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    persona TEXT NOT NULL,
    avatar_url VARCHAR(255),
    system_prompt TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. 公告聊天会话表
CREATE TABLE IF NOT EXISTS announcement_chat_sessions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(64),
    session_title VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. 公告聊天消息表
CREATE TABLE IF NOT EXISTS announcement_chat_messages (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES announcement_chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. 会话关联公告表
CREATE TABLE IF NOT EXISTS announcement_chat_contexts (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES announcement_chat_sessions(id) ON DELETE CASCADE,
    announcement_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. 投研会话表
CREATE TABLE IF NOT EXISTS research_sessions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(64),
    session_title VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. 投研消息表
CREATE TABLE IF NOT EXISTS research_messages (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. 投研选中基金表
CREATE TABLE IF NOT EXISTS research_funds (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    fund_code VARCHAR(10) NOT NULL,
    fund_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 10. 投研结果表（结构化分段存储）
CREATE TABLE IF NOT EXISTS research_results (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    analysis_type VARCHAR(50),
    conclusion TEXT,
    supporting_data TEXT,
    references TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 11. PDF解析内容表
CREATE TABLE IF NOT EXISTS announcement_content (
    id SERIAL PRIMARY KEY,
    announcement_id INTEGER NOT NULL,
    chunk_index INTEGER DEFAULT 0,
    content_text TEXT NOT NULL,
    char_count INTEGER,
    fulltext_vector tsvector,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 12. 社会热点表
CREATE TABLE IF NOT EXISTS social_hotspots (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    title VARCHAR(500),
    content TEXT,
    url VARCHAR(1000),
    author VARCHAR(100),
    publish_time TIMESTAMP,
    sentiment_score FLOAT,
    entity_tags TEXT,
    fulltext_vector tsvector,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 13. 公众号/研报文章表
CREATE TABLE IF NOT EXISTS articles (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    content TEXT,
    author VARCHAR(200),
    source VARCHAR(200),
    source_url VARCHAR(1000),
    publish_time TIMESTAMP,
    category VARCHAR(50),
    related_funds TEXT,
    content_hash VARCHAR(64) UNIQUE,
    fulltext_vector tsvector,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 14. 向量待处理队列表
CREATE TABLE IF NOT EXISTS vector_pending (
    id SERIAL PRIMARY KEY,
    source_type VARCHAR(20) NOT NULL,
    source_id INTEGER NOT NULL,
    retry_count INTEGER DEFAULT 0,
    last_retry_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 15. 爬虫错误日志表
CREATE TABLE IF NOT EXISTS crawl_error_log (
    id SERIAL PRIMARY KEY,
    spider_name VARCHAR(50),
    error_type VARCHAR(50),
    error_message TEXT,
    url TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_content_announcement ON announcement_content(announcement_id);
CREATE INDEX IF NOT EXISTS idx_content_fulltext ON announcement_content USING GIN(fulltext_vector);
CREATE INDEX IF NOT EXISTS idx_hotspot_publish ON social_hotspots(publish_time);
CREATE INDEX IF NOT EXISTS idx_hotspot_source ON social_hotspots(source);
CREATE INDEX IF NOT EXISTS idx_hotspot_fulltext ON social_hotspots USING GIN(fulltext_vector);
CREATE INDEX IF NOT EXISTS idx_article_publish ON articles(publish_time);
CREATE INDEX IF NOT EXISTS idx_article_category ON articles(category);
CREATE INDEX IF NOT EXISTS idx_article_fulltext ON articles USING GIN(fulltext_vector);
CREATE INDEX IF NOT EXISTS idx_pending_status ON vector_pending(status);
CREATE INDEX IF NOT EXISTS idx_pending_retry ON vector_pending(retry_count);
CREATE INDEX IF NOT EXISTS idx_crawl_error_spider ON crawl_error_log(spider_name);

-- 初始化默认AI智能体
INSERT INTO ai_chat_agents (name, persona, system_prompt) VALUES
('老李', '资深市场分析师，从业20年，说话稳重，喜欢用数据说话',
 '你是一位资深的REITs市场分析师，拥有20年资本市场经验。你的分析风格严谨务实，善于用数据支撑观点。'),
('小陈', '年轻活跃的散户投资者，思维活跃，关注短期机会',
 '你是一位活跃的个人投资者，投资风格偏激进，喜欢研究短期交易机会。'),
('王博士', '学术派研究员，深耕REITs领域，善于挖掘底层资产价值',
 '你是一位REITs领域的学术研究员，专注于底层资产分析和长期价值投资研究。');
```

- [ ] **Step 2: 创建Python模型文件**

```python
# backend/ai_db/models.py
from tortoise import fields
from tortoise.models import Model


class AiChatSession(Model):
    id = fields.IntField(pk=True)
    user_id = fields.CharField(max_length=64, null=True)
    session_title = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "ai_chat_sessions"


class AiChatMessage(Model):
    id = fields.IntField(pk=True)
    session = fields.ForeignKeyField("models.AiChatSession", related_name="messages")
    role = fields.CharField(max_length=20)
    content = fields.TextField()
    agent_name = fields.CharField(max_length=50, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "ai_chat_messages"


class AiChatAgent(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=50, unique=True)
    persona = fields.TextField()
    avatar_url = fields.CharField(max_length=255, null=True)
    system_prompt = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "ai_chat_agents"


class AnnouncementChatSession(Model):
    id = fields.IntField(pk=True)
    user_id = fields.CharField(max_length=64, null=True)
    session_title = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "announcement_chat_sessions"


class AnnouncementChatMessage(Model):
    id = fields.IntField(pk=True)
    session = fields.ForeignKeyField("models.AnnouncementChatSession", related_name="messages")
    role = fields.CharField(max_length=20)
    content = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "announcement_chat_messages"


class AnnouncementChatContext(Model):
    id = fields.IntField(pk=True)
    session = fields.ForeignKeyField("models.AnnouncementChatSession", related_name="contexts")
    announcement_id = fields.IntField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "announcement_chat_contexts"


class ResearchSession(Model):
    id = fields.IntField(pk=True)
    user_id = fields.CharField(max_length=64, null=True)
    session_title = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "research_sessions"


class ResearchMessage(Model):
    id = fields.IntField(pk=True)
    session = fields.ForeignKeyField("models.ResearchSession", related_name="messages")
    role = fields.CharField(max_length=20)
    content = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "research_messages"


class ResearchFund(Model):
    id = fields.IntField(pk=True)
    session = fields.ForeignKeyField("models.ResearchSession", related_name="funds")
    fund_code = fields.CharField(max_length=10)
    fund_name = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "research_funds"


class ResearchResult(Model):
    id = fields.IntField(pk=True)
    session = fields.ForeignKeyField("models.ResearchSession", related_name="results")
    analysis_type = fields.CharField(max_length=50, null=True)
    conclusion = fields.TextField(null=True)
    supporting_data = fields.TextField(null=True)
    references = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "research_results"


class AnnouncementContent(Model):
    id = fields.IntField(pk=True)
    announcement_id = fields.IntField()
    chunk_index = fields.IntField(default=0)
    content_text = fields.TextField()
    char_count = fields.IntField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "announcement_content"


class SocialHotspot(Model):
    id = fields.IntField(pk=True)
    source = fields.CharField(max_length=50)
    title = fields.CharField(max_length=500, null=True)
    content = fields.TextField(null=True)
    url = fields.CharField(max_length=1000, null=True)
    author = fields.CharField(max_length=100, null=True)
    publish_time = fields.DatetimeField(null=True)
    sentiment_score = fields.FloatField(null=True)
    entity_tags = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "social_hotspots"


class Article(Model):
    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=500)
    content = fields.TextField(null=True)
    author = fields.CharField(max_length=200, null=True)
    source = fields.CharField(max_length=200, null=True)
    source_url = fields.CharField(max_length=1000, null=True)
    publish_time = fields.DatetimeField(null=True)
    category = fields.CharField(max_length=50, null=True)
    related_funds = fields.TextField(null=True)
    content_hash = fields.CharField(max_length=64, unique=True, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "articles"


class VectorPending(Model):
    id = fields.IntField(pk=True)
    source_type = fields.CharField(max_length=20)
    source_id = fields.IntField()
    retry_count = fields.IntField(default=0)
    last_retry_at = fields.DatetimeField(null=True)
    status = fields.CharField(max_length=20, default="pending")
    error_message = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "vector_pending"


class CrawlErrorLog(Model):
    id = fields.IntField(pk=True)
    spider_name = fields.CharField(max_length=50, null=True)
    error_type = fields.CharField(max_length=50, null=True)
    error_message = fields.TextField(null=True)
    url = fields.TextField(null=True)
    retry_count = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "crawl_error_log"
```

- [ ] **Step 3: 更新配置文件**

```python
# backend/config.py 新增配置

# AI数据系统配置
AI_DB_CONFIG = {
    "type": "postgresql",
    "host": os.getenv("AI_DB_HOST", "localhost"),
    "port": int(os.getenv("AI_DB_PORT", "5432")),
    "user": os.getenv("AI_DB_USER", "postgres"),
    "password": os.getenv("AI_DB_PASSWORD", "postgres"),
    "database": os.getenv("AI_DB_NAME", "reits_ai"),
}

# Milvus配置
MILVUS_CONFIG = {
    "host": os.getenv("MILVUS_HOST", "localhost"),
    "port": int(os.getenv("MILVUS_PORT", "19530")),
    "collection_dim": 1536,
    "metric_type": "IP",
}

# Embedding API配置（国产）
EMBEDDING_CONFIG = {
    "provider": os.getenv("EMBEDDING_PROVIDER", "baidu"),  # baidu/qianfan/tencent
    "api_key": os.getenv("EMBEDDING_API_KEY", ""),
    "model": os.getenv("EMBEDDING_MODEL", "embedding-v1"),
    "dimension": 1536,
}

# LLM配置（分层）
LLM_CONFIG = {
    "reits": {  # AI聊REITs - 低成本
        "provider": "deepseek",
        "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
        "model": "deepseek-chat",
        "temperature": 0.7,
    },
    "announcement": {  # AI聊公告 - 强模型
        "provider": "openai",
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "model": "gpt-4o-mini",
        "temperature": 0.3,
    },
    "research": {  # AI投研 - 强模型
        "provider": "openai",
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "model": "gpt-4o",
        "temperature": 0.5,
    },
}

# 爬虫调度配置
CRAWLER_SCHEDULER_CONFIG = {
    "hotspot_interval_minutes": 30,
    "article_cron_hour": 8,
    "announcement_cron_hours": [6, 18],
    "max_retries": 3,
    "alert_threshold": 5,
}
```

- [ ] **Step 4: 创建数据库迁移脚本**

```bash
# backend/ai_db/migrations/run_migration.sh
#!/bin/bash
# 运行PostgreSQL迁移

psql -h $AI_DB_HOST -U $AI_DB_USER -d $AI_DB_NAME -f 001_initial_ai_schema.sql
```

- [ ] **Step 5: 提交**

```bash
git add backend/ai_db/
git add backend/config.py
git commit -m "feat: add AI database schema and models for PostgreSQL"
```

---

### Task 2: Milvus部署 + 向量客户端

**Files:**
- Create: `backend/vector/milvus_client.py`
- Create: `backend/vector/embedding_service.py`
- Create: `backend/docker-compose-milvus.yml`
- Modify: `backend/config.py`

- [ ] **Step 1: 创建Milvus Docker Compose文件**

```yaml
# backend/docker-compose-milvus.yml
version: '3.8'

services:
  milvus:
    image: milvusdb/milvus:v3.1.0
    container_name: milvus
    ports:
      - "19530:19530"
      - "9091:9091"
    environment:
      ETCD_USE_EMBED: "true"
      COMMON_STORAGETYPE: "local"
    volumes:
      - ./milvus/data:/var/lib/milvus/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9091/healthz"]
      interval: 30s
      timeout: 20s
      retries: 3
```

- [ ] **Step 2: 创建Milvus客户端**

```python
# backend/vector/milvus_client.py
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class MilvusClient:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.alias = "default"
        self._connected = False

    def connect(self):
        if not self._connected:
            connections.connect(alias=self.alias, host=self.host, port=self.port)
            self._connected = True
        return self

    def disconnect(self):
        if self._connected:
            connections.disconnect(alias=self.alias)
            self._connected = False

    def create_collection_if_not_exists(self, name: str, dim: int, description: str = ""):
        if utility.has_collection(name):
            return Collection(name)
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=2000),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
        ]
        schema = CollectionSchema(fields=fields, description=description)
        collection = Collection(name=name, schema=schema)
        collection.create_index(field_name="embedding", index_params={"metric_type": "IP", "index_type": "IVF_FLAT", "params": {"nlist": 128}})
        return collection

    def insert(self, collection_name: str, data: List[Dict[str, Any]]):
        collection = Collection(collection_name)
        entities = [d["embedding"] for d in data]
        texts = [d["content"] for d in data]
        result = collection.insert([texts, entities])
        collection.flush()
        return result

    def search(self, collection_name: str, query_vector: List[float], top_k: int = 5, expr: str = None):
        collection = Collection(collection_name)
        collection.load()
        search_params = {"metric_type": "IP", "params": {"nprobe": 10}}
        results = collection.search(
            data=[query_vector],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=["content"]
        )
        return results

    def is_healthy(self) -> bool:
        try:
            self.connect()
            utility.server_version()
            return True
        except Exception as e:
            logger.warning(f"Milvus health check failed: {e}")
            return False


# 全局单例
_milvus_client = None

def get_milvus_client() -> MilvusClient:
    global _milvus_client
    if _milvus_client is None:
        from backend.config import MILVUS_CONFIG
        _milvus_client = MilvusClient(
            host=MILVUS_CONFIG["host"],
            port=MILVUS_CONFIG["port"]
        )
    return _milvus_client
```

- [ ] **Step 3: 创建Embedding服务**

```python
# backend/vector/embedding_service.py
from typing import List
import logging
import hashlib
import time

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self, provider: str, api_key: str, model: str, dimension: int = 1536):
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.dimension = dimension

    def embed_text(self, text: str) -> List[float]:
        if self.provider == "baidu":
            return self._baidu_embed(text)
        elif self.provider == "qianfan":
            return self._qianfan_embed(text)
        elif self.provider == "openai":
            return self._openai_embed(text)
        else:
            raise ValueError(f"Unknown embedding provider: {self.provider}")

    def _baidu_embed(self, text: str) -> List[float]:
        import requests
        url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/embeddings/embedding-v1"
        headers = {"Content-Type": "application/json"}
        data = {"input": text[:2000]}  # 截断超长文本
        try:
            response = requests.post(url, json=data, headers=headers, params={"access_token": self.api_key}, timeout=30)
            result = response.json()
            return result["data"][0]["embedding"]
        except Exception as e:
            logger.error(f"Baidu embedding failed: {e}")
            raise

    def _qianfan_embed(self, text: str) -> List[float]:
        import requests
        url = "https://qianfan.baidubce.com/v2/embeddings"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        data = {"input": text[:2000], "model": self.model}
        try:
            response = requests.post(url, json=data, headers=headers, timeout=30)
            result = response.json()
            return result["data"][0]["embedding"]
        except Exception as e:
            logger.error(f"Qianfan embedding failed: {e}")
            raise

    def _openai_embed(self, text: str) -> List[float]:
        import openai
        client = openai.OpenAI(api_key=self.api_key)
        response = client.embeddings.create(input=text[:2000], model="text-embedding-3-small")
        return response.data[0].embedding


# 全局单例
_embedding_service = None

def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        from backend.config import EMBEDDING_CONFIG
        _embedding_service = EmbeddingService(
            provider=EMBEDDING_CONFIG["provider"],
            api_key=EMBEDDING_CONFIG["api_key"],
            model=EMBEDDING_CONFIG["model"],
            dimension=EMBEDDING_CONFIG["dimension"]
        )
    return _embedding_service
```

- [ ] **Step 4: 提交**

```bash
git add backend/vector/
git add backend/docker-compose-milvus.yml
git commit -m "feat: add Milvus client and embedding service"
```

---

### Task 3: PDF解析 + 异步向量队列

**Files:**
- Create: `backend/cleaners/pdf_parser.py`
- Create: `backend/vector/vector_queue.py`
- Create: `backend/vector/fulltext_index.py`

- [ ] **Step 1: PDF解析器**

```python
# backend/cleaners/pdf_parser.py
import pdfplumber
import hashlib
from typing import List, Tuple
import logging
import re

logger = logging.getLogger(__name__)

class PDFParser:
    def __init__(self, chunk_min_chars: int = 500, chunk_max_chars: int = 1500, target_chunk_chars: int = 600):
        self.chunk_min_chars = chunk_min_chars
        self.chunk_max_chars = chunk_max_chars
        self.target_chunk_chars = target_chunk_chars

    def parse_and_chunk(self, pdf_path: str) -> List[Tuple[int, str, int]]:
        """
        解析PDF并分块
        返回: [(chunk_index, content_text, char_count), ...]
        """
        chunks = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    text = self._clean_text(text)
                    full_text += text + "\n"

            # 按段落分割
            paragraphs = self._split_into_paragraphs(full_text)
            chunks = self._merge_paragraphs(paragraphs)

        except Exception as e:
            logger.error(f"PDF parsing failed for {pdf_path}: {e}")
            raise

        return chunks

    def _clean_text(self, text: str) -> str:
        # 去除页眉页脚（常见模式）
        text = re.sub(r'第\d+页', '', text)
        text = re.sub(r'Page \d+', '', text)
        # 去除多余空行
        text = re.sub(r'\n{3,}', '\n\n', text)
        # 去除特殊字符（保留中文、英文、数字、常用标点）
        text = re.sub(r'[^\w\s\u4e00-\u9fff，。、！？；：""''（）【】《》]', '', text)
        return text.strip()

    def _split_into_paragraphs(self, text: str) -> List[str]:
        # 按换行+空行分割
        paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 50]

    def _merge_paragraphs(self, paragraphs: List[str]) -> List[Tuple[int, str, int]]:
        chunks = []
        current_chunk = ""
        chunk_index = 0

        for para in paragraphs:
            if len(current_chunk) + len(para) < self.target_chunk_chars:
                current_chunk += para + "\n"
            else:
                if current_chunk.strip():
                    chunks.append((chunk_index, current_chunk.strip(), len(current_chunk)))
                    chunk_index += 1
                # 如果单个段落超过最大长度，先切分再合并
                if len(para) > self.chunk_max_chars:
                    sub_chunks = self._split_long_paragraph(para)
                    for sub in sub_chunks[:-1]:
                        chunks.append((chunk_index, sub, len(sub)))
                        chunk_index += 1
                    current_chunk = sub_chunks[-1] + "\n"
                else:
                    current_chunk = para + "\n"

        if current_chunk.strip():
            chunks.append((chunk_index, current_chunk.strip(), len(current_chunk)))

        return chunks

    def _split_long_paragraph(self, text: str) -> List[str]:
        # 按句子分割（。！？）
        sentences = re.split(r'([。！？])', text)
        merged = []
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                merged.append(sentences[i] + sentences[i + 1])
            else:
                merged.append(sentences[i])
        # 合并到目标长度
        result = []
        current = ""
        for s in merged:
            if len(current) + len(s) < self.target_chunk_chars:
                current += s
            else:
                if current:
                    result.append(current)
                current = s
        if current:
            result.append(current)
        return result


def calculate_content_hash(content: str) -> str:
    return hashlib.sha256(content.encode('utf-8')).hexdigest()
```

- [ ] **Step 2: 异步向量队列处理器**

```python
# backend/vector/vector_queue.py
from backend.ai_db.models import VectorPending
from backend.vector.milvus_client import get_milvus_client
from backend.vector.embedding_service import get_embedding_service
from typing import Dict, Any
import logging
import asyncio

logger = logging.getLogger(__name__)

class VectorQueueProcessor:
    def __init__(self):
        self.batch_size = 10
        self.max_retries = 3

    async def process_pending(self):
        """处理待向量化的记录"""
        pending_records = await VectorPending.filter(status="pending").limit(self.batch_size).all()

        for record in pending_records:
            try:
                await self._vectorize_record(record)
                record.status = "done"
                await record.save()
            except Exception as e:
                logger.error(f"Vectorization failed for {record.source_type}:{record.source_id}: {e}")
                record.retry_count += 1
                record.last_retry_at = asyncio.get_event_loop().time()
                record.error_message = str(e)[:500]
                if record.retry_count >= self.max_retries:
                    record.status = "failed"
                await record.save()

    async def _vectorize_record(self, record: VectorPending):
        if record.source_type == "announcement":
            await self._vectorize_announcement(record.source_id)
        elif record.source_type == "hotspot":
            await self._vectorize_hotspot(record.source_id)
        elif record.source_type == "article":
            await self._vectorize_article(record.source_id)

    async def _vectorize_announcement(self, announcement_id: int):
        from backend.ai_db.models import AnnouncementContent
        contents = await AnnouncementContent.filter(announcement_id=announcement_id).all()

        milvus = get_milvus_client()
        embed_service = get_embedding_service()
        milvus.connect()
        collection = milvus.create_collection_if_not_exists("announcement_content", dim=1536)

        for content in contents:
            embedding = embed_service.embed_text(content.content_text)
            milvus.insert("announcement_content", [{"content": content.content_text, "embedding": embedding}])

    async def _vectorize_hotspot(self, hotspot_id: int):
        from backend.ai_db.models import SocialHotspot
        hotspot = await SocialHotspot.filter(id=hotspot_id).first()
        if not hotspot:
            return

        milvus = get_milvus_client()
        embed_service = get_embedding_service()
        milvus.connect()
        collection = milvus.create_collection_if_not_exists("social_hotspots", dim=1536)

        text = f"{hotspot.title}\n{hotspot.content}"
        embedding = embed_service.embed_text(text)
        milvus.insert("social_hotspots", [{"content": text, "embedding": embedding}])

    async def _vectorize_article(self, article_id: int):
        from backend.ai_db.models import Article
        article = await Article.filter(id=article_id).first()
        if not article:
            return

        milvus = get_milvus_client()
        embed_service = get_embedding_service()
        milvus.connect()
        collection = milvus.create_collection_if_not_exists("articles", dim=1536)

        text = f"{article.title}\n{article.content}"
        embedding = embed_service.embed_text(text)
        milvus.insert("articles", [{"content": text, "embedding": embedding}])


# 后台任务入口
async def run_vector_queue_worker():
    processor = VectorQueueProcessor()
    while True:
        try:
            await processor.process_pending()
            await asyncio.sleep(5)  # 每5秒检查一次
        except Exception as e:
            logger.error(f"Vector queue worker error: {e}")
            await asyncio.sleep(30)
```

- [ ] **Step 3: PostgreSQL全文检索降级**

```python
# backend/vector/fulltext_index.py
from backend.ai_db.models import AnnouncementContent, SocialHotspot, Article
from tortoise.expressions import Q

class FulltextSearch:
    """Milvus降级时的PostgreSQL全文检索"""

    @staticmethod
    async def search_announcements(query: str, top_k: int = 5):
        """搜索公告内容"""
        results = await AnnouncementContent.filter(
            Q(content_text__icontains=query)
        ).limit(top_k).all()
        return results

    @staticmethod
    async def search_hotspots(query: str, top_k: int = 5):
        """搜索社会热点"""
        results = await SocialHotspot.filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        ).limit(top_k).all()
        return results

    @staticmethod
    async def search_articles(query: str, top_k: int = 5):
        """搜索文章"""
        results = await Article.filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        ).limit(top_k).all()
        return results
```

- [ ] **Step 4: 提交**

```bash
git add backend/cleaners/
git add backend/vector/
git commit -m "feat: add PDF parser and async vectorization queue"
```

---

### Task 4: 分离爬虫调度器

**Files:**
- Create: `backend/crawlers/base_scheduler.py`
- Create: `backend/crawlers/hotspot_scheduler.py`
- Create: `backend/crawlers/article_scheduler.py`
- Create: `backend/crawlers/announcement_scheduler.py`

- [ ] **Step 1: 调度器基类**

```python
# backend/crawlers/base_scheduler.py
import logging
from abc import ABC, abstractmethod
from typing import Callable
import asyncio
from backend.ai_db.models import CrawlErrorLog

logger = logging.getLogger(__name__)

class BaseScheduler(ABC):
    def __init__(self, name: str, max_retries: int = 3, alert_threshold: int = 5):
        self.name = name
        self.max_retries = max_retries
        self.alert_threshold = alert_threshold
        self.consecutive_failures = 0

    @abstractmethod
    async def crawl(self):
        """执行爬取逻辑，子类实现"""
        pass

    async def run(self):
        """调度器运行入口"""
        for attempt in range(self.max_retries):
            try:
                await self.crawl()
                self.consecutive_failures = 0
                logger.info(f"{self.name}: crawl successful")
                return
            except Exception as e:
                logger.warning(f"{self.name}: attempt {attempt + 1} failed: {e}")
                await self._log_error(str(e))
                if attempt == self.max_retries - 1:
                    self.consecutive_failures += 1
                    if self.consecutive_failures >= self.alert_threshold:
                        await self._send_alert()

    async def _log_error(self, error_msg: str):
        await CrawlErrorLog.create(
            spider_name=self.name,
            error_type="crawl_failure",
            error_message=error_msg[:1000],
            retry_count=self.max_retries
        )

    async def _send_alert(self):
        """连续失败告警（可扩展：邮件/钉钉/飞书）"""
        logger.error(f"ALERT: {self.name} failed {self.consecutive_failures} times consecutively")
```

- [ ] **Step 2: 社会热点调度器**

```python
# backend/crawlers/hotspot_scheduler.py
from backend.crawlers.base_scheduler import BaseScheduler
from backend.ai_db.models import SocialHotspot
from backend.cleaners.deduplication import DeduplicationCleaner
import hashlib
import httpx
from typing import List, Dict
import asyncio

class HotspotScheduler(BaseScheduler):
    def __init__(self):
        super().__init__(name="hotspot_spider", max_retries=3, alert_threshold=5)
        self.interval_minutes = 30
        self.dedup = DeduplicationCleaner()

    async def crawl(self):
        """爬取微博热搜、东方财富股吧、同花顺、雪球"""
        all_items = []

        # 微博热搜
        weibo_items = await self._crawl_weibo()
        all_items.extend(weibo_items)

        # 东方财富股吧
        eastmoney_items = await self._crawl_eastmoney()
        all_items.extend(eastmoney_items)

        # 去重并入库
        await self._save_hotspots(all_items)

    async def _crawl_weibo(self) -> List[Dict]:
        """爬取微博热搜"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://weibo.com/ajax/side/hotSearch",
                    timeout=10
                )
                data = response.json()
                items = []
                for item in data.get("data", {}).get("realtime", [])[:20]:
                    items.append({
                        "source": "weibo",
                        "title": item.get("word", ""),
                        "url": f"https://s.weibo.com/weibo?q={item.get('word', '')}",
                        "publish_time": None,
                        "content": item.get("raw_hot", ""),
                    })
                return items
        except Exception as e:
            self.logger.warning(f"Weibo crawl failed: {e}")
            return []

    async def _crawl_eastmoney(self) -> List[Dict]:
        """爬取东方财富股吧REITs相关帖子"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://guba.eastmoney.com/list/reits",
                    timeout=10
                )
                # 解析HTML获取帖子列表
                # 简化示例，实际使用BeautifulSoup解析
                return []
        except Exception as e:
            self.logger.warning(f"Eastmoney crawl failed: {e}")
            return []

    async def _save_hotspots(self, items: List[Dict]):
        for item in items:
            # SHA256去重检查
            content_hash = hashlib.sha256(
                f"{item['source']}:{item['title']}".encode()
            ).hexdigest()

            existing = await SocialHotspot.filter(
                source=item["source"],
                title=item["title"]
            ).first()

            if not existing:
                await SocialHotspot.create(
                    source=item["source"],
                    title=item["title"],
                    content=item.get("content"),
                    url=item.get("url"),
                    author=item.get("author"),
                    publish_time=item.get("publish_time"),
                    entity_tags="[]"
                )


# 调度器运行入口
if __name__ == "__main__":
    scheduler = HotspotScheduler()
    while True:
        asyncio.run(scheduler.run())
        import time
        time.sleep(scheduler.interval_minutes * 60)
```

- [ ] **Step 3: 提交**

```bash
git add backend/crawlers/
git commit -m "feat: add separated crawler schedulers (hotspot/article/announcement)"
```

---

### Task 5: AI接口服务

**Files:**
- Create: `backend/api/chat_reits.py`
- Create: `backend/api/chat_announcement.py`
- Create: `backend/api/research.py`

- [ ] **Step 1: AI聊REITs接口**

```python
# backend/api/chat_reits.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from backend.ai_db.models import AiChatSession, AiChatMessage, AiChatAgent
from backend.vector.milvus_client import get_milvus_client
from backend.vector.fulltext_index import FulltextSearch
import httpx
import logging

router = APIRouter(prefix="/api/ai", tags=["AI聊天"])
logger = logging.getLogger(__name__)


class ChatReitsRequest(BaseModel):
    session_id: Optional[int] = None
    message: str
    agent_name: Optional[str] = "老李"


class ChatReitsResponse(BaseModel):
    session_id: int
    message_id: int
    role: str
    content: str
    agent_name: str
    sources: List[dict]


@router.post("/chat-reits", response_model=ChatReitsResponse)
async def chat_reits(req: ChatReitsRequest):
    # 1. 获取或创建会话
    if req.session_id:
        session = await AiChatSession.filter(id=req.session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = await AiChatSession.create(session_title="新对话")

    # 2. 保存用户消息
    user_msg = await AiChatMessage.create(
        session=session,
        role="user",
        content=req.message
    )

    # 3. 获取Agent配置
    agent = await AiChatAgent.filter(name=req.agent_name).first()
    if not agent:
        agent = await AiChatAgent.filter(name="老李").first()

    # 4. 检索相关热点（降级策略：Milvus不可用时用全文检索）
    sources = await _retrieve_sources(req.message, top_k=3)

    # 5. 调用LLM
    response_text = await _call_llm(
        provider="deepseek",
        messages=[
            {"role": "system", "content": agent.system_prompt or agent.persona},
            {"role": "user", "content": req.message}
        ]
    )

    # 6. 保存AI回复
    ai_msg = await AiChatMessage.create(
        session=session,
        role="assistant",
        content=response_text,
        agent_name=agent.name
    )

    return ChatReitsResponse(
        session_id=session.id,
        message_id=ai_msg.id,
        role="assistant",
        content=response_text,
        agent_name=agent.name,
        sources=sources
    )


async def _retrieve_sources(query: str, top_k: int = 3) -> List[dict]:
    """检索相关数据源（Milvus优先，降级到全文检索）"""
    try:
        milvus = get_milvus_client()
        if milvus.is_healthy():
            embed_service = # get embedding service
            query_embedding = embed_service.embed_text(query)
            results = milvus.search("social_hotspots", query_embedding, top_k=top_k)
            return [{"type": "hotspot", "id": r.id, "title": r.entity.get("content", "")[:100]} for r in results]
    except Exception as e:
        logger.warning(f"Milvus search failed, falling back to fulltext: {e}")

    # 降级到全文检索
    hotspots = await FulltextSearch.search_hotspots(query, top_k)
    return [{"type": "hotspot", "id": h.id, "title": h.title[:100]} for h in hotspots]


async def _call_llm(provider: str, messages: List[dict], temperature: float = 0.7) -> str:
    """调用LLM API"""
    if provider == "deepseek":
        api_key = # get from config
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                json={"model": "deepseek-chat", "messages": messages, "temperature": temperature},
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=60
            )
            return response.json()["choices"][0]["message"]["content"]
    elif provider == "openai":
        # similar implementation
        pass
```

- [ ] **Step 2: AI聊公告接口**

```python
# backend/api/chat_announcement.py
@router.post("/chat-announcement", response_model=ChatReitsResponse)
async def chat_announcement(req: ChatAnnouncementRequest):
    # 1. 获取会话
    if req.session_id:
        session = await AnnouncementChatSession.filter(id=req.session_id).first()
    else:
        session = await AnnouncementChatSession.create()

    # 2. 关联公告
    for ann_id in req.announcement_ids:
        await AnnouncementChatContext.create(session=session, announcement_id=ann_id)

    # 3. 保存消息并调用LLM
    # ... 类似实现，检索公告内容
```

- [ ] **Step 3: AI投研接口**

```python
# backend/api/research.py
@router.post("/research")
async def research(req: ResearchRequest):
    # 1. 创建投研会话
    session = await ResearchSession.create(session_title=f"投研-{','.join(req.fund_codes)}")

    # 2. 关联基金
    for code in req.fund_codes:
        await ResearchFund.create(session=session, fund_code=code)

    # 3. 收集基金数据（行情+公告+季报）

    # 4. 调用强模型生成报告
    report = await _generate_research_report(session, req.fund_codes, req.analysis_type)

    # 5. 保存结构化结果
    result = await ResearchResult.create(
        session=session,
        analysis_type=req.analysis_type,
        conclusion=report["conclusion"],
        supporting_data=report["supporting_data"],
        references=report["references"]
    )

    return {"session_id": session.id, "result_id": result.id}
```

- [ ] **Step 4: 提交**

```bash
git add backend/api/
git commit -m "feat: add AI chat and research API endpoints"
```

---

## 三、实施顺序

| 顺序 | 任务 | 预计时间 | 依赖 |
|------|------|----------|------|
| 1 | Task 1: 数据库迁移 | 2小时 | 无 |
| 2 | Task 2: Milvus部署 | 1小时 | Task 1完成 |
| 3 | Task 3: PDF解析+向量队列 | 3小时 | Task 2完成 |
| 4 | Task 4: 爬虫调度器 | 4小时 | Task 1完成 |
| 5 | Task 5: AI接口服务 | 3小时 | Task 1,2,3完成 |

---

## 四、验证清单

- [ ] PostgreSQL数据库连接正常，9张新表创建成功
- [ ] Milvus Docker容器运行正常，`/api/healthz` 返回200
- [ ] PDF解析测试：上传测试PDF，分块正确（每块500-1500字）
- [ ] 向量化队列：记录正确进入pending状态，失败重试3次
- [ ] 爬虫调度器：独立进程运行，30分钟/8点/18点触发正确
- [ ] AI聊REITs：session创建，消息存储，LLM调用正常
- [ ] 降级策略：停止Milvus后，AI查询自动切换到PostgreSQL全文检索
