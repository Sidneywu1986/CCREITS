# 公告多选AI聊天实施计划

**Goal:** 允许用户同时选择最多3条公告进行AI聊天讨论

**Architecture:**
- 前端状态：从单选 `selectedAnnouncementId` 改为多选数组 `selectedAnnouncementIds[]`
- 每条公告添加复选框，选中效果与现有选中状态合并
- 聊天面板顶部显示选中公告摘要列表

**Tech Stack:** 原生JavaScript/Tailwind CSS前端

---

## Task 1: 修改前端状态（单选→多选）

**Files:**
- Modify: `admin-pro/frontend/announcements.html`

- [ ] **Step 1: 替换状态变量**

将（约第278行）：
```javascript
let selectedAnnouncementId = null;
let selectedAnnouncementTitle = '';
```

改为：
```javascript
let selectedAnnouncementIds = [];  // 改为数组
let selectedAnnouncements = [];  // 存储选中公告的完整信息 {id, title, summary}
```

- [ ] **Step 2: 替换 selectAnnouncement 函数**

约第697行，改为 `toggleSelection`：

```javascript
function toggleSelection(id, title, summary) {
    const idx = selectedAnnouncementIds.indexOf(id);
    if (idx > -1) {
        // 已选中，移除
        selectedAnnouncementIds.splice(idx, 1);
        selectedAnnouncements = selectedAnnouncements.filter(a => a.id !== id);
    } else {
        // 未选中
        if (selectedAnnouncementIds.length >= 3) {
            showToast('最多选择3条公告', 'warning');
            return;
        }
        selectedAnnouncementIds.push(id);
        selectedAnnouncements.push({ id, title, summary: summary || '' });
    }
    updateSelectionUI();
    updateChatPanelHeader();
}
```

- [ ] **Step 3: 添加 updateSelectionUI 函数**

```javascript
function updateSelectionUI() {
    // 更新所有卡片的复选框状态和样式
    const checkboxes = document.querySelectorAll('.announcement-checkbox');
    checkboxes.forEach(cb => {
        const id = parseInt(cb.dataset.id);
        cb.checked = selectedAnnouncementIds.includes(id);
    });
    // 刷新列表以更新选中样式
    renderAnnouncements();
}
```

- [ ] **Step 4: 添加 updateChatPanelHeader 函数**

```javascript
function updateChatPanelHeader() {
    const header = document.getElementById('selected-announcements-header');
    const list = document.getElementById('selected-announcements-list');
    const emptyMsg = document.getElementById('selected-announcements-empty');

    if (selectedAnnouncements.length === 0) {
        header.classList.add('hidden');
        list.innerHTML = '';
        emptyMsg.classList.remove('hidden');
    } else {
        header.classList.remove('hidden');
        emptyMsg.classList.add('hidden');
        header.textContent = `已选公告 (${selectedAnnouncements.length}/3)`;
        list.innerHTML = selectedAnnouncements.map((a, i) => `
            <div class="text-xs bg-white rounded px-2 py-1 flex justify-between items-center">
                <span class="truncate flex-1">${i+1}. ${a.title}</span>
                <button onclick="removeFromSelection(${a.id})" class="ml-2 text-gray-400 hover:text-red-500 font-bold">×</button>
            </div>
        `).join('');
    }
}
```

- [ ] **Step 5: 添加 removeFromSelection 和 clearSelection 函数**

```javascript
function removeFromSelection(id) {
    selectedAnnouncementIds = selectedAnnouncementIds.filter(i => i !== id);
    selectedAnnouncements = selectedAnnouncements.filter(a => a.id !== id);
    updateSelectionUI();
    updateChatPanelHeader();
}

function clearSelection() {
    selectedAnnouncementIds = [];
    selectedAnnouncements = [];
    updateSelectionUI();
    updateChatPanelHeader();
}
```

- [ ] **Step 6: 提交**

```bash
git add admin-pro/frontend/announcements.html
git commit -m "feat: change selection to multi-select (max 3)"
```

---

## Task 2: 添加复选框到公告卡片

**Files:**
- Modify: `admin-pro/frontend/announcements.html`

- [ ] **Step 1: 修改公告卡片模板，添加复选框**

找到公告卡片的开始（约第628行），在卡片最前面添加复选框：

```html
<div class="card card-hover p-4 md:p-5 ${selectedAnnouncementIds.includes(item.id) ? 'ring-2 ring-blue-500 bg-blue-50' : ''}">
    <div class="flex items-start gap-3">
        <!-- 复选框 -->
        <input type="checkbox"
               class="announcement-checkbox mt-1 w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
               data-id="${item.id}"
               ${selectedAnnouncementIds.includes(item.id) ? 'checked' : ''}
               onclick="toggleSelection(${item.id}, '${item.title.replace(/'/g, "\\'")}', '${(item.summary || '').replace(/'/g, "\\'")}')">
        <div class="flex-1 min-w-0">
            <!-- 原有内容 -->
```

注意：需要调整原有布局，把所有内容包在一个 div 中并向右偏移。

- [ ] **Step 2: 修改卡片点击行为**

原来的点击标题行为是 `onclick="selectAnnouncement..."`，现在改为复选框控制选择，标题点击保持原有行为（查看PDF等）。

找到标题的 onclick，移除 selectAnnouncement 调用：
```html
onclick="window.open('${mainLink}', '_blank'); markAsRead(${item.id});"
```

- [ ] **Step 3: 提交**

```bash
git add admin-pro/frontend/announcements.html
git commit -m "feat: add checkbox to announcement cards"
```

---

## Task 3: 更新聊天面板头部显示选中公告

**Files:**
- Modify: `admin-pro/frontend/announcements.html`

- [ ] **Step 1: 修改聊天面板HTML结构**

找到聊天面板（id="chat-panel"），修改头部（约第214-219行）：

```html
<div class="p-4 border-b bg-gray-50">
    <h2 class="font-bold text-gray-800">AI 公告讨论</h2>
    <!-- 选中公告列表 -->
    <div id="selected-announcements-header" class="hidden mt-2 text-xs font-medium text-blue-700"></div>
    <div id="selected-announcements-list" class="mt-1 space-y-1"></div>
    <p id="selected-announcements-empty" class="text-xs text-gray-500 mt-1">点击公告复选框开始讨论</p>
</div>
```

- [ ] **Step 2: 初始化时显示空状态**

在页面加载时调用 `updateChatPanelHeader()` 确保空状态显示正确。

- [ ] **Step 3: 提交**

```bash
git add admin-pro/frontend/announcements.html
git commit -m "feat: show selected announcements in chat panel header"
```

---

## Task 4: 更新聊天AI消息携带多公告上下文

**Files:**
- Modify: `admin-pro/frontend/announcements.html`

- [ ] **Step 1: 修改 selectAnnouncement 为初始化聊天（可选，如果需要保留单选行为）**

目前的设计是复选框控制选择。如果要保留"点击标题查看公告并初始化聊天"的行为，需要修改 `selectAnnouncement` 或创建新函数 `initChatForSelected`。

建议保持简单：选中公告后自动初始化聊天，不需要单独调用。

```javascript
// 当 selectedAnnouncements 变化时，自动初始化聊天
function initChatForSelected() {
    if (selectedAnnouncements.length === 0) {
        chatMessages = [];
        renderChatMessages();
        return;
    }

    // 清空聊天记录
    chatMessages = [];
    renderChatMessages();

    // 添加AI初始化消息
    if (selectedAnnouncements.length === 1) {
        const a = selectedAnnouncements[0];
        addChatMessage('assistant', `我正在查看公告: "${a.title}"。\n\n摘要: ${a.summary}\n\n有什么想讨论的吗?`);
    } else {
        const intro = selectedAnnouncements.map((a, i) => `${i+1}. ${a.title}`).join('\n');
        const summaries = selectedAnnouncements.map((a, i) => `${i+1}. [${a.title}]\n   ${a.summary}`).join('\n');
        addChatMessage('assistant', `我正在查看以下${selectedAnnouncements.length}条公告：\n${summaries}\n\n请告诉我您想讨论什么，我可以帮您分析这些公告。`);
    }
}
```

- [ ] **Step 2: 在 toggleSelection 中调用 initChatForSelected**

在 `toggleSelection` 函数末尾添加：
```javascript
initChatForSelected();
```

- [ ] **Step 3: 提交**

```bash
git add admin-pro/frontend/announcements.html
git commit -m "feat: init chat with multiple announcement context"
```

---

## Task 5: 测试与验证

- [ ] **Step 1: 测试复选框选择**

1. 刷新页面
2. 点击公告复选框，选中状态变化
3. 选中3条后，再选第4条应提示"最多选3条"

- [ ] **Step 2: 测试聊天面板**

1. 选中1条公告，聊天面板显示该公告摘要
2. 选中2-3条公告，聊天面板显示多条摘要
3. 取消选中，聊天面板更新

- [ ] **Step 3: 测试移除功能**

1. 点击选中公告列表中的×按钮
2. 该公告被移除，选中数量减少

- [ ] **Step 4: 测试清空功能**

1. 点击"清空"按钮
2. 所有选中被取消

- [ ] **Step 5: 提交最终代码**

```bash
git add -A
git commit -m "feat: complete multi-select announcement chat"
```

---

## 验证检查清单

- [ ] 复选框显示正常
- [ ] 最多选3条提示
- [ ] 选中样式正确（边框高亮）
- [ ] 聊天面板显示选中公告列表
- [ ] 移除单个公告功能正常
- [ ] 清空全部功能正常
- [ ] AI消息包含多公告上下文
