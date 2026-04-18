# 公告状态标签与AI聊天面板实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为公告页面添加状态工作流标签（草稿→待审核→已发布→归档）和右侧AI聊天面板

**Architecture:**
- 数据库层：announcements表新增status/status_changed_at/status_changed_by字段
- 后端API层：新增状态更新API `/api/announcements/{id}/status`
- 前端：修改页面布局为左右分栏，公告卡片显示状态标签，右侧固定AI聊天面板

**Tech Stack:** Python/SQLite后端, 原生JavaScript/Tailwind CSS前端

---

## 文件结构

- Modify: `backend/database/reits.db` - 添加status字段
- Modify: `backend/api_adapter.py` - 添加状态更新API端点
- Modify: `backend/services/announcements.py` - get_cached_announcements返回status字段
- Modify: `admin-pro/frontend/announcements.html` - 重构页面布局、状态标签、AI聊天面板

---

## Task 1: 数据库迁移 - 添加status字段

**Files:**
- Modify: `backend/database/reits.db`

- [ ] **Step 1: 执行SQL添加字段**

```bash
cd D:/tools/消费看板5（前端）/backend
python -c "
import sqlite3
conn = sqlite3.connect('database/reits.db')
cursor = conn.cursor()

# 添加status字段
cursor.execute(\"ALTER TABLE announcements ADD COLUMN status VARCHAR(20) DEFAULT 'draft'\")
cursor.execute(\"ALTER TABLE announcements ADD COLUMN status_changed_at DATETIME\")
cursor.execute(\"ALTER TABLE announcements ADD COLUMN status_changed_by VARCHAR(100)\")

# 更新现有公告为published（因为它们是从官方源抓取的）
cursor.execute(\"UPDATE announcements SET status = 'published', status_changed_at = datetime('now')\")

conn.commit()
print('数据库迁移完成')
conn.close()
"
```

Run: 直接运行上面的Python命令
Expected: 输出 "数据库迁移完成"

- [ ] **Step 2: 验证字段添加成功**

```bash
python -c "
import sqlite3
conn = sqlite3.connect('database/reits.db')
cursor = conn.cursor()
cursor.execute('PRAGMA table_info(announcements)')
for col in cursor.fetchall():
    if 'status' in col[1]:
        print(f'字段: {col[1]} ({col[2]})')
conn.close()
"
```

Expected: 显示 status, status_changed_at, status_changed_by 三个字段

- [ ] **Step 3: 提交数据库迁移**

```bash
git add backend/database/reits.db
git commit -m "feat: add status fields to announcements table"
```

---

## Task 2: 后端API - 状态更新接口

**Files:**
- Modify: `backend/api_adapter.py`

- [ ] **Step 1: 添加状态更新API端点**

在 api_adapter.py 末尾添加（约第890行之后）:

```python
@adapter_app.put("/api/announcements/{announcement_id}/status")
async def update_announcement_status(
    announcement_id: int,
    status: str = Body(..., description="状态: draft/pending/published/archived"),
    changed_by: str = Body("system", description="操作人")
):
    """更新公告状态"""
    valid_statuses = ['draft', 'pending', 'published', 'archived']
    if status not in valid_statuses:
        return {
            "success": False,
            "message": f"无效状态。可选: {valid_statuses}"
        }

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 验证状态流转规则
        cursor.execute("SELECT status FROM announcements WHERE id = ?", (announcement_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"success": False, "message": "公告不存在"}

        current_status = row[0]

        # 状态流转验证
        valid_transitions = {
            'draft': ['pending'],
            'pending': ['published', 'draft'],
            'published': ['archived'],
            'archived': ['published']
        }

        if status not in valid_transitions.get(current_status, []):
            conn.close()
            return {
                "success": False,
                "message": f"不允许的状态流转: {current_status} → {status}"
            }

        # 更新状态
        cursor.execute("""
            UPDATE announcements
            SET status = ?, status_changed_at = datetime('now'), status_changed_by = ?
            WHERE id = ?
        """, (status, changed_by, announcement_id))

        conn.commit()
        conn.close()

        return {
            "success": True,
            "message": f"状态已更新: {current_status} → {status}"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"更新失败: {str(e)}"
        }
```

- [ ] **Step 2: 重启后端验证API**

```bash
powershell -Command "Get-Process Python | Stop-Process -Force"; sleep 2
cd D:/tools/消费看板5（前端）/backend && python -m uvicorn api_adapter:adapter_app --host 0.0.0.0 --port 5074 &
sleep 5
curl -s -X PUT "http://localhost:5074/api/announcements/1/status" -H "Content-Type: application/json" -d '{"status":"archived","changed_by":"test"}'
```

Expected: `{"success":true,"message":"状态已更新: published → archived"}`

- [ ] **Step 3: 提交后端修改**

```bash
git add backend/api_adapter.py
git commit -m "feat: add announcement status update API endpoint"
```

---

## Task 3: 后端 - 公告列表返回status字段

**Files:**
- Modify: `backend/services/announcements.py`

- [ ] **Step 1: 修改get_cached_announcements的SQL查询**

在 get_cached_announcements 函数中，SQL查询添加 status 和 status_changed_at 字段:

```python
cursor.execute("""
    SELECT a.id, a.fund_code, a.fund_name, a.title, a.category, a.publish_date,
           a.source_url, a.pdf_url, a.exchange, a.confidence, a.source, a.created_at,
           a.manager, a.publisher,
           f.ipo_date, f.total_shares,
           (SELECT open_price FROM fund_prices WHERE fund_code = a.fund_code ORDER BY trade_date ASC LIMIT 1) as first_open_price,
           (SELECT close_price FROM fund_prices WHERE fund_code = a.fund_code ORDER BY trade_date DESC LIMIT 1) as latest_price,
           a.status, a.status_changed_at
    FROM announcements a
    LEFT JOIN funds f ON a.fund_code = f.fund_code
    ORDER BY a.publish_date DESC
    LIMIT ?
""", (limit,))
```

- [ ] **Step 2: 修改返回值，添加status字段**

在构建返回字典的部分添加:

```python
'status': row[18] or 'draft',
'status_changed_at': row[19] or '',
```

- [ ] **Step 3: 同样修改 get_announcements_by_fund 和 get_announcements_by_category**

这两个函数也需要添加相同的字段。

- [ ] **Step 4: 重启并验证**

```bash
powershell -Command "Get-Process Python | Stop-Process -Force"; sleep 2
cd D:/tools/消费看板5（前端）/backend && python -m uvicorn api_adapter:adapter_app --host 0.0.0.0 --port 5074 &
sleep 5
curl -s "http://localhost:5074/api/announcements?limit=1" | python -c "import sys,json; d=json.load(sys.stdin); print('status' in d['data'][0] if d.get('data') else 'no data')"
```

Expected: `True`

- [ ] **Step 5: 提交**

```bash
git add backend/services/announcements.py
git commit -m "feat: return status fields in announcement queries"
```

---

## Task 4: 前端 - 页面布局重构（左右分栏）

**Files:**
- Modify: `admin-pro/frontend/announcements.html`

- [ ] **Step 1: 找到页面容器开始标签**

约第270行，找到 `<div class="min-h-screen bg-gray-50">` 或类似容器

- [ ] **Step 2: 修改为Flex左右分栏布局**

将整个页面容器修改为:

```html
<div class="flex h-screen bg-gray-50">
    <!-- 左侧公告列表 -->
    <div class="flex-1 overflow-y-auto" id="announcement-list">
        <!-- 现有所有内容移动到这里 -->
    </div>

    <!-- 右侧AI聊天面板 -->
    <div class="w-[350px] border-l bg-white shadow-lg flex flex-col" id="chat-panel">
        <div class="p-4 border-b bg-gray-50">
            <h2 class="font-bold text-gray-800">AI 公告讨论</h2>
            <p class="text-xs text-gray-500 mt-1" id="current-announcement-title">点击公告开始讨论</p>
        </div>
        <div class="flex-1 overflow-y-auto p-4 space-y-3" id="chat-messages">
            <div class="text-center text-gray-400 text-sm py-8">
                选择一条公告，然后在这里与AI讨论其内容
            </div>
        </div>
        <div class="border-t p-3 flex gap-2">
            <input type="text" id="chat-input" placeholder="输入问题..." class="flex-1 border rounded-lg px-3 py-2 text-sm">
            <button onclick="sendChatMessage()" class="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">发送</button>
        </div>
    </div>
</div>
```

- [ ] **Step 3: 提交**

```bash
git add admin-pro/frontend/announcements.html
git commit -m "feat: restructure page layout with chat panel"
```

---

## Task 5: 前端 - 状态标签显示

**Files:**
- Modify: `admin-pro/frontend/announcements.html`

- [ ] **Step 1: 添加状态配置和映射函数**

在JavaScript部分（约第50行）添加:

```javascript
// 状态配置
const STATUS_CONFIG = {
    'draft': { label: '草稿', class: 'bg-gray-100 text-gray-600' },
    'pending': { label: '待审核', class: 'bg-yellow-100 text-yellow-700' },
    'published': { label: '已发布', class: 'bg-green-100 text-green-700' },
    'archived': { label: '归档', class: 'bg-blue-100 text-blue-700' }
};
```

- [ ] **Step 2: 修改公告卡片，添加状态标签到标题右侧**

在标题行（约第607行）修改:

```html
<h3 class="text-base font-bold text-gray-900 mb-2 ${!item.isRead ? 'text-blue-900' : ''} ${mainLink ? 'cursor-pointer hover:text-blue-600' : ''}"
    ${mainLink ? `onclick="selectAnnouncement(${item.id}, '${item.title.replace(/'/g, "\\'")}')"` : ''}>
    ${item.title}
</h3>
${item.status ? `<span class="ml-2 px-2 py-0.5 text-xs font-medium rounded-full ${STATUS_CONFIG[item.status]?.class || 'bg-gray-100 text-gray-600'}">${STATUS_CONFIG[item.status]?.label || item.status}</span>` : ''}
```

- [ ] **Step 3: 添加点击选中样式**

在card的div上添加选中状态:

```html
<div class="card card-hover p-4 md:p-5 ${selectedAnnouncementId === item.id ? 'ring-2 ring-blue-500 bg-blue-50' : ''} ..."
```

- [ ] **Step 4: 添加选中状态变量和函数**

```javascript
let selectedAnnouncementId = null;
let selectedAnnouncementTitle = '';

function selectAnnouncement(id, title) {
    selectedAnnouncementId = id;
    selectedAnnouncementTitle = title;
    document.getElementById('current-announcement-title').textContent = '当前公告: ' + title;
    // 刷新列表以更新选中样式
    renderAnnouncements();
}
```

- [ ] **Step 5: 验证**

刷新页面，确认状态标签显示正确

- [ ] **Step 6: 提交**

```bash
git add admin-pro/frontend/announcements.html
git commit -m "feat: add status tags to announcement cards"
```

---

## Task 6: 前端 - 状态操作栏

**Files:**
- Modify: `admin-pro/frontend/announcements.html`

- [ ] **Step 1: 在公告卡片底部添加状态操作栏**

在日期显示下方（约第627行）添加:

```html
<div class="flex items-center justify-between mt-2 pt-2 border-t">
    <div class="flex items-center gap-2">
        ${item.status_changed_at ? `<span class="text-xs text-gray-400">状态变更: ${item.status_changed_at}</span>` : ''}
    </div>
    ${getStatusActions(item.status, item.id)}
</div>
```

- [ ] **Step 2: 添加 getStatusActions 函数**

```javascript
function getStatusActions(status, id) {
    const actions = {
        'draft': [
            { label: '提交审核', class: 'bg-yellow-50 text-yellow-700 hover:bg-yellow-100', nextStatus: 'pending' },
            { label: '删除', class: 'bg-red-50 text-red-600 hover:bg-red-100', nextStatus: 'deleted' }
        ],
        'pending': [
            { label: '通过', class: 'bg-green-50 text-green-700 hover:bg-green-100', nextStatus: 'published' },
            { label: '驳回', class: 'bg-gray-50 text-gray-700 hover:bg-gray-100', nextStatus: 'draft' }
        ],
        'published': [
            { label: '归档', class: 'bg-blue-50 text-blue-700 hover:bg-blue-100', nextStatus: 'archived' }
        ],
        'archived': [
            { label: '恢复', class: 'bg-green-50 text-green-700 hover:bg-green-100', nextStatus: 'published' }
        ]
    };

    const btns = actions[status] || [];
    return btns.map(btn =>
        `<button onclick="updateStatus(${id}, '${btn.nextStatus}')" class="px-2 py-1 text-xs rounded-lg ${btn.class}">${btn.label}</button>`
    ).join('');
}
```

- [ ] **Step 3: 添加 updateStatus 函数**

```javascript
async function updateStatus(id, newStatus) {
    try {
        const response = await fetch(`/api/announcements/${id}/status`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: newStatus, changed_by: 'user' })
        });
        const result = await response.json();
        if (result.success) {
            showToast('状态已更新', 'success');
            await loadAnnouncements();
        } else {
            showToast(result.message || '更新失败', 'error');
        }
    } catch (error) {
        showToast('更新失败: ' + error.message, 'error');
    }
}
```

- [ ] **Step 4: 验证**

刷新页面，点击状态按钮，验证状态流转正确

- [ ] **Step 5: 提交**

```bash
git add admin-pro/frontend/announcements.html
git commit -m "feat: add status action buttons"
```

---

## Task 7: 前端 - AI聊天面板基础功能

**Files:**
- Modify: `admin-pro/frontend/announcements.html`

- [ ] **Step 1: 添加聊天相关变量**

```javascript
let chatMessages = [];
let isAiTyping = false;
```

- [ ] **Step 2: 修改 selectAnnouncement 函数，初始化聊天**

```javascript
function selectAnnouncement(id, title) {
    selectedAnnouncementId = id;
    selectedAnnouncementTitle = title;
    document.getElementById('current-announcement-title').textContent = '当前公告: ' + title;

    // 清空聊天记录
    chatMessages = [];
    renderChatMessages();

    // 如果有该公告的摘要，添加为第一条AI消息
    const announcement = allAnnouncements.find(a => a.id === id);
    if (announcement && announcement.summary) {
        addChatMessage('assistant', `我正在查看公告: "${title}"。\n\n摘要: ${announcement.summary}\n\n有什么想讨论的吗?`);
    }

    renderAnnouncements();
}
```

- [ ] **Step 3: 添加聊天渲染函数**

```javascript
function renderChatMessages() {
    const container = document.getElementById('chat-messages');
    if (!container) return;

    if (chatMessages.length === 0) {
        container.innerHTML = '<div class="text-center text-gray-400 text-sm py-8">选择一条公告，然后在这里与AI讨论其内容</div>';
        return;
    }

    container.innerHTML = chatMessages.map(msg => `
        <div class="${msg.role === 'user' ? 'bg-blue-100 ml-8' : 'bg-gray-100 mr-8'} rounded-lg p-3">
            <div class="text-xs font-bold mb-1 ${msg.role === 'user' ? 'text-blue-700' : 'text-gray-700'}">${msg.role === 'user' ? '你' : 'AI'}</div>
            <div class="text-sm text-gray-800 whitespace-pre-wrap">${escapeHtml(msg.content)}</div>
        </div>
    `).join('');

    container.scrollTop = container.scrollHeight;
}

function addChatMessage(role, content) {
    chatMessages.push({ role, content });
    renderChatMessages();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
```

- [ ] **Step 4: 添加 sendChatMessage 函数**

```javascript
async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message || !selectedAnnouncementId || isAiTyping) return;

    // 添加用户消息
    addChatMessage('user', message);
    input.value = '';
    isAiTyping = true;

    // 添加AI typing指示器
    const typingId = 'typing-' + Date.now();
    const container = document.getElementById('chat-messages');
    container.innerHTML += `<div id="${typingId}" class="bg-gray-100 mr-8 rounded-lg p-3">
        <div class="text-xs font-bold text-gray-700 mb-1">AI</div>
        <div class="text-sm text-gray-500">思考中...</div>
    </div>`;
    container.scrollTop = container.scrollHeight;

    try {
        // TODO: 调用真实AI接口（这里先用模拟响应）
        await new Promise(resolve => setTimeout(resolve, 1000));

        const announcement = allAnnouncements.find(a => a.id === selectedAnnouncementId);
        const response = `关于"${selectedAnnouncementTitle}"的问题: ${message}\n\n这是一个演示响应。在实际实现中，这里会调用AI接口来回答您关于该公告的问题。`;

        document.getElementById(typingId).remove();
        addChatMessage('assistant', response);
    } catch (error) {
        document.getElementById(typingId).remove();
        addChatMessage('assistant', '抱歉，发生了错误: ' + error.message);
    }

    isAiTyping = false;
}
```

- [ ] **Step 5: 添加回车发送支持**

在 input 元素上添加 `onkeypress` 事件:

```html
<input type="text" id="chat-input" onkeypress="if(event.key==='Enter') sendChatMessage()" ...>
```

- [ ] **Step 6: 验证**

1. 刷新页面
2. 点击一条公告
3. 在右侧聊天面板输入消息
4. 确认消息显示正确

- [ ] **Step 7: 提交**

```bash
git add admin-pro/frontend/announcements.html
git commit -m "feat: add AI chat panel basic functionality"
```

---

## Task 8: 完整测试与验证

- [ ] **Step 1: 测试状态流转**

1. 创建新公告（draft状态）→ 点击提交审核 → pending状态
2. pending → 点击通过 → published状态
3. published → 点击归档 → archived状态
4. archived → 点击恢复 → published状态

- [ ] **Step 2: 测试聊天功能**

1. 点击不同公告，确认聊天面板标题更新
2. 发送消息，确认显示正确

- [ ] **Step 3: 验证所有状态标签颜色**

确认4种状态标签显示不同颜色

- [ ] **Step 4: 提交最终代码**

```bash
git add -A
git commit -m "feat: complete announcement status workflow and AI chat panel"
```

---

## 实施检查清单

- [ ] 数据库迁移完成
- [ ] 状态更新API可用
- [ ] 公告列表返回status字段
- [ ] 页面左右分栏布局
- [ ] 状态标签显示正确
- [ ] 状态操作按钮可用
- [ ] AI聊天面板基本功能
- [ ] 完整状态流转测试通过
