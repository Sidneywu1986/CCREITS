# Phase 4 — 性能与稳定性优化

## Wave 1: asyncpg 连接池 + 数据库索引
- `core/db_pool.py` — 全局 asyncpg 连接池（min=5, max=20）
- 替换全部 14 处 `asyncpg.connect` → `pool.acquire()`
- 数据库索引：announcements.publish_date, funds.fund_code, users.username

## Wave 2: Redis 缓存层
- `core/cache.py` — aioredis 封装（get/set/delete/ttl）
- 缓存高频 API：基金列表、公告列表、搜索热点
- 缓存失效策略：写入时清除 + TTL

## Wave 3: 健康检查 + 监控
- 统一 `/health` 端点（DB + Redis + Milvus 状态）
- `/metrics` 端点（请求数、响应时间、错误率）
- 系统资源监控（CPU、内存、磁盘）
