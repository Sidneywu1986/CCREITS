# REITs数据平台 - 部署检查清单

## ✅ 系统状态（当前）

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 基金总数 | ✅ 81只 | 数据库已导入全部REITs |
| 实时行情 | ✅ 79只 | 新浪API覆盖79只活跃REITs |
| 历史数据 | ✅ 41,662条 | 2021-06-21 至 2026-04-03 |
| 公告数据 | ✅ 2条 | AKShare新闻源（可手动刷新） |

## 🚀 明日开盘前检查

### 1. 启动后端服务
```bash
cd backend
node server.js
```

### 2. 检查实时数据API
```bash
# 测试基金列表
curl http://localhost:3001/api/funds

# 测试单只基金
curl http://localhost:3001/api/funds/508000

# 测试系统状态
curl http://localhost:3001/api/system/status
```

### 3. 手动刷新实时行情
```bash
node backend/crawlers/price.js
```

### 4. 访问前端页面
```
http://localhost:3000/market.html        # 市场概况
http://localhost:3000/announcements.html # 公告追踪
```

## 📊 定时任务配置

| 任务 | 频率 | 时间 | 数据源 |
|------|------|------|--------|
| 实时行情 | 每5分钟 | 交易日 9:00-15:00 | 新浪财经 |
| 公告更新 | 每小时 | 全天 | AKShare |
| 历史数据 | 每天 | 凌晨 2:00 | AKShare |

## 🔧 故障排查

### 实时行情未更新
1. 检查新浪API: `node backend/crawlers/price.js`
2. 查看错误日志
3. 备用：使用AKShare `npm run crawl:akshare:spot`

### 数据库问题
```bash
# 检查数据库
sqlite3 backend/database/reits.db "SELECT COUNT(*) FROM funds;"
sqlite3 backend/database/reits.db "SELECT COUNT(*) FROM quotes;"
```

### 端口占用
如果3001端口被占用：
```bash
# 修改端口
set PORT=3002
node backend/server.js
```

## 📁 关键文件

| 文件 | 说明 |
|------|------|
| `backend/server.js` | 主服务入口 |
| `backend/crawlers/price.js` | 新浪实时行情爬虫 |
| `backend/crawlers/announcement_v2.js` | 公告爬虫（调用Python） |
| `backend/crawlers/announcement_akshare.py` | AKShare新闻爬虫 |
| `backend/database/reits.db` | SQLite数据库 |

## 🎯 明天开盘检查项

- [ ] 后端服务已启动
- [ ] `/api/funds` 返回79只基金
- [ ] `/api/funds/508000` 返回完整数据
- [ ] 前端页面能正常访问
- [ ] 实时行情定时任务运行中

---
最后检查时间: 2026-04-06
