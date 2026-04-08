# REITs数据库重置说明

## 概述

以图片中的**20只基金**为准，清空数据库中的所有其他REITs数据。

## 20只基金清单

| 代码 | 基金名称 | 板块 |
|:----:|----------|------|
| 180101 | 博时蛇口产园REIT | 产业园区 |
| 180102 | 华夏合肥高新REIT | 产业园区 |
| 180103 | 华夏和达高科REIT | 产业园区 |
| 180105 | 易方达广开产园REIT | 产业园区 |
| 180106 | 广发成都高投产业REIT | 产业园区 |
| 180201 | 平安广州广河REIT | 交通基础设施 |
| 180202 | 华夏越秀高速REIT | 交通基础设施 |
| 180203 | 招商高速公路REIT | 交通基础设施 |
| 180301 | 红土创新盐田港REIT | 仓储物流 |
| 180302 | 华夏深国际REIT | 仓储物流 |
| 180303 | 华泰宝湾物流REIT | 仓储物流 |
| 180305 | 南方顺丰物流REIT | 仓储物流 |
| 180306 | 华夏安博仓储REIT | 仓储物流 |
| 180401 | 鹏华深圳能源REIT | 能源基础设施 |
| 180402 | 工银蒙能清洁能源REIT | 能源基础设施 |
| 180501 | 红土创新深圳安居REIT | 租赁住房 |
| 180502 | 招商基金蛇口租赁REIT | 租赁住房 |
| 180601 | 华夏华润商业REIT | 消费基础设施 |
| 180602 | 中金印力消费REIT | 消费基础设施 |
| 180603 | 华夏大悦城商业REIT | 消费基础设施 |

## 重置方法

### 方法1：双击运行脚本（推荐）

```bash
# Windows
d:\tools\rixian\reset_db.bat

# Linux/Mac
cd d:\tools\rixian
./reset_db.sh
```

### 方法2：手动运行

```bash
cd d:\tools\消费看板5（前端）\backend
node reset_reits_db.js
```

### 方法3：使用SQLite工具

使用 DB Browser for SQLite 或其他工具打开数据库：
```
d:\tools\消费看板5（前端）\backend\database\reits.db
```

然后执行 SQL 文件：
```
文件 → 导入 → 从SQL文件
选择: reset_reits_db.sql
```

## 重置内容

执行后会清空以下表的所有数据：
- ✅ `funds` - 基金基础信息表
- ✅ `quotes` - 实时行情表
- ✅ `price_history` - 历史价格表
- ✅ `announcements` - 公告表

然后只插入上述20只基金的基础信息。

## 重置后操作

重置完成后，需要重新运行爬虫获取数据：

```bash
cd d:\tools\消费看板5（前端）\backend

# 获取实时行情
npm run crawl:price

# 或使用AKShare
npm run crawl:akshare:spot
```

## 验证结果

重置完成后，可以通过以下API验证：

```bash
curl http://localhost:3001/api/funds
```

应该只返回20只基金数据。

## 注意事项

⚠️ **警告**: 此操作会永久删除数据库中的所有REITs数据，无法恢复！
- 如果之前有重要的历史数据，请先备份数据库文件
- 数据库文件位置: `backend/database/reits.db`
