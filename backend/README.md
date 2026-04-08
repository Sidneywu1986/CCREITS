# REITs数据平台后端 - 阶段一

## 快速开始

### 1. 安装依赖

```bash
cd backend
npm install
```

### 2. 启动服务

```bash
# 开发模式（热更新）
npm run dev

# 生产模式
npm start
```

服务启动后访问 http://localhost:3001

### 3. 手动更新数据

```bash
# 更新行情
npm run crawl:price

# 更新公告
npm run crawl:announcement
```

## 项目结构

```
backend/
├── database/
│   ├── schema.sql      # 数据库结构
│   ├── db.js           # 数据库连接
│   └── reits.db        # SQLite数据库文件（自动创建）
├── crawlers/
│   ├── price.js        # 行情爬虫（新浪财经）
│   └── announcement.js # 公告爬虫（上交所/深交所）
├── routes/
│   ├── funds.js        # 基金API
│   ├── announcements.js# 公告API
│   └── system.js       # 系统API
├── server.js           # 主服务入口
└── package.json
```

## API接口文档

### 基金相关

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/funds | 获取所有基金列表 |
| GET | /api/funds/:code | 获取单个基金详情 |
| GET | /api/funds/:code/kline?period=1d&limit=100 | 获取K线数据 |

### 公告相关

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/announcements?category=&days=7 | 获取公告列表 |
| GET | /api/announcements/:id | 获取公告详情 |

**Query参数：**
- `category`: 分类过滤（operation/dividend/inquiry/financial）
- `fund_code`: 基金代码过滤
- `days`: 最近N天（默认7天）
- `limit`: 数量限制（默认20）
- `search`: 标题/摘要搜索

### 系统相关

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/health | 健康检查 |
| GET | /api/system/status | 系统状态和数据源健康度 |
| GET | /api/system/logs | 更新日志 |

## 数据源配置

数据源自追踪表自动初始化：

| 数据类型 | 来源 | 更新频率 |
|---------|------|---------|
| 行情数据 | 新浪财经（免费API） | 每5分钟（交易时间） |
| 公告数据 | 上交所/深交所爬虫 | 每小时 |
| 净值数据 | 东方财富（待接入） | 每日 |

## 定时任务

| 任务 | Cron表达式 | 说明 |
|------|-----------|------|
| 行情更新 | `*/5 9-15 * * 1-5` | 工作日9:00-15:00每5分钟 |
| 公告更新 | `0 * * * *` | 每小时整点 |

## 部署到服务器

### 使用 PM2（推荐）

```bash
# 全局安装PM2
npm install -g pm2

# 启动服务
pm2 start server.js --name reits-backend

# 查看状态
pm2 status

# 查看日志
pm2 logs reits-backend

# 重启
pm2 restart reits-backend

# 开机自启
pm2 startup
pm2 save
```

### 使用 Docker（可选）

```dockerfile
# Dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install --production

COPY . .

EXPOSE 3001

CMD ["node", "server.js"]
```

```bash
# 构建镜像
docker build -t reits-backend .

# 运行容器
docker run -d -p 3001:3001 -v $(pwd)/database:/app/database reits-backend
```

## 数据迁移

从 Mock 数据迁移到真实数据库：

```bash
# 1. 确保前端引用了 api.js
# 2. 数据库会自动初始化，包含81只基金基础信息
# 3. 运行爬虫填充实时数据
npm run crawl:price
npm run crawl:announcement
```

## 常见问题

### 1. 爬虫被封IP？
- 新浪API有频率限制，建议每批请求间隔500ms以上
- 如需大规模抓取，考虑使用代理池

### 2. 数据库文件过大？
- SQLite默认启用WAL模式，性能较好
- 历史价格数据可定期归档（保留最近1年）

### 3. 前端跨域问题？
- 后端已开启CORS，允许所有来源
- 生产环境建议配置具体域名

## 阶段二预告

- [ ] 用户系统（登录/注册/JWT）
- [ ] 自选基金同步
- [ ] 更完善的K线数据（分钟级）
- [ ] 财报数据接入
- [ ] 管理后台（可视化配置爬虫）
