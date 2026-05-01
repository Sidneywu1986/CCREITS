# Phase 2 — 前端UI深度整改 · 执行计划

> Plan derived from UI-SPEC.md. Wave-based execution with verification gates.

---

## Goal

修复157处innerHTML XSS漏洞，建立现代前端工程化体系，重构4870行单体admin_app.py为多层架构，使前端达到生产部署安全标准。

---

## Waves

### Wave 1 — XSS 紧急修复（安全红线）

**Priority:** P0 — 安全漏洞必须立即修复
**Estimated:** 2-3 小时

**Plans:**

1. **全局 innerHTML 审计**
   - 扫描全部 `innerHTML` 使用点（~157处）
   - 分类：外部数据注入 / 内部HTML拼接 / 第三方库使用
   - 输出：`xss-audit-report.md`

2. **核心转义工具强化**
   - 验证 `escapeHtml()` 函数覆盖完整性（`app-core.js`, `common.js`）
   - 确保转义 `< > & " '` 全部五个字符
   - 添加 `escapeHtml` 到全局命名空间，所有页面可访问

3. **高危页面批量修复**
   - 按风险排序修复：用户输入展示页 > 公告列表 > 基金详情 > 管理后台
   - 修复模式：`el.innerHTML = data` → `el.textContent = data` 或 `el.innerHTML = escapeHtml(data)`
   - 优先修复外部API数据直接渲染的点

4. **Verification**
   - 全局搜索 `innerHTML` = 仅保留内部模板拼接（确认无外部数据）
   - 运行测试脚本验证页面无XSS告警

---

### Wave 2 — 设计系统基础设施

**Priority:** P1 — 为后续组件化打基础
**Estimated:** 3-4 小时
**Depends on:** Wave 1

**Plans:**

1. **Tailwind 配置统一**
   - 创建 `tailwind.config.js` design token 文件
   - 定义色彩系统（参考 UI-SPEC Color 章节）
   - 定义间距、字体、圆角 token
   - 确保与现有 Tailwind 类名兼容

2. **CSS 架构重构**
   - 创建 `frontend/css/design-system.css`
   - 提取通用变量：colors, spacing, typography, shadows
   - 清理现有散落在各页面的内联样式和 `<style>` 标签
   - 建立 BEM 命名规范或 Tailwind 原子类统一用法

3. **图标系统统一**
   - 引入 Lucide Icons（CDN）
   - 替换现有混用图标（FontAwesome/图片/inline SVG）
   - 创建 `frontend/js/icons.js` 统一管理图标映射

4. **Verification**
   - 所有页面样式一致，无样式回归
   - 图标全部替换完成

---

### Wave 3 — 组件化架构（Web Components）

**Priority:** P1 — 降低维护复杂度
**Estimated:** 4-6 小时
**Depends on:** Wave 2

**Plans:**

1. **核心组件开发**
   - `<reit-card>` — 基金信息卡片（代码、名称、涨跌幅、板块标签）
   - `<reit-table>` — 数据表格（排序、分页、搜索、空状态）
   - `<reit-modal>` — 弹窗/对话框（确认、表单、详情）
   - `<reit-toast>` — 消息提示（成功、错误、警告）
   - `<reit-badge>` — 状态标签（涨跌色、板块色、优先级）

2. **安全组件开发**
   - `<safe-text>` — textContent 自动渲染（防XSS）
   - `<safe-html>` — DOMPurify 净化渲染（仅限可信来源）
   - 所有组件内部禁止使用 `innerHTML` 渲染 props

3. **组件注册与加载**
   - 创建 `frontend/js/components/index.js`
   - 按需加载机制（非所有页面加载全部组件）
   - 组件文档（Props、Events、Slots、CSS Variables）

4. **Verification**
   - 至少3个核心页面使用新组件替换旧实现
   - 组件在 Chrome/Firefox/Safari 测试通过

---

### Wave 4 — 管理后台重构

**Priority:** P1 — 解决4870行单体文件
**Estimated:** 6-8 小时
**Depends on:** Wave 3

**Plans:**

1. **目录结构创建**
   ```
   backend/admin/
   ├── __init__.py
   ├── app.py              # FastAPI 实例 + 中间件
   ├── routes/             # 路由层（仅HTTP处理）
   ├── services/           # 业务逻辑层
   ├── templates/          # Jinja2 HTML模板
   └── static/             # CSS/JS/图片
   ```

2. **路由拆分**
   - `auth.py` — 登录/登出/Cookie验证
   - `funds.py` — 基金CRUD、导入导出
   - `announcements.py` — 公告管理、爬虫触发
   - `users.py` — 用户管理
   - `dashboard.py` — 数据看板、统计
   - `crawlers.py` — 爬虫配置、日志、状态
   - `system.py` — 系统设置、日志查看、完整性检查

3. **服务层提取**
   - 从 admin_app.py 提取业务逻辑到 services/
   - 每个 service 对应一个业务领域
   - 服务层负责：数据校验、数据库操作、外部调用

4. **模板提取**
   - 将内联 HTML 字符串提取到 `templates/` 目录
   - 使用 Jinja2 模板继承（base.html → 各页面）
   - 模板中所有动态数据使用 `escapeHtml` 或自动转义

5. **渐进迁移**
   - 逐个路由迁移，每迁移一个即测试
   - 保持 URL 不变，确保前端调用不受影响
   - 旧 admin_app.py 逐步瘦身，最终删除

6. **Verification**
   - 所有管理后台功能测试通过
   - admin_app.py 行数 < 500 行（仅剩入口和配置）

---

### Wave 5 — 响应式优化与工程化

**Priority:** P2 — 提升用户体验
**Estimated:** 3-4 小时
**Depends on:** Wave 4

**Plans:**

1. **响应式布局**
   - 断点：Mobile (<768px), Tablet (768-1024px), Desktop (>1024px)
   - 侧边栏折叠为抽屉（Mobile）
   - 表格横向滚动优化（Mobile）
   - 卡片网格自适应（1列/2列/3列/4列）

2. **构建工具引入**
   - 引入 Vite 作为前端构建工具
   - CSS/JS 打包、压缩、Source Map
   - 开发服务器热更新
   - 生产构建优化

3. **状态管理**
   - 引入轻量级状态管理（Zustand 或自制 Pub/Sub）
   - 统一管理：用户信息、主题、通知、当前页面状态
   - 替代现有全局变量和 DOM 数据存储

4. **Verification**
   - Lighthouse 评分 > 80
   - 移动端基本可用

---

## Verification Gates

### Wave 1 Gate
- [ ] `grep -r "innerHTML" frontend/ admin-pro/` 无外部数据注入
- [ ] 渗透测试：尝试 `<script>alert(1)</script>` 不执行

### Wave 2 Gate
- [ ] 所有页面色彩统一，无视觉回归
- [ ] 图标全部使用 Lucide

### Wave 3 Gate
- [ ] 至少3个页面使用新组件
- [ ] 组件无 `innerHTML` 使用

### Wave 4 Gate
- [ ] 管理后台所有功能正常
- [ ] admin_app.py < 500 行

### Wave 5 Gate
- [ ] Lighthouse Performance > 80
- [ ] Lighthouse Accessibility > 80

---

## Risk & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| 重构引入回归bug | High | 逐个路由迁移，每步测试；保留旧代码回退 |
| Web Components 浏览器兼容 | Medium | 使用 Custom Elements v1（现代浏览器全支持） |
| Vite 引入破坏现有流程 | Medium | 保留现有直接文件服务模式作为fallback |
| 时间超出预期 | Medium | Wave 1优先完成（安全红线），其余可分期 |

---

## Files to Modify

```
frontend/js/app-core.js
frontend/js/common.js
frontend/js/components/            [NEW]
frontend/css/design-system.css     [NEW]
admin-pro/frontend/               [refactor all]
backend/admin_app.py              [refactor → split]
backend/admin/                    [NEW directory]
```

---

*Plan created: 2026-05-01*
*Based on: 02-UI-SPEC.md*
