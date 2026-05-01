---
phase: 2
slug: ui-refresh
status: draft
shadcn_initialized: false
preset: none
created: 2026-05-01
---

# Phase 2 — UI Design Contract

> 前端UI深度整改：XSS安全修复、组件化架构、设计系统建立、管理后台重构

---

## Design System

| Property | Value |
|----------|-------|
| Tool | TailwindCSS 3.x (existing) |
| Preset | Custom REITs theme |
| Component library | Vanilla JS components (custom) + ECharts |
| Icon library | Lucide (CDN) — 替换现有混用图标 |
| Font | system-ui stack — 中文优先 "PingFang SC", "Microsoft YaHei", sans-serif |

**决策说明：**
- 不引入 React/Vue（迁移成本过高，当前团队熟悉纯HTML/JS）
- 采用 Web Components 作为组件化方案（原生支持，渐进增强）
- TailwindCSS 继续使用，但建立 design token 文件统一配置

---

## Spacing Scale

Declared values (multiples of 4):

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Icon gaps, inline padding |
| sm | 8px | Compact element spacing, button padding |
| md | 16px | Default element spacing, card padding |
| lg | 24px | Section padding, form group gap |
| xl | 32px | Layout gaps, page sections |
| 2xl | 48px | Major section breaks |
| 3xl | 64px | Page-level spacing |

**Exceptions:**
- 表格行高：40px（非4的倍数，为保证可读性）
- 侧边栏宽度：240px（固定导航宽度）

---

## Typography

| Role | Size | Weight | Line Height | Usage |
|------|------|--------|-------------|-------|
| Body | 14px | 400 | 1.5 | 正文、表格内容 |
| Label | 12px | 500 | 1.4 | 表单标签、表头 |
| Heading | 18px | 600 | 1.3 | 区块标题、卡片标题 |
| Display | 24px | 700 | 1.2 | 页面标题、数据大屏数字 |
| Mono | 13px | 400 | 1.5 | 代码、基金代码、日志 |

**中文适配：**
- 最小字重：400（避免100/200细体中文发虚）
- 行高 ≥ 1.5（中文需要更多呼吸空间）
- 段落 max-width: 65ch（中文阅读舒适宽度）

---

## Color

基于现有 Tailwind 配置，建立统一语义化色彩：

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `#f8fafc` (slate-50) | 页面背景、大面积底色 |
| Secondary (30%) | `#ffffff` | 卡片、面板、弹窗背景 |
| Surface | `#f1f5f9` (slate-100) | 侧边栏、表头背景 |
| Accent (10%) | `#0ea5e9` (sky-500) | 主按钮、活跃状态、链接 |
| Accent Hover | `#0284c7` (sky-600) | 按钮悬停、链接悬停 |
| Success | `#10b981` (emerald-500) | 成功状态、上涨 |
| Warning | `#f59e0b` (amber-500) | 警告、提醒 |
| Destructive | `#ef4444` (red-500) | 删除、错误、下跌 |
| Text Primary | `#0f172a` (slate-900) | 主要文字 |
| Text Secondary | `#64748b` (slate-500) | 次要文字、说明 |
| Border | `#e2e8f0` (slate-200) | 分割线、边框 |

**REITs 专用语义色：**
| Role | Value | Usage |
|------|-------|-------|
| REIT Green | `#10b981` | 上涨、正收益 |
| REIT Red | `#ef4444` | 下跌、负收益 |
| REIT Blue | `#0ea5e9` | 基础设施/交通类板块 |
| REIT Purple | `#8b5cf6` | 产业园/仓储类板块 |
| REIT Orange | `#f97316` | 能源/环保类板块 |

**Accent reserved for:**
- 主操作按钮（CTA）
- 当前选中导航项
- 活跃 Tab 指示器
- 数据图表主系列色

**Never use accent for:**
- 大面积背景（避免视觉疲劳）
- 纯装饰元素
- 非交互文字

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Primary CTA | "保存" / "确认" / "立即查询" |
| Empty state heading | "暂无数据" |
| Empty state body | "当前条件下没有找到相关数据，请尝试调整筛选条件。" |
| Error state | "加载失败，请刷新页面重试。如问题持续，请联系技术支持。" |
| Destructive confirmation | "删除 {item}": "此操作不可撤销，确定要删除吗？" |
| Loading state | "数据加载中..." |
| Success toast | "操作成功" |

**通用文案规范：**
- 使用中文全角标点
- 避免技术术语暴露给用户（如"500 Internal Server Error" → "服务暂时不可用"）
- 按钮动词优先（"保存配置" 而非 "配置保存"）
- 错误文案必须包含下一步行动指引

---

## Component Registry

### 核心组件（自定义 Web Components）

| Component | Purpose | Status |
|-----------|---------|--------|
| `<reit-card>` | 基金信息卡片 | New |
| `<reit-table>` | 数据表格（带排序、分页） | New |
| `<reit-modal>` | 弹窗/对话框 | New |
| `<reit-toast>` | 消息提示 | New |
| `<reit-chart>` | ECharts 封装 | New |
| `<reit-badge>` | 状态标签（涨跌、板块） | New |
| `<reit-nav>` | 侧边栏导航 | Refactor |
| `<reit-form>` | 表单组（含验证） | New |

### 安全组件（XSS防护专用）

| Component | Purpose |
|-----------|---------|
| `<safe-text>` | 自动转义 textContent 渲染 |
| `<safe-html>` | 经 DOMPurify 净化后渲染（仅限可信来源） |
| `<safe-link>` | 带 `rel="noopener noreferrer"` 的链接 |

### 第三方依赖

| Library | Version | Usage |
|---------|---------|-------|
| TailwindCSS | 3.4.x | 原子化CSS |
| ECharts | 5.x | 数据可视化 |
| Lucide | latest (CDN) | 图标系统 |
| DOMPurify | 3.x | XSS 净化（safe-html组件） |

**Registry Safety Gate:**
- shadcn/ui: Not applicable（无React）
- 所有第三方库通过 CDN 引入，版本锁定在 package-lock 或明确指定
- DOMPurify 必须保持最新（安全依赖）

---

## Layout Architecture

### 管理后台布局

```
┌─────────────────────────────────────────┐
│  Header (logo + user + global search)   │  56px
├──────────┬──────────────────────────────┤
│          │                              │
│ Sidebar  │      Main Content            │
│ 240px    │      (scrollable)            │
│          │                              │
├──────────┴──────────────────────────────┤
│  Footer (version + status)              │  32px
└─────────────────────────────────────────┘
```

### 响应式断点

| Breakpoint | Width | Layout Change |
|------------|-------|---------------|
| Mobile | < 768px | 侧边栏折叠为抽屉，表格横向滚动 |
| Tablet | 768-1024px | 侧边栏图标模式，内容区自适应 |
| Desktop | > 1024px | 完整侧边栏，最大内容区 1440px |

---

## XSS Security Contract

### 严格规则

1. **禁止 `innerHTML` 插入用户/外部数据** — 157处全部替换
2. **必须使用 `textContent` 或 `escapeHtml()` 工具函数**
3. **仅 `<safe-html>` 组件可使用 HTML 渲染，且必须经过 DOMPurify**
4. **所有 API 返回数据渲染前默认转义**

### 转义映射

```javascript
const ESCAPE_MAP = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;'
};
```

### 审计检查点

- [ ] 全局搜索 `innerHTML` = 0 处用于外部数据
- [ ] 所有 `document.write` 移除
- [ ] 所有 `eval()` 移除
- [ ] CSP (Content-Security-Policy) 头配置

---

## Admin App Refactor Contract

### 目标：admin_app.py (4870行) → 多层架构

```
backend/admin/
├── __init__.py
├── app.py              # FastAPI 应用实例 (200行)
├── routes/
│   ├── __init__.py
│   ├── auth.py         # 登录/认证路由
│   ├── funds.py        # 基金管理路由
│   ├── announcements.py # 公告管理路由
│   ├── users.py        # 用户管理路由
│   ├── dashboard.py    # 数据看板路由
│   ├── crawlers.py     # 爬虫管理路由
│   └── system.py       # 系统设置/日志路由
├── services/
│   ├── __init__.py
│   ├── fund_service.py
│   ├── announcement_service.py
│   └── user_service.py
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── funds/
│   └── ...
└── static/
    ├── css/
    ├── js/
    └── img/
```

### 迁移原则

1. **路由层**：仅处理 HTTP 请求/响应，无业务逻辑
2. **服务层**：业务逻辑 + 数据校验
3. **模板层**：HTML 模板，禁止内嵌 Python 逻辑（除简单循环）
4. **渐进迁移**：按路由逐个拆分，确保功能不中断

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending
