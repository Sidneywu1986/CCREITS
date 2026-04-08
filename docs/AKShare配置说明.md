# AKShare 配置说明

## 当前状态

✅ **AKShare 已配置完成**

## 文件清单

| 文件 | 路径 | 说明 |
|------|------|------|
| `akshare_crawler_v2.py` | `backend/crawlers/` | Python爬虫V2（支持81只基金） |
| `akshare.js` | `backend/crawlers/` | Node.js包装器 |
| `.env` | `backend/` | 环境变量（已启用AKShare） |

## 配置详情

### 1. 环境变量 (.env)
```bash
USE_AKSHARE=true    # 已启用
USE_SINA=true       # 新浪财经作为备用
```

### 2. 依赖安装
```bash
pip install akshare pandas
```

已安装版本：AKShare 1.18.51

### 3. 功能特性

V2版本优化：
- ✅ 从本地数据库读取81只基金列表
- ✅ 支持获取实时行情
- ✅ 支持获取历史日线数据（365天）
- ✅ 自动保存到SQLite数据库
- ✅ 支持单只或全部基金查询

## 使用方法

### 命令行调用

```bash
cd backend/crawlers

# 获取81只基金列表（从数据库）
python akshare_crawler_v2.py list

# 获取实时行情（全部81只）
python akshare_crawler_v2.py spot

# 获取单只基金实时行情
python akshare_crawler_v2.py spot --code 180101

# 获取历史数据（全部81只，365天）
python akshare_crawler_v2.py history

# 获取单只基金历史数据
python akshare_crawler_v2.py history --code 180101 --days 365
```

### Node.js调用

```bash
cd backend

# 获取实时行情并保存到数据库
node crawlers/akshare.js spot

# 获取历史数据并保存到数据库
node crawlers/akshare.js history

# 获取单只基金历史数据
node crawlers/akshare.js history 180101
```

### NPM命令

```bash
cd backend

# 实时行情
npm run crawl:akshare:spot

# 历史数据
npm run crawl:akshare:all
```

## 定时任务

服务启动后会自动运行：
- **实时行情**: 每5分钟（交易时间 9:00-15:00）
- **历史数据**: 每日凌晨 2:00

## 数据源优先级

当前配置：
1. **主数据源**: AKShare（东方财富）
2. **备用数据源**: 新浪财经

如果AKShare获取失败，自动降级到新浪财经。

## 测试脚本

运行测试：
```bash
D:\tools\rixian\test_akshare.bat
```

## 注意事项

1. **网络要求**: AKShare需要连接东方财富服务器
2. **基金代码**: 自动从数据库读取81只基金
3. **数据保存**: 行情数据自动保存到数据库
4. **错误处理**: 单只基金失败不影响其他基金
