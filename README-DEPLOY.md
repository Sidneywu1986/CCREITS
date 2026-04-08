# REITs 数据平台 - 部署文档

## 特性

- 📊 **多数据源支持**: 新浪财经 + AKShare (东方财富)
- 📈 **历史数据**: 支持 REITs 历史日线数据下载
- 🔄 **实时行情**: 自动定时更新
- 🐍 **Python 集成**: 使用 AKShare 获取专业金融数据

## 快速开始

### Windows 开发环境

**前置要求**: Node.js 18+，Python 3.8+ (如需 AKShare)

```bash
# 1. 安装依赖并初始化数据库（会自动安装 AKShare）
install.bat

# 2. 启动服务
start.bat

# 3. 停止服务
stop.bat
```

### Linux/Mac 开发环境

**前置要求**: Node.js 18+，Python 3.8+ (如需 AKShare)

```bash
# 1. 安装依赖并初始化数据库（会自动安装 AKShare）
chmod +x install.sh start.sh stop.sh
./install.sh

# 2. 启动服务
./start.sh

# 3. 停止服务
./stop.sh
```

### 生产环境部署（Linux）

```bash
# 一键部署
chmod +x deploy.sh
sudo ./deploy.sh
```

或使用 PM2：

```bash
# 安装 PM2
npm install -g pm2

# 启动服务
pm2 start ecosystem.config.js --env production

# 保存配置
pm2 save
pm2 startup
```

### Docker 部署

```bash
# 构建镜像
docker build -t reits-platform .

# 运行容器
docker run -d -p 3001:3001 -v $(pwd)/backend/database:/app/backend/database reits-platform
```

### Nginx 反向代理

```bash
# 复制配置文件
sudo cp nginx.reits.conf /etc/nginx/sites-available/reits
sudo ln -s /etc/nginx/sites-available/reits /etc/nginx/sites-enabled/

# 测试并重载
sudo nginx -t
sudo systemctl reload nginx
```

## 目录结构

```
消费看板5（前端）/
├── backend/                  # 后端服务
│   ├── crawlers/            # 数据爬虫
│   │   ├── price.js         # 新浪财经爬虫
│   │   ├── announcement.js  # 公告爬虫
│   │   ├── akshare.js       # AKShare Node.js 包装器
│   │   └── akshare_crawler.py  # AKShare Python 脚本
│   ├── database/            # SQLite 数据库
│   ├── routes/              # API 路由
│   │   └── akshare.js       # AKShare API 路由
│   ├── server.js            # 主服务入口
│   ├── package.json
│   └── requirements.txt     # Python 依赖
├── frontend/                 # 前端静态页面
│   ├── *.html               # 页面文件
│   ├── css/                 # 样式文件
│   └── js/                  # JavaScript
├── install.bat / install.sh  # 安装脚本
├── start.bat / start.sh      # 启动脚本
├── stop.bat / stop.sh        # 停止脚本
├── deploy.sh                 # 生产部署脚本
├── ecosystem.config.js       # PM2 配置
├── nginx.reits.conf          # Nginx 配置
└── Dockerfile                # Docker 配置
```

## API 接口

### 基础接口

| 接口 | 说明 |
|------|------|
| GET /api/health | 健康检查 |
| GET /api/funds | 基金列表 |
| GET /api/funds/:code | 基金详情 |
| GET /api/funds/:code/kline | K线数据 |
| GET /api/announcements | 公告列表 |
| GET /api/system/status | 系统状态 |

### AKShare 接口

| 接口 | 说明 |
|------|------|
| GET /api/akshare/list | 获取 REITs 列表 |
| GET /api/akshare/spot | 获取实时行情 |
| GET /api/akshare/history/:code | 获取历史数据 |
| POST /api/akshare/crawl/spot | 立即爬取实时行情 |
| POST /api/akshare/crawl/history/:code | 立即爬取历史数据 |

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| PORT | 3001 | 服务端口 |
| HOST | 0.0.0.0 | 监听地址 |
| DEBUG | true | 调试模式 |
| LOG_LEVEL | info | 日志级别 |
| USE_AKSHARE | true | 启用 AKShare 数据源 |
| USE_SINA | true | 启用新浪财经数据源 |

## 数据更新

### 自动更新

- **行情数据**: 每5分钟自动更新（交易日 9:00-15:00）
- **公告数据**: 每小时自动更新
- **历史数据**: 每日凌晨 2:00 更新（AKShare）

### 手动更新

```bash
cd backend

# 新浪财经
npm run crawl:price
npm run crawl:announcement

# AKShare
npm run crawl:akshare:spot        # 实时行情
npm run crawl:akshare:history     # 单只基金历史数据
npm run crawl:akshare:all         # 所有基金历史数据
```

### Python 脚本直接调用

```bash
cd backend/crawlers

# 获取 REITs 列表
python akshare_crawler.py list

# 获取实时行情
python akshare_crawler.py spot

# 获取单只基金历史数据
python akshare_crawler.py history --code 508056 --start 20240101 --end 20241231

# 获取所有基金历史数据
python akshare_crawler.py all-history --start 20240101
```

## 注意事项

1. 公告爬虫接口可能需要更新（当前上交所接口返回404）
2. 建议在生产环境使用 Nginx 反向代理
3. 数据库文件建议定期备份
4. 推荐使用 PM2 管理 Node.js 进程
