# REIT公告8张专项表设计

## 概述
将单一的announcements表拆分为8张专项表，分别处理不同类型的公告，每张表都有针对性的字段设计。

---

## 8张公告表结构

### 1. announcements - 基础公告表
**用途**: 存储所有公告的基础信息，作为其他表的关联入口

```sql
CREATE TABLE announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_code TEXT NOT NULL,              -- 基金代码
    title TEXT NOT NULL,                  -- 公告标题
    category TEXT NOT NULL,               -- 公告分类（dividend/operation/financial/inquiry/asset/major/other）
    publish_date TEXT NOT NULL,           -- 发布日期
    announcement_type TEXT,               -- 公告类型（如：收益分配公告、运营情况报告）
    exchange TEXT,                        -- 交易所（SSE/SZSE）
    pdf_url TEXT,                         -- PDF链接
    source_url TEXT,                      -- 原文链接（巨潮资讯网）
    is_key_announcement INTEGER DEFAULT 0, -- 是否重大事项（0/1）
    confidence REAL,                      -- AI分类置信度
    summary TEXT,                         -- AI摘要
    extracted_status TEXT DEFAULT 'pending', -- 提取状态：pending/processing/completed/failed
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fund_code) REFERENCES funds(code)
);
```

---

### 2. dividend_announcements - 分红公告详情表
**用途**: 存储分红公告的详细数据

```sql
CREATE TABLE dividend_announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    announcement_id INTEGER NOT NULL,     -- 关联announcements.id
    
    -- 分红方案
    dividend_amount_total REAL,           -- 分红总金额（元）
    dividend_per_10_units REAL,           -- 每10份分红金额（元）
    dividend_per_unit REAL,               -- 每份分红金额（元）
    
    -- 关键日期
    record_date TEXT,                     -- 权益登记日
    ex_dividend_date TEXT,                -- 除息日
    payment_date TEXT,                     -- 分红发放日
    base_date TEXT,                        -- 收益分配基准日
    
    -- 收益数据
    distributable_income REAL,            -- 可分配金额（元）
    net_profit REAL,                      -- 净利润（元）
    distribution_ratio REAL,              -- 分红比例（%）
    annualized_yield REAL,                -- 年化派息率（%）
    
    -- 对比上期
    last_dividend_amount REAL,            -- 上期分红金额（元）
    change_percent REAL,                  -- 变动比例（%）
    
    -- 说明
    dividend_description TEXT,            -- 分红说明
    tax_info TEXT,                        -- 税收信息
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (announcement_id) REFERENCES announcements(id) ON DELETE CASCADE
);
```

---

### 3. operation_announcements - 运营公告详情表
**用途**: 存储底层资产运营情况公告

```sql
CREATE TABLE operation_announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    announcement_id INTEGER NOT NULL,     -- 关联announcements.id
    
    -- 报告期
    report_period TEXT,                   -- 报告期（如：2024年Q1）
    report_start_date TEXT,               -- 报告期起始日
    report_end_date TEXT,                 -- 报告期截止日
    
    -- 出租率指标
    occupancy_rate REAL,                  -- 出租率（%）
    occupancy_rate_change REAL,           -- 出租率变动（百分点）
    leased_area REAL,                     -- 已租面积（平方米）
    total_area REAL,                      -- 总面积（平方米）
    
    -- 租金指标
    avg_rent_price REAL,                  -- 平均租金（元/平方米/天）
    rent_price_change REAL,               -- 租金变动（%）
    rent_collection_rate REAL,            -- 租金收缴率（%）
    
    -- 租户情况
    tenant_count INTEGER,                 -- 租户数量
    top5_tenant_ratio REAL,               -- 前五大租户占比（%）
    top10_tenant_ratio REAL,              -- 前十大租户占比（%）
    wale REAL,                            -- 加权平均租赁期限（年）
    
    -- 收入情况（根据REIT类型不同）
    rental_income REAL,                   -- 租金收入（元）
    property_income REAL,                 -- 物业收入（元）
    other_income REAL,                    -- 其他收入（元）
    total_income REAL,                    -- 总收入（元）
    
    -- 特定类型指标
    traffic_volume INTEGER,               -- 客流量（人次）- 商业REIT
    traffic_change REAL,                  -- 客流变动（%）
    vehicle_flow INTEGER,                 -- 车流量（辆次）- 高速公路REIT
    
    -- 运营说明
    operation_summary TEXT,               -- 运营情况摘要
    risk_alerts TEXT,                     -- 风险提示
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (announcement_id) REFERENCES announcements(id) ON DELETE CASCADE
);
```

---

### 4. financial_announcements - 财务公告详情表
**用途**: 存储年报、中报、季报的财务数据

```sql
CREATE TABLE financial_announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    announcement_id INTEGER NOT NULL,     -- 关联announcements.id
    
    -- 报告期
    report_period TEXT,                   -- 报告期（2024年报/2024中报）
    report_type TEXT,                     -- 报告类型（annual/semi_annual/quarterly）
    accounting_period TEXT,               -- 会计期间
    
    -- 资产负债表
    total_assets REAL,                    -- 总资产（元）
    total_liabilities REAL,               -- 总负债（元）
    net_assets REAL,                      -- 净资产（元）
    asset_liability_ratio REAL,           -- 资产负债率（%）
    
    -- 利润表
    operating_income REAL,                -- 营业收入（元）
    operating_cost REAL,                  -- 营业成本（元）
    operating_profit REAL,                -- 营业利润（元）
    net_profit REAL,                      -- 净利润（元）
    
    -- 现金流量表
    operating_cash_flow REAL,             -- 经营活动现金流（元）
    investing_cash_flow REAL,             -- 投资活动现金流（元）
    financing_cash_flow REAL,             -- 筹资活动现金流（元）
    net_cash_increase REAL,               -- 现金净增加额（元）
    
    -- 关键比率
    gross_margin REAL,                    -- 毛利率（%）
    net_margin REAL,                      -- 净利率（%）
    roe REAL,                             -- 净资产收益率（%）
    
    -- 可供分配金额
    distributable_amount REAL,            -- 可供分配金额（元）
    actual_distribution REAL,             -- 实际分配金额（元）
    distribution_rate REAL,               -- 分配比例（%）
    
    -- 对比上期
    revenue_growth REAL,                  -- 营收增长率（%）
    profit_growth REAL,                   -- 利润增长率（%）
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (announcement_id) REFERENCES announcements(id) ON DELETE CASCADE
);
```

---

### 5. inquiry_announcements - 询价/发售公告详情表
**用途**: 存储询价、定价、发售相关公告

```sql
CREATE TABLE inquiry_announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    announcement_id INTEGER NOT NULL,     -- 关联announcements.id
    
    -- 发售类型
    offering_type TEXT,                   -- 发售类型（IPO/扩募/增发）
    
    -- 发售规模
    total_offering REAL,                  -- 发售总份额（万份）
    public_offering REAL,                 -- 公众发售份额（万份）
    institutional_offering REAL,          -- 机构发售份额（万份）
    strategic_offering REAL,              -- 战略配售份额（万份）
    
    -- 定价信息
    inquiry_price_low REAL,               -- 询价区间下限（元）
    inquiry_price_high REAL,              -- 询价区间上限（元）
    final_price REAL,                     -- 最终定价（元）
    price_to_nav REAL,                    -- 定价相对净值溢价率（%）
    
    -- 募集资金
    raised_capital_total REAL,            -- 募集总金额（元）
    raised_capital_net REAL,              -- 募集资金净额（元）
    
    -- 认购情况
    public_subscription_ratio REAL,       -- 公众认购倍数
    institutional_subscription_ratio REAL,-- 机构认购倍数
    over_subscription_ratio REAL,         -- 超额认购倍数
    
    -- 关键日期
    inquiry_start_date TEXT,              -- 询价起始日
    inquiry_end_date TEXT,                -- 询价截止日
    subscription_start_date TEXT,         -- 认购起始日
    subscription_end_date TEXT,           -- 认购截止日
    listing_date TEXT,                    -- 上市日期
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (announcement_id) REFERENCES announcements(id) ON DELETE CASCADE
);
```

---

### 6. asset_announcements - 底层资产公告详情表
**用途**: 存储底层资产变动、评估、处置公告

```sql
CREATE TABLE asset_announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    announcement_id INTEGER NOT NULL,     -- 关联announcements.id
    
    -- 资产基本信息
    asset_name TEXT,                      -- 资产名称
    asset_type TEXT,                      -- 资产类型（产业园/物流/高速公路/环保等）
    asset_location TEXT,                  -- 资产位置
    asset_area REAL,                      -- 资产面积（平方米）
    
    -- 评估信息
    appraisal_date TEXT,                  -- 评估基准日
    appraisal_value REAL,                 -- 评估价值（元）
    last_appraisal_value REAL,            -- 上次评估价值（元）
    value_change REAL,                    -- 价值变动（元）
    value_change_percent REAL,            -- 价值变动率（%）
    
    -- 交易信息
    transaction_type TEXT,                -- 交易类型（收购/处置/置换）
    transaction_price REAL,               -- 交易价格（元）
    transaction_counterparty TEXT,        -- 交易对手方
    
    -- 抵押/担保
    mortgage_status TEXT,                 -- 抵押状态（有/无）
    mortgage_amount REAL,                 -- 抵押金额（元）
    guarantee_status TEXT,                -- 担保状态
    
    -- 资产变动说明
    asset_change_reason TEXT,             -- 资产变动原因
    impact_analysis TEXT,                 -- 影响分析
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (announcement_id) REFERENCES announcements(id) ON DELETE CASCADE
);
```

---

### 7. major_event_announcements - 重大事项公告详情表
**用途**: 存储重大事项、风险提示、关联交易等公告

```sql
CREATE TABLE major_event_announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    announcement_id INTEGER NOT NULL,     -- 关联announcements.id
    
    -- 事件类型
    event_type TEXT,                      -- 事件类型（risk/related_party/change_manager/litigation/other）
    event_type_name TEXT,                 -- 事件类型名称
    
    -- 事件描述
    event_summary TEXT,                   -- 事件摘要
    event_detail TEXT,                    -- 事件详情
    event_cause TEXT,                     -- 事件原因
    
    -- 影响分析
    impact_level TEXT,                    -- 影响级别（high/medium/low）
    impact_scope TEXT,                    -- 影响范围
    impact_duration TEXT,                 -- 预计影响时长
    financial_impact REAL,                -- 财务影响金额（元）
    
    -- 相关方
    related_party_name TEXT,              -- 相关方名称
    related_party_relation TEXT,          -- 与基金关系
    
    -- 处理措施
    handling_measures TEXT,               -- 处理措施
    follow_up_plan TEXT,                  -- 后续计划
    
    -- 进展跟踪
    event_status TEXT,                    -- 事件状态（ongoing/resolved）
    latest_progress TEXT,                 -- 最新进展
    resolution_date TEXT,                 -- 预计解决日期
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (announcement_id) REFERENCES announcements(id) ON DELETE CASCADE
);
```

---

### 8. pdf_extractions - PDF提取结果表
**用途**: 存储PDF提取的原始数据和AI提取结果

```sql
CREATE TABLE pdf_extractions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    announcement_id INTEGER NOT NULL,     -- 关联announcements.id
    
    -- PDF信息
    pdf_url TEXT NOT NULL,                -- PDF链接
    pdf_size INTEGER,                     -- PDF大小（字节）
    pdf_pages INTEGER,                    -- PDF页数
    
    -- 提取结果（三AI结果）
    extractor1_result JSON,               -- 基础信息提取结果（JSON）
    extractor2_result JSON,               -- 财务数据提取结果（JSON）
    extractor3_result JSON,               -- 运营数据提取结果（JSON）
    
    -- 验证结果
    validation_result JSON,               -- 交叉验证结果（JSON）
    final_extracted_data JSON,            -- 最终合并的数据（JSON）
    
    -- 置信度
    overall_confidence REAL,              -- 整体置信度（0-100）
    field_confidence JSON,                -- 各字段置信度（JSON）
    
    -- 处理状态
    extraction_status TEXT DEFAULT 'pending', -- pending/processing/completed/failed/manual_review
    retry_count INTEGER DEFAULT 0,        -- 重试次数
    
    -- 人工审核
    review_status TEXT,                   -- 审核状态（auto_pass/manual_review/rejected）
    reviewed_by TEXT,                     -- 审核人
    reviewed_at DATETIME,                 -- 审核时间
    review_comments TEXT,                 -- 审核意见
    
    -- 元数据
    extraction_model TEXT,                -- 使用的模型版本
    extraction_time_ms INTEGER,           -- 提取耗时（毫秒）
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (announcement_id) REFERENCES announcements(id) ON DELETE CASCADE,
    UNIQUE(announcement_id)
);

-- 提取历史版本表（可选，用于追踪同一PDF多次提取）
CREATE TABLE pdf_extraction_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    extraction_id INTEGER NOT NULL,       -- 关联pdf_extractions.id
    version INTEGER NOT NULL,             -- 版本号
    extracted_data JSON,                  -- 提取数据
    confidence REAL,                      -- 置信度
    model_version TEXT,                   -- 模型版本
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (extraction_id) REFERENCES pdf_extractions(id) ON DELETE CASCADE
);
```

---

## 表关系图

```
┌─────────────────────────────────────────────────────────────────┐
│                     announcements                               │
│  (基础公告信息，所有公告的统一入口)                               │
│  - id, fund_code, title, category, publish_date, pdf_url        │
└─────────────────┬───────────────────────────────────────────────┘
                  │ 1:1 关系
    ┌─────────────┼─────────────┬─────────────┬─────────────┬─────────────┐
    ▼             ▼             ▼             ▼             ▼             ▼
┌────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│dividend│  │operation │  │financial │  │ inquiry  │  │  asset   │  │  major   │
│announce│  │announce  │  │announce  │  │announce  │  │announce  │  │ announce │
│-ments  │  │-ments    │  │-ments    │  │-ments    │  │-ments    │  │ -ments   │
└────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     pdf_extractions                             │
│  (PDF提取结果，包含三AI提取数据和验证结果)                         │
│  - announcement_id, extractor1/2/3_result, validation_result    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 数据流转流程

```
1. 公告爬取
   ↓
2. announcements表插入基础数据
   ↓
3. PDF提取Pipeline触发
   ├─ MinerU版面恢复 → Markdown
   ├─ Extractor1提取 → JSON
   ├─ Extractor2提取 → JSON
   ├─ Extractor3提取 → JSON
   ├─ Validator验证 → 置信度评分
   ↓
4. pdf_extractions表存储提取结果
   ↓
5. 根据category将数据写入对应详情表
   ├─ dividend_announcements (分红数据)
   ├─ operation_announcements (运营数据)
   ├─ financial_announcements (财务数据)
   ├─ inquiry_announcements (询价数据)
   ├─ asset_announcements (资产数据)
   └─ major_event_announcements (重大事项)
   ↓
6. 数据可用（前端展示/AI分析）
```

---

## 索引设计

```sql
-- announcements表索引
CREATE INDEX idx_announcements_fund_date ON announcements(fund_code, publish_date);
CREATE INDEX idx_announcements_category ON announcements(category);
CREATE INDEX idx_announcements_extracted ON announcements(extracted_status);

-- 各详情表索引
CREATE INDEX idx_dividend_record_date ON dividend_announcements(record_date);
CREATE INDEX idx_operation_period ON operation_announcements(report_period);
CREATE INDEX idx_financial_period ON financial_announcements(report_period);

-- pdf_extractions索引
CREATE INDEX idx_pdf_extraction_status ON pdf_extractions(extraction_status, review_status);
CREATE INDEX idx_pdf_confidence ON pdf_extractions(overall_confidence);
```

---

## 实施建议

### Phase 1: 基础改造 (1周)
1. 修改现有announcements表，添加extracted_status字段
2. 创建pdf_extractions表
3. 实现单AI提取Pipeline

### Phase 2: 专项表建设 (2周)
1. 创建6张详情表（dividend/operation/financial/inquiry/asset/major）
2. 实现根据category自动分发数据到对应表
3. 实现数据验证和清洗逻辑

### Phase 3: 三AI验证 (2周)
1. 实现三AI并行提取
2. 实现交叉验证逻辑
3. 实现人工审核后台

### Phase 4: 历史数据迁移 (1周)
1. 对651条历史公告进行PDF提取
2. 数据清洗和入库
3. 质量检查和补录

---

**下一步**: 是否需要我开始实施Phase 1，先创建这些表并实现基础提取功能？