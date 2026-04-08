# 前端API接入指南

## 现状

当前前端使用 `common.js` 中的 `ALL_FUNDS` 静态数据（Mock数据）。

## 切换到后端API

### 1. 引入API模块

在 `fund-detail.html` 等页面中添加：

```html
<script src="./js/api.js"></script>
```

### 2. 修改数据获取逻辑

**原代码（Mock）：**
```javascript
const fund = ALL_FUNDS.find(f => f.code === code);
```

**新代码（API）：**
```javascript
const { data: fund } = await REITS_API.getFundDetail(code);
```

### 3. 修改公告页面

**原代码：**
```javascript
allAnnouncements = generateAnnouncements(); // 模拟数据
```

**新代码：**
```javascript
const { data: announcements, stats } = await REITS_API.getAnnouncements({
    category: currentCategory,
    days: currentTimeDays,
    limit: 100
});
allAnnouncements = announcements;
```

### 4. 降级策略

`api.js` 已内置降级逻辑：
- API请求失败时自动返回 `ALL_FUNDS` 模拟数据
- 设置 `USE_MOCK = true` 可强制使用Mock（开发调试）

## 完整示例：详情页改造

```javascript
// 加载基金数据
async function loadFundData(code) {
    try {
        // 尝试从API获取
        const { data: fund } = await REITS_API.getFundDetail(code);
        
        if (!fund) {
            // 降级到Mock
            fund = ALL_FUNDS.find(f => f.code === code);
        }
        
        renderFundInfo(fund);
        
        // 加载K线
        const { data: kline } = await REITS_API.getKline(code, '1d', 100);
        renderKlineChart(kline);
        
    } catch (error) {
        console.error('加载失败:', error);
        // 完全降级到Mock
        const fund = ALL_FUNDS.find(f => f.code === code);
        renderFundInfo(fund);
        renderMockKline();
    }
}
```

## 启动后端服务

```bash
cd ../backend
npm install
npm start
```

后端运行在 http://localhost:3001

## 验证API连通性

浏览器访问：
- http://localhost:3001/api/health
- http://localhost:3001/api/funds

## 生产环境配置

修改 `api.js` 中的 `API_BASE_URL`：

```javascript
const API_BASE_URL = 'https://your-domain.com/api'; // 生产地址
```

## 信源展示

在页面底部添加数据来源标识：

```javascript
async function showDataSource() {
    const { data: status } = await REITS_API.getSystemStatus();
    
    const sourceHtml = status.sources.map(s => `
        <span class="text-xs text-gray-400">
            ${s.data_type}: ${s.source_name} 
            (${new Date(s.last_updated).toLocaleTimeString()})
        </span>
    `).join(' | ');
    
    document.getElementById('data-source-bar').innerHTML = sourceHtml;
}
```

## 后续优化建议

1. **数据缓存**：API结果缓存5分钟，减少请求
2. **增量更新**：只拉取更新的数据，减少流量
3. **WebSocket**：实时推送行情变化（高频交易场景）

## 注意事项

1. 新浪财经API有频率限制，不要在前端直接请求
2. 所有爬虫逻辑都在后端，前端只调封装好的API
3. 数据库文件 `reits.db` 需要定期备份
