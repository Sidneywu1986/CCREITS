# REITs 数据实时计算与爬虫采集方案

## 一、已实现功能

### 1. 前端实时计算（自动计算）

| 指标 | 计算公式 | 数据来源 |
|------|----------|----------|
| **溢价率** | `(市价 - 净值) / 净值 × 100%` | 实时价格 + 净值 |
| **流通市值** | `流通份额 × 当前价格 / 10000` | 流通份额 + 实时价格 |

**实现文件：**
- `frontend/js/fund-calculator.js` - 计算工具函数
- `backend/routes/funds.js` - API实时计算

### 2. 后端爬虫采集（需定时运行）

| 指标 | 数据源 | 采集方式 | 更新频率 |
|------|--------|----------|----------|
| **净值(NAV)** | 天天基金网/东方财富 | API接口 | 每日 |
| **流通份额** | 东方财富 | API接口 | 每周 |
| **债务率** | 基金季报/年报 | 公告解析 | 季度 |
| **机构持仓** | 东方财富 | API接口 | 季度 |
| **派息率** | 分红公告 | 公告解析 | 实时 |

**实现文件：**
- `backend/crawlers/fund-detail.js` - 详情爬虫

---

## 二、数据库结构更新

### 新增字段（funds表）

```sql
ALTER TABLE funds ADD COLUMN circulating_shares REAL;  -- 流通份额（万份）
ALTER TABLE funds ADD COLUMN institution_hold REAL;      -- 机构持仓比例（%）
```

### 迁移脚本

```bash
cd backend/database
node migrate-add-fields.js
```

---

## 三、API返回数据格式

### GET /api/funds

```json
{
  "success": true,
  "data": [
    {
      "code": "508056",
      "name": "中金普洛斯REIT",
      "price": 3.85,
      "nav": 3.72,
      "premium": 3.49,           // 实时计算
      "marketCap": 25.8,         // 实时计算
      "debt": 35.2,
      "institutionHold": 87.5,
      "yield": 4.85
    }
  ]
}
```

### GET /api/funds/:code

```json
{
  "success": true,
  "data": {
    "code": "508056",
    "name": "中金普洛斯REIT",
    "price": 3.85,
    "nav": 3.72,
    "circulating_shares": 67000,
    "premium": 3.49,           // 实时计算
    "marketCap": 25.8,         // 实时计算
    "debt_ratio": 35.2,
    "institution_hold": 87.5,
    "history": [...]
  }
}
```

---

## 四、运行爬虫

### 手动运行

```bash
cd backend
node -e "const Crawler = require('./crawlers/fund-detail'); new Crawler().fetchData()"
```

### 添加到定时任务（server.js）

```javascript
const FundDetailCrawler = require('./crawlers/fund-detail');

// 每日凌晨2点运行
 cron.schedule('0 2 * * *', () => {
     console.log('⏰ 启动基金详情爬虫...');
     new FundDetailCrawler().fetchData();
 });
```

---

## 五、数据来源说明

### 已接入数据源

1. **新浪财经** - 实时价格、涨跌幅、成交量
2. **东方财富** - 主力资金、机构持仓、流通份额
3. **上交所/深交所** - 公告、分红信息

### 需要补充的数据源

1. **基金净值** - 天天基金网 (fund.eastmoney.com)
2. **债务率** - 基金季报PDF解析
3. **详细分红记录** - 公告分类提取

---

## 六、前端展示逻辑

### 数据优先级

1. **实时计算字段**（优先）
   - 溢价率：使用API返回的实时计算值
   - 流通市值：使用API返回的实时计算值

2. **爬虫采集字段**（其次）
   - 净值：爬取后存入数据库
   - 债务率：季报发布后更新
   - 机构持仓：季报发布后更新
   - 派息率：基于分红公告计算

3. **兜底显示**
   - 所有字段在无数据时显示 `--`

---

## 七、后续优化建议

1. **数据缓存**：Redis缓存实时行情，减少数据库查询
2. **增量更新**：只更新变化的数据字段
3. **数据校验**：添加异常数据检测和告警
4. **历史趋势**：保存每日指标，绘制趋势图
5. **对比分析**：板块内基金指标对比

---

## 八、测试验证

### 验证步骤

1. 运行数据库迁移：`node backend/database/migrate-add-fields.js`
2. 重启后端服务：`npm start`
3. 打开基金详情页，检查以下字段：
   - [ ] 溢价率显示正确
   - [ ] 流通市值显示正确
   - [ ] 机构持仓显示正确
   - [ ] 净值显示正确
   - [ ] 债务率显示正确

### 调试命令

```bash
# 检查API返回
curl http://localhost:3000/api/funds/508056

# 检查数据库数据
sqlite3 backend/database/reits.db \
  "SELECT code, nav, circulating_shares, institution_hold FROM funds WHERE code='508056';"
```
