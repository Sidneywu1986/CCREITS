# AKShare REITs 数据服务部署指南

## 概述

本服务使用 AKShare Python库提供REITs专用数据接口，包括：
- **实时行情**: 全市场79只REITs的实时价格、涨跌幅、市值等
- **基础信息**: 资产类型、上市日期、基金管理人等
- **公告爬虫**: 巨潮资讯网监管公告（季报、年报、问询函）

## 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

## 启动服务

### 方式1: 直接启动

```bash
# 在终端1启动AKShare服务
cd backend
python akshare_reits_server.py

# 在终端2测试服务
curl http://127.0.0.1:5000/health
```

### 方式2: 使用npm脚本

```bash
# 启动AKShare服务
cd backend
npm run akshare:start

# 测试连接
npm run akshare:test
```

### 方式3: Windows双击启动

双击 `start_akshare_server.bat` 文件

## 可用接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/reits/realtime` | GET | 全部REITs实时行情 |
| `/reits/realtime/<code>` | GET | 单只REITs行情 |
| `/reits/info` | GET | REITs基础信息 |
| `/reits/announcements/<code>` | GET | 公告列表 |
| `/reits/batch/announcements` | POST | 批量公告查询 |

## 测试接口

```bash
# 获取全部实时行情
curl http://127.0.0.1:5000/reits/realtime

# 获取单只基金
curl http://127.0.0.1:5000/reits/realtime/180601

# 获取公告列表
curl "http://127.0.0.1:5000/reits/announcements/508000?category=regular_report"

# 批量查询公告
curl -X POST http://127.0.0.1:5000/reits/batch/announcements \
  -H "Content-Type: application/json" \
  -d '{"codes":["508000","180101"],"category":"inquiry"}'
```

## 与Node.js后端集成

启动Node.js服务器时会自动检测AKShare服务：

```bash
# 1. 先启动AKShare服务
cd backend
python akshare_reits_server.py

# 2. 再启动Node.js服务器（另一个终端）
npm start
```

## 数据更新

- **实时行情**: 交易时段每15秒更新
- **基础信息**: 每日更新
- **公告数据**: 根据监管披露时间T+1更新

## 故障排查

### 问题: 端口5000被占用

```bash
# 查找占用进程
lsof -i :5000
# Windows: netstat -ano | findstr :5000

# 或修改端口
# 编辑 akshare_reits_server.py 最后一行
app.run(host='0.0.0.0', port=5001)  # 改为其他端口
```

### 问题: AKShare版本过旧

```bash
pip install akshare --upgrade
```

### 问题: 获取数据为空

检查网络连接，AKShare需要从东方财富获取数据：
```python
import akshare as ak
df = ak.reits_realtime_em()
print(len(df))  # 应返回79
```
