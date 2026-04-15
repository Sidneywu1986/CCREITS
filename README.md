# REITs 数据平台 - 消费者版

一款面向个人投资者的REITs（房地产投资信托基金）数据分析平台，提供实时行情、基金档案、公告追踪、多维对比等功能。

## ✨ 功能特性

### 核心功能
- 📊 **实时行情** - 81只REITs实时数据，支持板块热力图展示
- 📋 **基金档案** - 完整的招募说明书数据，包含债务率、剩余期限等关键指标
- 📢 **公告追踪** - 自动抓取巨潮资讯网公告，AI分类（运营/分红/问询/财务）
- ⚖️ **基金对比** - 支持多维度对比，雷达图可视化分析
- 🔍 **智能搜索** - 支持代码、名称模糊搜索


功能	建议
分红日历	展示各REITs除息日、登记日、派息日
估值工具	基于P/FFO、现金分派率等指标的估值分位
自选股	前端LocalStorage存储用户自选列表
板块对比	支持板块间的收益率、分红率对比
导出功能	对比结果支持导出PDF/Excel

收益率计算器：输入买入价、持有份额，计算实际收益率

换手率监控：异常换手率提醒

折溢价分析：对比净值与交易价格的偏离度

业绩归因：分解收益来源（租金增长、资本化率变化等）

### 数据血缘
| 数据类型 | 数据来源 | 时效性 |
|----------|----------|--------|
| 实时行情 | 东方财富(AKShare) | 实时（1分钟） |
| 基金档案 | 招募说明书/交易所披露 | T+1 |
| 公告数据 | 巨潮资讯网(cninfo.com.cn) | T+1（收盘后15:30更新） |
| 历史行情 | AKShare | 日级 |




```

## 📁 项目结构

```
reits-platform/
├── backend/                  # 后端服务
│   ├── app/
│   │   ├── api/             # API路由
│   │   ├── core/            # 核心配置
│   │   ├── models/          # 数据模型
│   │   └── services/        # 业务服务
│   │       ├── fund_database.py      # 基金档案数据库（79只完整数据）
│   │       ├── akshare_service.py    # AKShare数据源
│   │       └── cninfo_spider.py      # 巨潮资讯爬虫
│   ├── logs/                # 日志目录
│   ├── data/                # 数据目录
│   ├── main.py              # FastAPI主入口
│   └── requirements.txt     # Python依赖
├── frontend/                # 前端页面
│   ├── market.html          # 市场概览
│   ├── detail.html          # 基金详情
│   └── compare.html         # 基金对比
├── docker/                  # Docker配置
│   ├── Dockerfile.backend   # 后端镜像
│   ├── Dockerfile.nginx     # 前端镜像
│   ├── docker-compose.yml   # 开发环境
│   ├── docker-compose.prod.yml  # 生产环境
│   └── nginx.conf           # Nginx配置
├── scripts/                 # 部署脚本
│   ├── start.sh             # 启动脚本
│   ├── stop.sh              # 停止脚本
│   └── deploy.sh            # 部署脚本
├── .env.example             # 环境变量示例
└── README.md                # 项目文档

增加目录
ackend/app/
├── tasks/           # 定时任务（Celery/APScheduler）
│   ├── data_fetch.py   # 数据抓取任务
│   └── announcement.py # 公告同步任务
├── cache/           # 缓存策略
│   └── redis_client.py
└── utils/           # 工具函数
    ├── rate_limiter.py # 限流器
    └── notify.py       # 告警通知
```

## ⚙️ 配置说明

### 环境变量 (.env)

```bash
# 基础配置
DEBUG=false                    # 调试模式
HOST=0.0.0.0                  # 监听地址
PORT=8000                     # 服务端口
WORKERS=4                     # 工作进程数

# CORS配置（生产环境必须配置具体域名）
CORS_ORIGINS=https://your-domain.com

# 日志配置
LOG_LEVEL=INFO                # 日志级别
LOG_FILE=logs/app.log         # 日志文件路径

# 数据源配置
AKSHARE_TIMEOUT=30            # AKShare超时时间
CNINFO_TIMEOUT=10             # 巨潮资讯超时时间
CNINFO_RETRY_TIMES=3          # 重试次数
Tushare Pro	历史行情补充	部分免费
新浪财经API	实时行情备选	免费
腾讯财经API	实时行情备选	免费
```

## 🔌 API 接口

### 市场行情
- `GET /api/market/realtime` - 实时行情
- `GET /api/market/sectors` - 板块列表
- `GET /api/market/funds` - 基金列表（分页）
- `GET /api/market/hot` - 热门基金
- `GET /api/market/ranking` - 排行榜

### 基金详情
- `GET /api/fund/{code}/detail` - 基金详情
- `GET /api/fund/{code}/historical` - 历史行情
- `GET /api/fund/{code}/announcements` - 公告列表
- `GET /api/fund/{code}/compare` - 对比数据

### 系统
- `GET /api/health` - 健康检查

```

### 数据更新机制

- **实时行情**: 每分钟自动刷新（交易时间）
- **公告更新**: 每日收盘后15:30自动抓取
- **数据缓存**: 本地缓存5分钟，减少API调用

## 📊 支持的REITs

平台录入81只REITs完整档案数据，覆盖以下板块：

这14个板块具体如下：

板块名称	涵盖的主要内容
1. 交通基础设施	收费公路、铁路、机场、港口项目。
2. 能源基础设施	风电、光伏、水电、核电等清洁能源，以及储能、充电桩、符合低碳要求的煤电等项目。
3. 市政基础设施	城镇供水、供气、供热及停车场项目。
4. 生态环保基础设施	城镇污水垃圾处理、固废危废处理及大宗固废综合利用项目。
5. 仓储物流基础设施	面向社会提供存储服务的通用仓库、冷库等。
6. 园区基础设施	位于自贸区、国家级/省级开发区等区域的研发平台、工业厂房、孵化器等。
7. 新型基础设施	数据中心、人工智能、5G通信铁塔、物联网、智慧城市等项目。
8. 租赁住房	保障性租赁住房、公租房，以及专业机构自持的市场化长租公寓等。
9. 水利设施	具有供水、发电等功能的水利设施。
10. 文化旅游基础设施	5A/4A级旅游景区及自然文化遗产，可配套纳入景区内的旅游酒店。
11. 消费基础设施	百货商场、购物中心、农贸市场、社区商业、体育场馆及四星级及以上酒店等。
12. 商业办公设施	超大特大城市的超甲级、甲级商务楼宇（此为2025年新增类型）。
13. 养老设施	依法登记并在民政部门备案的养老项目。
14. 城市更新设施	老旧街区、老旧厂区更新改造项目（此为2025年新增类型）。


## 🔒 安全说明

1. **生产环境CORS**: 务必在 `.env` 中配置具体的域名，不要使用 `*`
2. **SSL证书**: 生产环境建议配置HTTPS
3. **数据隐私**: 用户收藏等个人数据存储在浏览器本地
4. **API限流**: 建议配合Nginx配置API限流

## 🐛 常见问题

### Q1: 数据加载慢？
- 检查网络连接（需要访问东方财富、巨潮资讯）
- 查看日志：`docker logs reits-backend`
- 调整 `AKSHARE_TIMEOUT` 和 `CNINFO_TIMEOUT`

### Q2: 如何更新基金数据？
- 基金档案数据在 `backend/app/services/fund_database.py` 中
- 定期更新数据后重启服务

### Q3: 支持私有化部署？
- 完全支持，所有代码开源
- 不依赖外部付费API（除可选的Tushare Pro增强功能）

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request。

## 📞 联系方式

- 项目主页: [Your URL]
- 问题反馈: [Your Issues URL]

---

**免责声明**: 本软件提供的数据仅供参考，不构成投资建议。投资有风险，入市需谨慎。
