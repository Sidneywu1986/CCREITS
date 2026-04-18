# 公告状态标签与AI聊天面板设计

## 概述

为REITs公告页面添加两个功能：
1. 公告状态标签（草稿→待审核→已发布→归档完整工作流）
2. 右侧AI聊天面板（可针对特定公告与AI讨论）

## 布局结构

```
┌─────────────────────────────────────┬──────────────┐
│  公告列表                            │  AI聊天面板   │
│  ┌─────────────────────────────┐   │              │
│  │ 分类标签 标题 [状态标签]   │   │  当前公告:   │
│  │ 摘要                         │   │  xxx公告    │
│  │ 发行人/管理人/市值...      │   │              │
│  │ ...                         │   │  [聊天记录]  │
│  │ [状态操作栏]               │   │              │
│  └─────────────────────────────┘   │  [输入框]    │
│                                     │              │
└─────────────────────────────────────┴──────────────┘
```

## 1. 公告状态标签

### 状态定义

| 状态 | 说明 | 标签颜色 |
|------|------|----------|
| draft | 草稿 | `bg-gray-100 text-gray-600` |
| pending | 待审核 | `bg-yellow-100 text-yellow-700` |
| published | 已发布 | `bg-green-100 text-green-700` |
| archived | 归档 | `bg-blue-100 text-blue-700` |

### 位置
- 标题右侧，紧跟标题
- 多个状态标签可并排显示（如 `draft` + `pending`）

### 状态操作栏
- 卡片底部显示状态时间和操作按钮
- 操作按钮根据当前状态显示：
  - `draft` → [提交审核] [删除]
  - `pending` → [通过] [驳回]
  - `published` → [归档]
  - `archived` → [恢复发布]

## 2. AI聊天面板

### 位置与尺寸
- 固定在页面右侧
- 宽度：350px
- 高度：与公告列表等高
- 样式：白色背景，左侧灰色边框，阴影

### 功能
- 选择公告后，顶部显示"当前公告: xxx"
- 中间显示聊天记录区域
- 底部输入框 + 发送按钮

### 数据流
1. 用户点击公告 → 公告高亮 → 聊天面板显示该公告标题
2. 用户发送消息 → 调用AI接口 → 流式返回聊天内容
3. 聊天记录保存在前端会话中

## 3. 数据模型

### announcements 表新增字段
```sql
ALTER TABLE announcements ADD COLUMN status VARCHAR(20) DEFAULT 'draft';
ALTER TABLE announcements ADD COLUMN status_changed_at DATETIME;
ALTER TABLE announcements ADD COLUMN status_changed_by VARCHAR(100);
```

### API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/announcements` | GET | 获取公告列表（包含status字段） |
| `/api/announcements/{id}/status` | PUT | 更新公告状态 |
| `/api/announcements/chat` | POST | AI聊天接口 |

## 4. 前端实现

### 文件修改
- `admin-pro/frontend/announcements.html`
  - 新增右侧AI聊天面板HTML结构
  - 修改公告卡片模板，添加状态标签和操作栏
  - 新增聊天相关JavaScript函数

### 组件结构
```html
<!-- 页面布局 -->
<div class="flex h-screen">
  <!-- 左侧公告列表 -->
  <div class="flex-1 overflow-y-auto">
    <!-- 公告卡片 -->
  </div>

  <!-- 右侧AI聊天面板 -->
  <div class="w-[350px] border-l bg-white shadow-lg">
    <!-- 聊天面板内容 -->
  </div>
</div>
```

## 5. 状态流转规则

```
draft → pending（提交审核）
pending → published（通过审核）
pending → draft（驳回）
published → archived（归档）
archived → published（恢复发布）
```

## 6. 样式细节

### 状态标签样式
```css
.status-tag {
  @apply px-2 py-0.5 text-xs font-medium rounded-full;
}
.status-draft { @apply bg-gray-100 text-gray-600; }
.status-pending { @apply bg-yellow-100 text-yellow-700; }
.status-published { @apply bg-green-100 text-green-700; }
.status-archived { @apply bg-blue-100 text-blue-700; }
```

### 聊天面板样式
```css
.chat-panel {
  @apply flex flex-col h-full border-l bg-white;
}
.chat-messages {
  @apply flex-1 overflow-y-auto p-4 space-y-3;
}
.chat-input {
  @apply border-t p-3 flex gap-2;
}
```

## 实施步骤

1. 数据库迁移：添加status字段
2. 后端API：更新公告状态接口
3. 前端：修改页面布局，添加聊天面板
4. 前端：实现状态标签显示和操作
5. 前端：实现AI聊天功能
6. 测试：完整工作流测试
