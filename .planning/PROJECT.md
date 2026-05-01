# CCREITS — 中国公募REITs数据平台

## What This Is

中国公募REITs（基础设施证券投资基金）一站式数据平台。提供实时行情、公告追踪、分红日历、AI问答、投研分析等核心功能，覆盖全部79只公募REITs基金。面向个人投资者和机构研究员。

## Core Value

**让 REITs 投资者第一时间获取准确的行情、公告和投研数据。** 数据准确性和实时性是平台生命线。

## Requirements

### Validated

- ✓ 79只REITs基金基础数据管理（基金列表、板块分类、基本信息）
- ✓ 实时行情数据采集与展示（价格、涨跌幅、成交量）
- ✓ 公告爬虫与检索（巨潮资讯网、AKShare、公众号文章同步）
- ✓ 分红日历与派息率计算
- ✓ AI问答系统（RAG检索 + LLM多智能体对话）
- ✓ 管理后台（基金CRUD、公告管理、用户管理、系统监控）
- ✓ 数据看板（市场指数、板块概况、实时行情大屏）

### Active

- [ ] 前端UI深度整改（XSS安全、组件化、设计系统、工程化升级）
- [ ] API JWT认证（当前全部 `/api/*` 端点公开访问）
- [ ] 前端 innerHTML XSS 修复（~157处未转义注入）
- [ ] 管理后台架构拆分（admin_app.py 4870行单体文件重构）
- [ ] 生产环境安全加固（Cookie、CORS、速率限制已修复，JWT待完成）

### Out of Scope

- 交易执行（仅提供数据，不涉及买卖）
- 移动端 App（当前为Web响应式，暂不做原生App）
- 多市场支持（当前仅A股REITs，暂不支持港股/新加坡REITs）
- 付费订阅系统（当前免费使用，商业化暂不规划）

## Context

**技术环境：**
- 后端：Python 3.11 + FastAPI + PostgreSQL + Milvus + AKShare
- 前端：纯 HTML/JS（admin-pro/frontend/），TailwindCSS, ECharts
- 部署：Git main 分支，本地开发环境

**技术债务：**
- 前端无现代框架（无React/Vue），纯HTML/JS拼接，维护困难
- admin_app.py 4870行单体文件，路由/HTML模板/业务逻辑/DB操作混杂
- 157处 `innerHTML` 未转义外部数据，存在XSS风险
- 全部 `/api/*` 端点无身份验证
- 数据库连接逐请求新建，未使用连接池

**已知问题（已修复）：**
- 硬编码密码已改为环境变量
- 异常信息泄露已修复（`str(e)` 不再返回客户端）
- CORS已收窄，Cookie已加HMAC签名
- API速率限制已部署
- print已迁移为logging

## Constraints

- **Tech stack**: 前端当前为纯HTML/JS，整改需考虑迁移成本与兼容性
- **Timeline**: 需要尽快修复XSS和JWT认证（安全红线）
- **Dependencies**: AKShare数据源稳定性不可控，需有降级策略
- **Compatibility**: 前端整改不能影响现有管理后台功能
- **Security**: 生产环境部署前必须完成JWT认证和XSS修复

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 使用纯HTML/JS而非现代框架（初期） | 快速原型，降低前端复杂度 | ⚠️ Revisit — 当前维护困难，需考虑升级 |
| PostgreSQL + Milvus 双数据库 | 结构化数据用PG，向量检索用Milvus | ✓ Good — 满足RAG检索需求 |
| AKShare作为主要数据源 | 国内金融数据免费开源 | ✓ Good — 数据覆盖全 |
| FastAPI而非Django | 轻量异步，适合实时数据API | ✓ Good — 性能满足需求 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-01 after security audit completion*
