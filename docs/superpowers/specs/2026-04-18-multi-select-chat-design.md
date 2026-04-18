# 公告多选AI聊天设计

## 概述

允许用户同时选择最多3条公告进行AI聊天讨论，支持多公告对比分析。

## 交互方式

### 选择机制
- 每条公告左侧添加复选框（Checkbox）
- 用户勾选复选框选择公告
- 最多选择3条公告（超过提示"最多选3条"）
- 取消勾选即取消选择

### 选中效果
- 复选框勾选状态
- 卡片边框高亮：`ring-2 ring-blue-500 bg-blue-50`
- 选中公告数量显示在聊天面板顶部

## 布局结构

```
┌─────────────────────────────────────┬──────────────┐
│  公告列表                            │  AI聊天面板   │
│  ☑ 公告1  [状态标签] 标题...       │  已选3条:    │
│  ☐ 公告2  [状态标签] 标题...       │  1. xxx...  │
│  ☑ 公告3  [状态标签] 标题...       │  2. xxx...  │
│  ☐ 公告4  [状态标签] 标题...       │  3. xxx...  │
│                                     │              │
│                                     │  [聊天记录]  │
│                                     │  [输入框]    │
└─────────────────────────────────────┴──────────────┘
```

## 数据模型变更

### 前端状态
```javascript
let selectedAnnouncementIds = [];  // 改为数组，最多3个
```

### 选中公告数据结构
```javascript
{
  ids: [1, 2, 3],  // 最多3个ID
  announcements: [
    { id: 1, title: '公告1标题', summary: '摘要1' },
    { id: 2, title: '公告2标题', summary: '摘要2' },
    { id: 3, title: '公告3标题', summary: '摘要3' }
  ]
}
```

## UI组件

### 1. 复选框
- 位置：公告卡片最左侧
- 样式：原生Checkbox + Tailwind
- 状态：未选中、选中（蓝色勾选）、禁用（已达3条时未选中的）

### 2. 选中公告列表（聊天面板顶部）
```html
<div class="p-3 bg-blue-50 border-b">
  <div class="flex items-center justify-between mb-2">
    <span class="text-sm font-medium">已选公告 (3/3)</span>
    <button onclick="clearSelection()" class="text-xs text-gray-500 hover:text-gray-700">清空</button>
  </div>
  <div class="space-y-1">
    ${selectedAnnouncements.map((a, i) => `
      <div class="text-xs bg-white rounded px-2 py-1 flex justify-between">
        <span class="truncate">${i+1}. ${a.title}</span>
        <button onclick="removeFromSelection(${a.id})" class="text-gray-400 hover:text-red-500">×</button>
      </div>
    `).join('')}
  </div>
</div>
```

### 3. 聊天面板AI消息
AI回复时携带多公告上下文：
```
我正在查看以下3条公告：
1. [公告标题1] - 摘要...
2. [公告标题2] - 摘要...
3. [公告标题3] - 摘要...

这三条公告都是关于xxx主题，请分析它们的异同。
```

## 功能函数

### toggleSelection(id, title, summary)
切换公告选中状态
- 如果已选中，从数组移除
- 如果未选中且少于3条，添加到数组
- 如果未选中但已达3条，提示"最多选3条"

### removeFromSelection(id)
从选中列表移除特定公告

### clearSelection()
清空所有选中

### updateSelectionUI()
更新所有卡片的复选框状态和选中样式

## 状态规则

| 条件 | 行为 |
|------|------|
| 未选中，点击复选框 | 添加到选中列表 |
| 已选中，点击复选框 | 从选中列表移除 |
| 已选3条，再选第4条 | 提示"最多选3条"，不添加 |
| 点击公告标题 | 原有的查看PDF/详情行为不变 |

## 实施步骤

1. 修改前端状态：`selectedAnnouncementId` → `selectedAnnouncementIds[]`
2. 添加复选框到公告卡片
3. 实现 `toggleSelection`, `removeFromSelection`, `clearSelection`
4. 更新聊天面板顶部显示选中公告列表
5. 修改 `selectAnnouncement` 为多选兼容
6. 测试验证

## 兼容性

- 单选功能保持不变
- 现有状态标签、操作按钮不受影响
- 聊天面板底部输入和发送功能不变
