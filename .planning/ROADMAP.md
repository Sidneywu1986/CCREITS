# ROADMAP — CCREITS 中国公募REITs数据平台

> GSD Roadmap — Phase-driven execution plan. Each phase delivers a shippable outcome.

---

## Milestone v2.1 — 安全加固与前端整改

**Goal:** 修复核心安全漏洞，完成前端UI深度整改，达到生产部署标准。

**Deadline:** 2026-05-31

---

## Phase 1 — 安全审计收尾

**Status:** ✅ Complete

**Goal:** 修复CRITICAL和HIGH安全问题

**Deliverables:**
- 硬编码密码移除
- 异常信息泄露修复
- CORS收窄 + Cookie HMAC签名
- API速率限制部署
- print→logging迁移
- except Exception精确化（87处已收窄）

**Depends on:** —

---

## Phase 2 — 前端UI深度整改

**Status:** ✅ Complete

**Goal:** 解决157处innerHTML XSS漏洞，建立现代前端工程化体系，重构管理后台

**Deliverables:**
- ✅ XSS漏洞全面修复（innerHTML → textContent/escapeHtml）
- ✅ 前端组件化架构设计（8个Web Components，TDD模式）
- ✅ 设计系统建立（色彩、字体、间距、组件规范）
- ✅ 管理后台架构拆分（admin_app.py 4923行 → 13个路由文件 + 多层结构）
- ✅ 响应式布局优化（14页面移动端适配）
- ⏳ 前端构建工具引入（Vite / 现代打包）— 移至 Phase 4
- ⏳ 前端状态管理引入 — 移至 Phase 4

**Depends on:** Phase 1

**UI-SPEC:** `02-UI-SPEC.md`

---

## Phase 3 — API JWT认证体系

**Status:** 🔄 In Progress

**Goal:** 为全部 `/api/*` 端点和管理后台添加统一 JWT 身份验证

**Deliverables:**
- ✅ 技术方案（03-AUTH-SPEC.md + 03-PLAN.md）
- ⏳ JWT 核心模块（生成/验证/刷新/撤销）
- ⏳ 数据库迁移（users 表扩展 + 角色权限关联表）
- ⏳ 认证 API（注册/登录/刷新/登出/改密）
- ⏳ API 权限分级（PUBLIC / USER / ADMIN）
- ⏳ 前端 TokenManager（自动刷新 + 请求拦截）
- ⏳ 速率限制 + 账号锁定
- ⏳ 测试覆盖（核心模块 + API + 集成）

**Depends on:** Phase 2

**Auth-SPEC:** `03-AUTH-SPEC.md`
**Plan:** `03-PLAN.md`

---

## Phase 4 — 性能与稳定性优化

**Status:** ⏳ Pending

**Goal:** 数据库连接池化、缓存优化、监控告警

**Deliverables:**
- asyncpg连接池替代逐请求新建连接
- Redis缓存层引入
- 数据库索引优化
- 健康检查与监控
- 日志聚合与告警

**Depends on:** Phase 3

---

## Milestone v2.2 — 功能增强

**Goal:** 新增投研分析功能，提升数据覆盖度

---

## Phase 5 — 投研分析平台

**Status:** ⏳ Backlog

**Goal:** 深度投研报告、对比分析、估值模型

**Deliverables:**
- 基金对比分析工具
- 估值模型（NAV、IRR、CapRate）
- 投研报告自动生成
- 研报PDF导出

**Depends on:** Milestone v2.1

---

## Phase 6 — 数据覆盖扩展

**Status:** ⏳ Backlog

**Goal:** 接入更多数据源，提升数据质量

**Deliverables:**
- 上交所/深交所官方公告API
- 基金净值自动校准
- 机构持仓数据
- 舆情情绪分析增强

**Depends on:** Phase 5

---

## Out of Scope (v2.x)

- 移动端原生App
- 交易执行系统
- 多市场（港股/新加坡REITs）
- 付费订阅与会员系统

---

*Last updated: 2026-05-01*
