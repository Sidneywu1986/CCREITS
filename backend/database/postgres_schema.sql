-- ============================================================
-- CCREITS PostgreSQL 统一数据库 Schema
-- 版本: 3.0.0
-- 说明: 将 SQLite 主业务库 + AI PostgreSQL 库合并为单一 PostgreSQL 数据库
--       使用 schema 隔离不同业务域
-- ============================================================

-- --------------------------------------------------
-- 0. 创建业务 Schema
-- --------------------------------------------------
CREATE SCHEMA IF NOT EXISTS business;
CREATE SCHEMA IF NOT EXISTS ai;
CREATE SCHEMA IF NOT EXISTS admin;

-- 设置默认搜索路径（可选，应用层建议显式指定 schema）
-- SET search_path TO business, ai, admin, public;

-- ============================================================
-- 第一部分: 业务核心表 (business schema)
-- ============================================================

-- --------------------------------------------------
-- 1.1 基金基础信息表 (兼容原 funds + reit_product_info)
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS business.funds (
    fund_code               VARCHAR(20) PRIMARY KEY,
    fund_name               VARCHAR(200) NOT NULL,
    fund_short_name         VARCHAR(100),
    full_name               VARCHAR(200),
    fund_type               VARCHAR(20) NOT NULL DEFAULT '产权类' CHECK (fund_type IN ('产权类', '经营权类')),
    asset_type              VARCHAR(50),                -- 产业园/仓储物流/保障性租赁住房/购物中心/高速公路/新能源等
    sector                  VARCHAR(50),                -- 简化板块标识（兼容旧代码）
    sector_name             VARCHAR(50),                -- 板块显示名（兼容旧代码）
    exchange                VARCHAR(10),                -- SSE / SZSE
    manager                 VARCHAR(100),               -- 基金管理人
    manager_name            VARCHAR(100),               -- 兼容 RSDS 字段
    custodian               VARCHAR(100),               -- 基金托管人
    custodian_name          VARCHAR(100),               -- 兼容 RSDS 字段
    operating_manager       VARCHAR(200),               -- 运营管理机构
    abs_manager             VARCHAR(100),               -- ABS管理人（经营权类）
    original_equity_holder  VARCHAR(100),               -- 原始权益人（经营权类）
    status                  VARCHAR(20) DEFAULT 'active',

    -- 发行与上市
    issue_date              DATE,                       -- 发行日期
    listing_date            DATE,                       -- 上市日期
    ipo_date                VARCHAR(20),                -- 兼容旧代码
    issue_price             NUMERIC(18,4),              -- 发行价/元
    ipo_price               NUMERIC(18,4),              -- 兼容旧代码
    issue_amount            NUMERIC(18,4),              -- 发行规模/亿元
    fund_shares             NUMERIC(18,4),              -- 基金份额/亿份
    total_shares            NUMERIC(18,4),              -- 兼容旧代码

    -- 费率
    management_fee_rate     NUMERIC(8,4),               -- 管理费率
    custody_fee_rate        NUMERIC(8,4),               -- 托管费率

    -- 最新指标（缓存，定时更新）
    nav                     NUMERIC(18,4),              -- 最新单位净值
    market_cap              NUMERIC(18,4),              -- 流通市值/万元
    scale                   NUMERIC(18,4),              -- 规模/亿元
    dividend_yield          NUMERIC(8,4),               -- 股息率/%
    debt_ratio              NUMERIC(8,4),               -- 债务率/%
    premium_rate            NUMERIC(8,4),               -- 溢价率/%
    property_type           VARCHAR(50),                -- 资产类型
    remaining_years         VARCHAR(50),                -- 剩余期限
    underlying_assets       TEXT,                       -- 底层资产描述
    investment_scope        TEXT,                       -- 投资范围

    -- 经营权类特有
    concession_period_years INTEGER,                    -- 特许经营权年限
    concession_start_date   DATE,                       -- 特许经营起始日
    concession_end_date     DATE,                       -- 特许经营到期日
    operation_start_date    DATE,                       -- 运营起始日
    remaining_concession_years INTEGER,                 -- 剩余特许经营年限
    credit_rating           VARCHAR(10),                -- 信用评级
    compliance_defect_flag  BOOLEAN DEFAULT FALSE,      -- 合规缺陷标记
    missing_certificates    JSONB,                      -- 缺失证照清单
    rights_restriction_amount NUMERIC(18,4),            -- 权利限制金额
    unpooled_asset_ratio    NUMERIC(8,4),               -- 未入池资产比例/%
    competition_coefficient NUMERIC(8,4),               -- 竞争系数

    -- 数据血缘
    lineage_id              INTEGER,
    data_verified           BOOLEAN DEFAULT FALSE,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_funds_asset_type ON business.funds (asset_type);
CREATE INDEX idx_funds_manager ON business.funds (manager);
CREATE INDEX idx_funds_listing ON business.funds (listing_date);
CREATE INDEX idx_funds_sector ON business.funds (sector);
CREATE INDEX idx_funds_exchange ON business.funds (exchange);
CREATE INDEX idx_funds_fund_type ON business.funds (fund_type);
CREATE INDEX idx_funds_data_verified ON business.funds (data_verified) WHERE data_verified = FALSE;

-- --------------------------------------------------
-- 1.2 实时行情快照表（兼容原 quotes）
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS business.quotes (
    id                      SERIAL PRIMARY KEY,
    fund_code               VARCHAR(20) NOT NULL REFERENCES business.funds(fund_code) ON DELETE CASCADE,
    price                   NUMERIC(18,4) NOT NULL,     -- 当前价
    change_percent          NUMERIC(8,4),               -- 涨跌幅/%
    change_amount           NUMERIC(18,4),              -- 涨跌额
    volume                  BIGINT,                     -- 成交量
    premium                 NUMERIC(8,4),               -- 溢价率/%
    yield                   NUMERIC(8,4),               -- 派息率/%
    market_cap              NUMERIC(18,4),              -- 流通市值/亿元
    turnover_rate           NUMERIC(8,4),               -- 换手率/%
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_quotes_fund_code ON business.quotes (fund_code);
CREATE INDEX idx_quotes_updated ON business.quotes (updated_at);
CREATE UNIQUE INDEX idx_quotes_fund_unique ON business.quotes (fund_code); -- 每只基金仅一条最新快照

-- --------------------------------------------------
-- 1.3 历史行情表 / 日K线表（兼容 price_history + daily_data）
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS business.price_history (
    id                      SERIAL PRIMARY KEY,
    fund_code               VARCHAR(20) NOT NULL REFERENCES business.funds(fund_code) ON DELETE CASCADE,
    trade_date              DATE NOT NULL,              -- 交易日期
    open_price              NUMERIC(18,4),              -- 开盘价
    close_price             NUMERIC(18,4),              -- 收盘价
    high_price              NUMERIC(18,4),              -- 最高价
    low_price               NUMERIC(18,4),              -- 最低价
    volume                  BIGINT,                     -- 成交量
    amount                  NUMERIC(18,4),              -- 成交额/万元
    turnover_rate           NUMERIC(8,4),               -- 换手率/%
    daily_return            NUMERIC(8,4),               -- 日收益率/%
    nav_premium_rate        NUMERIC(8,4),               -- 净值溢价率/%
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(fund_code, trade_date)
);

CREATE INDEX idx_price_history_fund_date ON business.price_history (fund_code, trade_date DESC);
CREATE INDEX idx_price_history_trade_date ON business.price_history (trade_date DESC);

-- --------------------------------------------------
-- 1.4 基金价格表（兼容 fund_analysis.py 查询的 fund_prices）
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS business.fund_prices (
    id                      SERIAL PRIMARY KEY,
    fund_code               VARCHAR(20) NOT NULL REFERENCES business.funds(fund_code) ON DELETE CASCADE,
    trade_date              DATE NOT NULL,
    close_price             NUMERIC(18,4),
    change_pct              NUMERIC(8,4),
    volume                  BIGINT,
    premium_rate            NUMERIC(8,4),
    yield                   NUMERIC(8,4),
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(fund_code, trade_date)
);

CREATE INDEX idx_fund_prices_fund_date ON business.fund_prices (fund_code, trade_date DESC);

-- --------------------------------------------------
-- 1.5 分红派息表（兼容 dividends + reit_dividend_history）
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS business.dividends (
    id                      SERIAL PRIMARY KEY,
    fund_code               VARCHAR(20) NOT NULL REFERENCES business.funds(fund_code) ON DELETE CASCADE,
    dividend_year           INTEGER,                    -- 分红年度
    dividend_round          INTEGER DEFAULT 1,          -- 分红轮次
    dividend_date           DATE,                       -- 分红日期（兼容旧代码）
    dividend_amount         NUMERIC(18,6),              -- 每份分红金额/元
    dividend_per_share      NUMERIC(18,6),              -- 兼容 RSDS 字段
    total_dividend          NUMERIC(18,4),              -- 分红总额/万元
    dividend_yield          NUMERIC(8,4),               -- 分红收益率/%
    record_date             DATE,                       -- 权益登记日
    ex_dividend_date        DATE,                       -- 除息日
    dividend_payment_date   DATE,                       -- 红利发放日
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(fund_code, dividend_year, dividend_round)
);

CREATE INDEX idx_dividends_fund ON business.dividends (fund_code);
CREATE INDEX idx_dividends_fund_year ON business.dividends (fund_code, dividend_year);
CREATE INDEX idx_dividends_payment ON business.dividends (dividend_payment_date);
CREATE INDEX idx_dividends_ex_date ON business.dividends (ex_dividend_date);

-- --------------------------------------------------
-- 1.6 公告表（兼容 announcements + wechat_articles）
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS business.announcements (
    id                      SERIAL PRIMARY KEY,
    fund_code               VARCHAR(20) REFERENCES business.funds(fund_code) ON DELETE SET NULL,
    fund_name               VARCHAR(100),               -- 冗余缓存
    title                   VARCHAR(500) NOT NULL,
    content                 TEXT,                       -- 公告正文或摘要
    category                VARCHAR(50),                -- operation/dividend/inquiry/financial
    announcement_type       VARCHAR(50),                -- 兼容旧代码
    summary                 TEXT,                       -- AI摘要
    publish_date            DATE,                       -- 发布日期
    source                  VARCHAR(50),                -- 来源标识
    source_url              VARCHAR(500),               -- 原文链接
    pdf_url                 VARCHAR(500),               -- PDF下载链接
    exchange                VARCHAR(10),                -- SSE / SZSE
    confidence              NUMERIC(8,4),               -- AI分类置信度
    is_read                 BOOLEAN DEFAULT FALSE,
    is_processed            BOOLEAN DEFAULT FALSE,
    is_important            BOOLEAN DEFAULT FALSE,
    sentiment_score         NUMERIC(8,4),               -- 情感分数
    emotion_tag             VARCHAR(20),                -- 情感标签
    event_tags              JSONB,                      -- 事件标签
    content_hash            VARCHAR(64) UNIQUE,         -- 内容去重哈希
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_announcements_fund ON business.announcements (fund_code);
CREATE INDEX idx_announcements_date ON business.announcements (publish_date DESC);
CREATE INDEX idx_announcements_category ON business.announcements (category);
CREATE INDEX idx_announcements_source ON business.announcements (source);
CREATE INDEX idx_announcements_important ON business.announcements (is_important) WHERE is_important = TRUE;
CREATE INDEX idx_announcements_hash ON business.announcements (content_hash);

-- --------------------------------------------------
-- 1.7 微信公众号/研报文章表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS business.wechat_articles (
    id                      SERIAL PRIMARY KEY,
    title                   VARCHAR(500) NOT NULL,
    content                 TEXT,
    link                    VARCHAR(500),
    author                  VARCHAR(100),
    source                  VARCHAR(100),
    published               TIMESTAMP,
    category                VARCHAR(50),
    sentiment_score         NUMERIC(8,4) DEFAULT 0,
    emotion_tag             VARCHAR(20),
    event_tags              JSONB,
    related_funds           JSONB,
    content_hash            VARCHAR(64) UNIQUE,
    is_processed            BOOLEAN DEFAULT FALSE,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_wechat_articles_published ON business.wechat_articles (published DESC);
CREATE INDEX idx_wechat_articles_sentiment ON business.wechat_articles (sentiment_score DESC);
CREATE INDEX idx_wechat_articles_category ON business.wechat_articles (category);
CREATE INDEX idx_wechat_articles_hash ON business.wechat_articles (content_hash);

-- --------------------------------------------------
-- 1.8 大盘指数表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS business.market_indices (
    code                    VARCHAR(50) PRIMARY KEY,    -- sh_index, dividend, reits_total, bond_yield
    name                    VARCHAR(100) NOT NULL,
    value                   NUMERIC(18,4) NOT NULL,
    change_value            NUMERIC(18,4),              -- 涨跌值
    change_percent          NUMERIC(8,4),               -- 涨跌幅/%
    source                  VARCHAR(50),
    updated_at              TIMESTAMP,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_market_indices_updated ON business.market_indices (updated_at DESC);

-- --------------------------------------------------
-- 1.9 数据源追踪表（血缘管理）
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS business.data_sources (
    id                      SERIAL PRIMARY KEY,
    data_type               VARCHAR(50) NOT NULL,       -- price/announcement/nav等
    source_name             VARCHAR(100) NOT NULL,      -- sina-finance/sse/cninfo等
    source_url              VARCHAR(500),
    api_endpoint            VARCHAR(500),
    fetch_interval          INTEGER DEFAULT 60,         -- 抓取间隔/分钟
    last_updated            TIMESTAMP,
    last_fetch_at           TIMESTAMP,
    update_count            INTEGER DEFAULT 0,
    status                  VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'error', 'disabled')),
    error_msg               TEXT,
    is_active               BOOLEAN DEFAULT TRUE,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_data_sources_type ON business.data_sources (data_type);
CREATE INDEX idx_data_sources_status ON business.data_sources (status);

-- --------------------------------------------------
-- 1.10 数据更新日志表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS business.update_logs (
    id                      SERIAL PRIMARY KEY,
    data_type               VARCHAR(50) NOT NULL,
    source                  VARCHAR(100),
    status                  VARCHAR(20) NOT NULL CHECK (status IN ('success', 'error', 'partial')),
    records_count           INTEGER,
    duration_ms             INTEGER,
    error_msg               TEXT,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_update_logs_type ON business.update_logs (data_type, created_at DESC);
CREATE INDEX idx_update_logs_status ON business.update_logs (status);


-- ============================================================
-- 第二部分: RSDS v1.1.2 标准表 (business schema)
-- ============================================================

-- --------------------------------------------------
-- 2.1 数据血缘追踪表（两类REIT共用）
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS business.data_lineage (
    id                      SERIAL PRIMARY KEY,
    table_name              VARCHAR(50) NOT NULL,
    record_id               VARCHAR(50) NOT NULL,
    project_code            VARCHAR(20) NOT NULL,
    agent_name              VARCHAR(50),
    source_type             VARCHAR(20),
    source_document         VARCHAR(200),
    source_url              VARCHAR(500) NOT NULL,
    source_page             INTEGER,
    extracted_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confidence_score        NUMERIC(4,3) CHECK (confidence_score BETWEEN 0 AND 1),
    raw_snapshot            TEXT,
    operator_id             VARCHAR(50),
    data_verified           BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_lineage_project ON business.data_lineage (project_code, extracted_at);
CREATE INDEX idx_lineage_source ON business.data_lineage (source_url);
CREATE INDEX idx_lineage_unverified ON business.data_lineage (data_verified) WHERE data_verified = FALSE;

-- --------------------------------------------------
-- 2.2 产权类 - 资产信息表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS business.reit_property_info (
    property_id             SERIAL PRIMARY KEY,
    fund_code               VARCHAR(20) NOT NULL REFERENCES business.funds(fund_code) ON DELETE CASCADE,
    property_name           VARCHAR(200),
    city                    VARCHAR(50),
    district                VARCHAR(50),
    address                 VARCHAR(500),
    property_type           VARCHAR(50),                -- 办公楼/商业综合体/产业园/仓储物流等
    building_area           NUMERIC(18,4),              -- 建筑面积/㎡
    leasable_area           NUMERIC(18,4),              -- 可出租面积/㎡
    valuation_date          DATE,                       -- 评估基准日
    appraised_value         NUMERIC(18,4),              -- 评估价值/万元
    value_per_sqm           NUMERIC(18,4),              -- 单价/元/㎡
    tenant_count            INTEGER,
    occupancy_rate          NUMERIC(8,4) CHECK (occupancy_rate BETWEEN 0 AND 100), -- 出租率%
    average_rent            NUMERIC(18,4),              -- 平均租金/元/㎡/月
    weighted_lease_term     NUMERIC(8,4),               -- 加权平均租期/年
    expiration_date         DATE DEFAULT '9999-12-31',
    lineage_id              INTEGER REFERENCES business.data_lineage(id),
    data_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_verified           BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_property_fund ON business.reit_property_info (fund_code);
CREATE INDEX idx_property_city ON business.reit_property_info (city);
CREATE INDEX idx_property_type ON business.reit_property_info (property_type);

-- --------------------------------------------------
-- 2.3 产权类 - 租约明细表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS business.reit_lease_detail (
    id                      SERIAL PRIMARY KEY,
    fund_code               VARCHAR(20) NOT NULL REFERENCES business.funds(fund_code) ON DELETE CASCADE,
    lease_id                VARCHAR(50) NOT NULL,
    tenant_name             VARCHAR(100) NOT NULL,
    industry_gics           VARCHAR(20),
    tenant_credit_rating    VARCHAR(10),
    lease_area_sqm          NUMERIC(18,4),
    area_ratio_pct          NUMERIC(8,4) CHECK (area_ratio_pct BETWEEN 0 AND 100),
    rent_per_sqm            NUMERIC(18,4),
    market_rent_per_sqm     NUMERIC(18,4),
    rent_discount_pct       NUMERIC(8,4),               -- 租金折扣率%，<-15% 触发利益输送标记
    lease_start             DATE,
    lease_end               DATE,
    remaining_months        INTEGER,
    expiry_year             INTEGER,
    rent_free_months        INTEGER,
    is_related_party        BOOLEAN DEFAULT FALSE,
    related_party_name      VARCHAR(100),
    renewal_option          VARCHAR(50),
    deposit_months          INTEGER,
    effective_date          DATE DEFAULT CURRENT_DATE,
    expiration_date         DATE DEFAULT '9999-12-31',
    lineage_id              INTEGER REFERENCES business.data_lineage(id),
    data_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(fund_code, lease_id)
);

CREATE INDEX idx_lease_fund_expiry ON business.reit_lease_detail (fund_code, expiry_year);
CREATE INDEX idx_lease_related_discount ON business.reit_lease_detail (fund_code, rent_discount_pct) WHERE is_related_party = TRUE;
CREATE INDEX idx_lease_current ON business.reit_lease_detail (fund_code, effective_date, expiration_date) WHERE expiration_date = '9999-12-31';
CREATE INDEX idx_lease_2026 ON business.reit_lease_detail (fund_code, area_ratio_pct) WHERE expiry_year = 2026;

-- --------------------------------------------------
-- 2.4 产权类 - 财务指标表（与现有 reit_financial_metrics 合并）
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS business.reit_financial_metrics (
    id                      SERIAL PRIMARY KEY,
    fund_code               VARCHAR(20) NOT NULL REFERENCES business.funds(fund_code) ON DELETE CASCADE,
    report_period           VARCHAR(10) NOT NULL,       -- 如2024Q3
    total_revenue           NUMERIC(18,4),              -- 营业总收入/万元
    operating_revenue       NUMERIC(18,4),              -- 运营收入/万元
    net_profit              NUMERIC(18,4),              -- 净利润/万元
    total_assets            NUMERIC(18,4),              -- 总资产/万元
    net_assets              NUMERIC(18,4),              -- 净资产/万元
    fund_nav_per_share      NUMERIC(18,6),              -- 基金净值/元/份
    distributeable_amount   NUMERIC(18,4),              -- 可供分配金额/万元
    distribution_per_share  NUMERIC(18,6),              -- 每份可供分配金额/元
    lineage_id              INTEGER REFERENCES business.data_lineage(id),
    data_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_verified           BOOLEAN DEFAULT FALSE,
    UNIQUE(fund_code, report_period)
);

CREATE INDEX idx_fin_fund_period ON business.reit_financial_metrics (fund_code, report_period);
CREATE INDEX idx_fin_distributable ON business.reit_financial_metrics (distributeable_amount) WHERE distributeable_amount IS NOT NULL;

-- --------------------------------------------------
-- 2.5 产权类 - 运营数据表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS business.reit_operational_data (
    id                      SERIAL PRIMARY KEY,
    fund_code               VARCHAR(20) NOT NULL REFERENCES business.funds(fund_code) ON DELETE CASCADE,
    report_period           VARCHAR(10) NOT NULL,
    occupancy_rate          NUMERIC(8,4) CHECK (occupancy_rate BETWEEN 0 AND 100),
    cap_rate                NUMERIC(8,4),               -- 资本化率%
    average_rent            NUMERIC(18,4),              -- 平均租金/元/㎡/月
    rent_growth_rate        NUMERIC(8,4),               -- 租金增长率%
    operating_expense       NUMERIC(18,4),              -- 运营成本/万元
    expense_ratio           NUMERIC(8,4) CHECK (expense_ratio BETWEEN 0 AND 100),
    top_ten_tenant_concentration NUMERIC(8,4) CHECK (top_ten_tenant_concentration BETWEEN 0 AND 100),
    tenant_turnover_rate    NUMERIC(8,4),
    lineage_id              INTEGER REFERENCES business.data_lineage(id),
    data_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_verified           BOOLEAN DEFAULT FALSE,
    UNIQUE(fund_code, report_period)
);

CREATE INDEX idx_ops_fund_period ON business.reit_operational_data (fund_code, report_period);
CREATE INDEX idx_ops_cap_rate ON business.reit_operational_data (cap_rate);

-- --------------------------------------------------
-- 2.6 产权类 - 市场表现表（与 price_history 互补，含更多衍生指标）
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS business.reit_market_performance (
    id                      SERIAL PRIMARY KEY,
    fund_code               VARCHAR(20) NOT NULL REFERENCES business.funds(fund_code) ON DELETE CASCADE,
    trade_date              DATE NOT NULL,
    opening_price           NUMERIC(18,4),
    closing_price           NUMERIC(18,4),
    highest_price           NUMERIC(18,4),
    lowest_price            NUMERIC(18,4),
    turnover                NUMERIC(18,4),              -- 成交额/万元
    volume                  NUMERIC(18,4),              -- 成交量/万手
    turnover_rate           NUMERIC(8,4),               -- 换手率%
    market_cap              NUMERIC(18,4),              -- 市值/万元
    daily_return            NUMERIC(8,4),               -- 日收益率%
    nav_premium_rate        NUMERIC(8,4),               -- 溢价率%
    lineage_id              INTEGER REFERENCES business.data_lineage(id),
    data_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_verified           BOOLEAN DEFAULT FALSE,
    UNIQUE(fund_code, trade_date)
);

CREATE INDEX idx_mkt_fund_date ON business.reit_market_performance (fund_code, trade_date DESC);
CREATE INDEX idx_mkt_premium ON business.reit_market_performance (nav_premium_rate);

-- --------------------------------------------------
-- 2.7 产权类 - 投资者结构表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS business.reit_investor_structure (
    id                      SERIAL PRIMARY KEY,
    fund_code               VARCHAR(20) NOT NULL REFERENCES business.funds(fund_code) ON DELETE CASCADE,
    report_period           VARCHAR(10) NOT NULL,
    investor_type           VARCHAR(20) NOT NULL CHECK (investor_type IN ('个人投资者', '机构投资者')),
    holder_count            INTEGER,
    holding_shares          NUMERIC(18,4),              -- 持有份额/万份
    holding_ratio           NUMERIC(8,4) CHECK (holding_ratio BETWEEN 0 AND 100),
    avg_holding_per_investor NUMERIC(18,4),             -- 户均持有/万份
    lineage_id              INTEGER REFERENCES business.data_lineage(id),
    data_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_verified           BOOLEAN DEFAULT FALSE,
    UNIQUE(fund_code, report_period, investor_type)
);

CREATE INDEX idx_inv_fund_period ON business.reit_investor_structure (fund_code, report_period);
CREATE INDEX idx_inv_type ON business.reit_investor_structure (investor_type);

-- --------------------------------------------------
-- 2.8 产权类 - 风险指标表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS business.reit_risk_metrics (
    id                      SERIAL PRIMARY KEY,
    fund_code               VARCHAR(20) NOT NULL REFERENCES business.funds(fund_code) ON DELETE CASCADE,
    report_period           VARCHAR(10) NOT NULL,
    debt_ratio              NUMERIC(8,4) CHECK (debt_ratio BETWEEN 0 AND 100),
    debt_asset_ratio        NUMERIC(8,4),
    volatility_30d          NUMERIC(8,4),
    volatility_60d          NUMERIC(8,4),
    volatility_90d          NUMERIC(8,4),
    property_concentration  NUMERIC(8,4) CHECK (property_concentration BETWEEN 0 AND 100),
    tenant_concentration    NUMERIC(8,4) CHECK (tenant_concentration BETWEEN 0 AND 100),
    geographic_concentration NUMERIC(8,4) CHECK (geographic_concentration BETWEEN 0 AND 100),
    liquidity_ratio         NUMERIC(8,4),
    credit_rating           VARCHAR(10),
    lineage_id              INTEGER REFERENCES business.data_lineage(id),
    data_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_verified           BOOLEAN DEFAULT FALSE,
    UNIQUE(fund_code, report_period)
);

CREATE INDEX idx_risk_fund_period ON business.reit_risk_metrics (fund_code, report_period);
CREATE INDEX idx_risk_credit ON business.reit_risk_metrics (credit_rating);



-- ============================================================
-- 第三部分: 经营权类 RSDS 标准表 (business schema)
-- ============================================================

-- --------------------------------------------------
-- 3.1 经营权类 - 运营数据明细表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS business.reits_operation_detail (
    id                      SERIAL PRIMARY KEY,
    project_code            VARCHAR(20) NOT NULL REFERENCES business.funds(fund_code) ON DELETE CASCADE,
    report_period           VARCHAR(10) NOT NULL,
    waste_processing_volume NUMERIC(18,4),              -- 垃圾处理量
    waste_capacity_utilization NUMERIC(8,4),            -- 产能利用率
    power_generation        NUMERIC(18,4),              -- 发电量
    grid_settlement_volume  NUMERIC(18,4),              -- 电网结算量
    equivalent_utilization_hours NUMERIC(18,4),         -- 等效利用小时数
    kitchen_waste_collection NUMERIC(18,4),             -- 餐厨垃圾收运量
    kitchen_waste_disposal  NUMERIC(18,4),              -- 餐厨垃圾处置量
    avg_daily_collection    NUMERIC(18,4),              -- 日均收运量
    avg_daily_disposal      NUMERIC(18,4),              -- 日均处置量
    waste_treatment_fee     NUMERIC(18,4),              -- 垃圾处理费
    kitchen_collection_fee  NUMERIC(18,4),              -- 餐厨收运费
    kitchen_disposal_fee    NUMERIC(18,4),              -- 餐厨处置费
    power_price_on_grid     NUMERIC(18,6),              -- 上网电价
    power_price_baseline    NUMERIC(18,6),              -- 基准电价
    subsidy_national        NUMERIC(18,4),              -- 国家补贴
    subsidy_provincial      NUMERIC(18,4),              -- 省级补贴
    subsidy_dependency_ratio NUMERIC(8,4),              -- 补贴依赖度
    grid_company_name       VARCHAR(100),
    major_client_concentration NUMERIC(8,4),
    government_client_ratio NUMERIC(8,4),
    market_client_ratio     NUMERIC(8,4),
    accounts_receivable_amount NUMERIC(18,4),           -- 应收账款金额
    arrear_aging_days       INTEGER,                    -- 账龄天数
    collection_rate         NUMERIC(8,4),               -- 收缴率
    operating_cost          NUMERIC(18,4),              -- 运营成本
    unit_operating_cost     NUMERIC(18,4),              -- 单位运营成本
    lineage_id              INTEGER REFERENCES business.data_lineage(id),
    data_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_verified           BOOLEAN DEFAULT FALSE,
    UNIQUE(project_code, report_period)
);

CREATE INDEX idx_reits_ops_project ON business.reits_operation_detail (project_code, report_period);
CREATE INDEX idx_reits_ops_collection ON business.reits_operation_detail (collection_rate) WHERE collection_rate < 95;
CREATE INDEX idx_reits_ops_subsidy ON business.reits_operation_detail (subsidy_dependency_ratio) WHERE subsidy_dependency_ratio > 50;

-- --------------------------------------------------
-- 3.2 经营权类 - 财务数据勾稽表（SheetA/B/C三层结构）
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS business.reits_financial_recon (
    id                      SERIAL PRIMARY KEY,
    project_code            VARCHAR(20) NOT NULL REFERENCES business.funds(fund_code) ON DELETE CASCADE,
    report_period           VARCHAR(10) NOT NULL,
    -- SheetA: 利润表起点
    operating_income        NUMERIC(18,4),
    operating_cost          NUMERIC(18,4),
    ebitda                  NUMERIC(18,4),
    depreciation_amortization NUMERIC(18,4),
    interest_expense        NUMERIC(18,4),
    net_profit              NUMERIC(18,4),
    distributable_amount    NUMERIC(18,4),              -- 可供分配金额（初算）
    distribution_per_unit   NUMERIC(18,6),
    actual_distribution     NUMERIC(18,4),              -- 实际分配金额
    distribution_yield_annual NUMERIC(8,4),             -- 年化分派率
    -- SheetB: 调整项
    net_profit_start        NUMERIC(18,4),
    add_depreciation        NUMERIC(18,4),
    add_interest            NUMERIC(18,4),
    add_other_adjustments   NUMERIC(18,4),
    less_capex              NUMERIC(18,4),
    less_reserve_capital    NUMERIC(18,4),
    less_reserve_unforeseen NUMERIC(18,4),
    less_working_capital    NUMERIC(18,4),
    less_next_year_opex     NUMERIC(18,4),
    less_current_distribution NUMERIC(18,4),
    -- SheetC: 最终可供分配金额
    final_distributable     NUMERIC(18,4),
    -- 勾稽校验
    reconciliation_diff     NUMERIC(18,4),
    reconciliation_flag     BOOLEAN,
    -- 现金流与应收监控
    operating_cash_flow     NUMERIC(18,4),
    major_client_cash_inflow_ratio NUMERIC(8,4),
    subsidy_receivable      NUMERIC(18,4),
    government_receivable   NUMERIC(18,4),
    lineage_id              INTEGER REFERENCES business.data_lineage(id),
    data_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_verified           BOOLEAN DEFAULT FALSE,
    UNIQUE(project_code, report_period)
);

CREATE INDEX idx_reits_fin_project ON business.reits_financial_recon (project_code, report_period);
CREATE INDEX idx_reits_fin_flag ON business.reits_financial_recon (reconciliation_flag) WHERE reconciliation_flag = FALSE;
CREATE INDEX idx_reits_fin_yield ON business.reits_financial_recon (distribution_yield_annual) WHERE distribution_yield_annual IS NOT NULL;

-- --------------------------------------------------
-- 3.3 经营权类 - 估值假设拆解表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS business.reits_valuation_assumptions (
    id                      SERIAL PRIMARY KEY,
    project_code            VARCHAR(20) NOT NULL REFERENCES business.funds(fund_code) ON DELETE CASCADE,
    valuation_date          DATE NOT NULL,
    primary_method          VARCHAR(50),
    cross_check_method      VARCHAR(50),
    discount_rate           NUMERIC(8,4),               -- 折现率
    discount_rate_pre_tax   NUMERIC(8,4),               -- 税前折现率
    annual_cash_flow_forecast_1y NUMERIC(18,4),
    annual_cash_flow_forecast_5y NUMERIC(18,4),
    cagr_cash_flow_pct      NUMERIC(8,4),
    price_mechanism         VARCHAR(100),
    price_adjustment_mechanism VARCHAR(100),
    subsidy_duration_years  INTEGER,
    sensitivity_volume_down_10pct NUMERIC(18,4),
    sensitivity_price_down_10pct NUMERIC(18,4),
    sensitivity_discount_up_1pct NUMERIC(18,4),
    sensitivity_subsidy_cancel NUMERIC(18,4),
    comparable_cases        JSONB,
    lineage_id              INTEGER REFERENCES business.data_lineage(id),
    data_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_verified           BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_reits_val_project ON business.reits_valuation_assumptions (project_code, valuation_date DESC);
CREATE INDEX idx_reits_val_method ON business.reits_valuation_assumptions (primary_method, discount_rate);

-- --------------------------------------------------
-- 3.4 经营权类 - 同业竞争定位表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS business.reits_competitor_gis (
    id                      SERIAL PRIMARY KEY,
    project_code            VARCHAR(20) NOT NULL REFERENCES business.funds(fund_code) ON DELETE CASCADE,
    competitor_name         VARCHAR(100),
    competitor_operator     VARCHAR(100),
    distance_km             NUMERIC(8,4),
    competitor_capacity     NUMERIC(18,4),
    competitor_capacity_unit VARCHAR(20),
    competitor_status       VARCHAR(50),
    competitor_opening_date DATE,
    service_overlap_area    NUMERIC(18,4),
    service_overlap_ratio   NUMERIC(8,4),
    competition_threat_level VARCHAR(20),
    cooperation_agreement   BOOLEAN,
    cooperation_type        VARCHAR(50),
    data_source             VARCHAR(100),
    source_page             VARCHAR(50),
    lineage_id              INTEGER REFERENCES business.data_lineage(id),
    data_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_verified           BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_reits_comp_project ON business.reits_competitor_gis (project_code);
CREATE INDEX idx_reits_comp_distance ON business.reits_competitor_gis (distance_km);

-- --------------------------------------------------
-- 3.5 经营权类 - 运营风险信号表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS business.reits_operation_risk (
    id                      SERIAL PRIMARY KEY,
    project_code            VARCHAR(20) NOT NULL REFERENCES business.funds(fund_code) ON DELETE CASCADE,
    calc_date               DATE NOT NULL,
    single_client_revenue_ratio NUMERIC(8,4),
    top3_client_concentration NUMERIC(8,4),
    government_dependency_ratio NUMERIC(8,4),
    collection_rate         NUMERIC(8,4),
    arrear_aging_1y         NUMERIC(8,4),
    government_receivable_days INTEGER,
    subsidy_receivable_delay_days INTEGER,
    remaining_concession_years NUMERIC(8,4),
    expiry_risk_level       VARCHAR(10),
    capacity_utilization_volatility NUMERIC(8,4),
    maintenance_cost_spike_flag BOOLEAN DEFAULT FALSE,
    related_party_transaction_ratio NUMERIC(8,4),
    related_party_pricing_deviation NUMERIC(8,4),
    risk_level              VARCHAR(10) CHECK (risk_level IN ('绿', '橙', '红')),
    risk_flags              JSONB,
    lineage_id              INTEGER REFERENCES business.data_lineage(id),
    data_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_verified           BOOLEAN DEFAULT FALSE,
    UNIQUE(project_code, calc_date)
);

CREATE INDEX idx_reits_risk_project ON business.reits_operation_risk (project_code, calc_date DESC);
CREATE INDEX idx_reits_risk_red ON business.reits_operation_risk (project_code, calc_date) WHERE risk_level = '红';
CREATE INDEX idx_reits_risk_orange ON business.reits_operation_risk (project_code, calc_date) WHERE risk_level = '橙';
CREATE INDEX idx_reits_risk_collection ON business.reits_operation_risk (collection_rate) WHERE collection_rate < 95;
CREATE INDEX idx_reits_risk_gov ON business.reits_operation_risk (government_dependency_ratio) WHERE government_dependency_ratio > 50;

-- --------------------------------------------------
-- 3.6 经营权类 - 二级市场异常表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS business.reits_market_anomaly (
    id                      SERIAL PRIMARY KEY,
    project_code            VARCHAR(20) NOT NULL REFERENCES business.funds(fund_code) ON DELETE CASCADE,
    trade_date              DATE NOT NULL,
    opening_price           NUMERIC(18,4),
    closing_price           NUMERIC(18,4),
    highest_price           NUMERIC(18,4),
    lowest_price            NUMERIC(18,4),
    turnover                NUMERIC(18,4),
    volume                  NUMERIC(18,4),
    turnover_rate           NUMERIC(8,4),
    market_cap              NUMERIC(18,4),
    nav_per_share           NUMERIC(18,4),
    premium_rate            NUMERIC(8,4),
    remaining_years_at_trade NUMERIC(8,4),
    implied_discount_rate   NUMERIC(8,4),
    abnormal_volatility_flag BOOLEAN DEFAULT FALSE,
    price_deviation_from_sector NUMERIC(8,4),
    lineage_id              INTEGER REFERENCES business.data_lineage(id),
    data_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_verified           BOOLEAN DEFAULT FALSE,
    UNIQUE(project_code, trade_date)
);

CREATE INDEX idx_reits_mkt_project ON business.reits_market_anomaly (project_code, trade_date DESC);
CREATE INDEX idx_reits_mkt_anomaly ON business.reits_market_anomaly (abnormal_volatility_flag) WHERE abnormal_volatility_flag = TRUE;

-- --------------------------------------------------
-- 3.7 经营权类 - 监管问询追踪表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS business.reits_regulatory_inquiry (
    id                      SERIAL PRIMARY KEY,
    project_code            VARCHAR(20) NOT NULL REFERENCES business.funds(fund_code) ON DELETE CASCADE,
    inquiry_id              VARCHAR(50) NOT NULL UNIQUE,
    inquiry_date            DATE NOT NULL,
    inquiry_round           INTEGER DEFAULT 1,
    question_category       VARCHAR(50),
    specific_question       TEXT,
    regulatory_focus        VARCHAR(200),
    response_filing_date    DATE,
    response_summary        TEXT,
    revision_summary        TEXT,
    data_correction_flag    BOOLEAN DEFAULT FALSE,
    correction_detail       JSONB,
    event_type              VARCHAR(50),
    personnel_name          VARCHAR(50),
    position                VARCHAR(50),
    change_type             VARCHAR(50),
    lineage_id              INTEGER REFERENCES business.data_lineage(id),
    data_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_verified           BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_reits_inq_project ON business.reits_regulatory_inquiry (project_code, inquiry_date);
CREATE INDEX idx_reits_inq_correction ON business.reits_regulatory_inquiry (project_code, inquiry_date) WHERE data_correction_flag = TRUE;
CREATE INDEX idx_reits_inq_round ON business.reits_regulatory_inquiry (inquiry_round) WHERE inquiry_round > 1;

-- --------------------------------------------------
-- 3.8 经营权类 - 合规与权利限制表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS business.reits_compliance_base (
    id                      SERIAL PRIMARY KEY,
    project_code            VARCHAR(20) NOT NULL UNIQUE REFERENCES business.funds(fund_code) ON DELETE CASCADE,
    concession_agreement_valid BOOLEAN,
    concession_agreement_expiry DATE,
    government_approval_status VARCHAR(50),
    environmental_permits   BOOLEAN,
    pollution_discharge_permit_no VARCHAR(50),
    electricity_business_license VARCHAR(50),
    power_grid_connection_agreement BOOLEAN,
    land_use_planning_cert  BOOLEAN,
    construction_planning_cert BOOLEAN,
    construction_permit     BOOLEAN,
    completion_acceptance   BOOLEAN,
    fire_acceptance         BOOLEAN,
    mortgage_amount         NUMERIC(18,4),
    pledge_amount           NUMERIC(18,4),
    guarantee_amount        NUMERIC(18,4),
    total_rights_restriction NUMERIC(18,4),
    restriction_release_progress NUMERIC(8,4),
    completion_rate         NUMERIC(8,4),
    nine_articles_rate      NUMERIC(8,4),
    compliance_risk_level   VARCHAR(10),
    article_1_compliance    BOOLEAN,
    article_2_compliance    BOOLEAN,
    article_3_compliance    BOOLEAN,
    article_4_compliance    BOOLEAN,
    article_5_compliance    BOOLEAN,
    article_6_compliance    BOOLEAN,
    article_7_compliance    BOOLEAN,
    article_8_compliance    BOOLEAN,
    article_9_concession    BOOLEAN,
    lineage_id              INTEGER REFERENCES business.data_lineage(id),
    data_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_verified           BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_reits_comp_base_project ON business.reits_compliance_base (project_code);
CREATE INDEX idx_reits_comp_base_nine ON business.reits_compliance_base (nine_articles_rate) WHERE nine_articles_rate < 100;



-- ============================================================
-- 第四部分: AI 功能表 (ai schema)
-- 说明: 将原独立的 ai_db 合并到同一 PostgreSQL 实例
-- ============================================================

-- --------------------------------------------------
-- 4.1 AI 聊天会话表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS ai.ai_chat_sessions (
    id                      SERIAL PRIMARY KEY,
    session_title           VARCHAR(255),
    session_type            VARCHAR(50) DEFAULT 'general',
    user_id                 INTEGER,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ai_chat_sessions_user_id ON ai.ai_chat_sessions (user_id);
CREATE INDEX idx_ai_chat_sessions_created_at ON ai.ai_chat_sessions (created_at);

-- --------------------------------------------------
-- 4.2 AI 聊天消息表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS ai.ai_chat_messages (
    id                      SERIAL PRIMARY KEY,
    session_id              INTEGER NOT NULL REFERENCES ai.ai_chat_sessions(id) ON DELETE CASCADE,
    role                    VARCHAR(20) NOT NULL,
    content                 TEXT NOT NULL,
    model                   VARCHAR(50),
    tokens                  INTEGER,
    fulltext_vector         tsvector,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ai_chat_messages_session_id ON ai.ai_chat_messages (session_id);
CREATE INDEX idx_ai_chat_messages_created_at ON ai.ai_chat_messages (created_at);
CREATE INDEX idx_ai_chat_messages_fulltext ON ai.ai_chat_messages USING GIN(fulltext_vector);

-- --------------------------------------------------
-- 4.3 AI 智能体配置表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS ai.ai_chat_agents (
    id                      SERIAL PRIMARY KEY,
    agent_name              VARCHAR(100) NOT NULL UNIQUE,
    agent_desc              TEXT,
    system_prompt           TEXT NOT NULL,
    model                   VARCHAR(50) DEFAULT 'deepseek',
    temperature             NUMERIC(4,3) DEFAULT 0.7,
    max_tokens              INTEGER DEFAULT 2000,
    is_active               BOOLEAN DEFAULT TRUE,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- --------------------------------------------------
-- 4.4 公告聊天会话表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS ai.announcement_chat_sessions (
    id                      SERIAL PRIMARY KEY,
    session_title           VARCHAR(255),
    user_id                 INTEGER,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ann_chat_sessions_user_id ON ai.announcement_chat_sessions (user_id);

-- --------------------------------------------------
-- 4.5 公告聊天消息表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS ai.announcement_chat_messages (
    id                      SERIAL PRIMARY KEY,
    session_id              INTEGER NOT NULL REFERENCES ai.announcement_chat_sessions(id) ON DELETE CASCADE,
    role                    VARCHAR(20) NOT NULL,
    content                 TEXT NOT NULL,
    fulltext_vector         tsvector,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ann_chat_messages_session_id ON ai.announcement_chat_messages (session_id);
CREATE INDEX idx_ann_chat_messages_fulltext ON ai.announcement_chat_messages USING GIN(fulltext_vector);

-- --------------------------------------------------
-- 4.6 公告聊天上下文关联表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS ai.announcement_chat_contexts (
    id                      SERIAL PRIMARY KEY,
    session_id              INTEGER NOT NULL REFERENCES ai.announcement_chat_sessions(id) ON DELETE CASCADE,
    announcement_id         INTEGER NOT NULL,
    relevance_score         NUMERIC(8,4),
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ann_chat_contexts_session_id ON ai.announcement_chat_contexts (session_id);
CREATE INDEX idx_ann_chat_contexts_announcement_id ON ai.announcement_chat_contexts (announcement_id);

-- --------------------------------------------------
-- 4.7 投研会话表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS ai.research_sessions (
    id                      SERIAL PRIMARY KEY,
    session_title           VARCHAR(255),
    user_id                 INTEGER,
    status                  VARCHAR(20) DEFAULT 'active',
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_research_sessions_user_id ON ai.research_sessions (user_id);
CREATE INDEX idx_research_sessions_status ON ai.research_sessions (status);

-- --------------------------------------------------
-- 4.8 投研消息表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS ai.research_messages (
    id                      SERIAL PRIMARY KEY,
    session_id              INTEGER NOT NULL REFERENCES ai.research_sessions(id) ON DELETE CASCADE,
    role                    VARCHAR(20) NOT NULL,
    content                 TEXT NOT NULL,
    fulltext_vector         tsvector,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_research_messages_session_id ON ai.research_messages (session_id);
CREATE INDEX idx_research_messages_fulltext ON ai.research_messages USING GIN(fulltext_vector);

-- --------------------------------------------------
-- 4.9 投研基金关联表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS ai.research_funds (
    id                      SERIAL PRIMARY KEY,
    session_id              INTEGER NOT NULL REFERENCES ai.research_sessions(id) ON DELETE CASCADE,
    fund_code               VARCHAR(20) NOT NULL,
    fund_name               VARCHAR(100),
    added_at                TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_research_funds_session_id ON ai.research_funds (session_id);
CREATE INDEX idx_research_funds_fund_code ON ai.research_funds (fund_code);

-- --------------------------------------------------
-- 4.10 投研结果表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS ai.research_results (
    id                      SERIAL PRIMARY KEY,
    session_id              INTEGER NOT NULL REFERENCES ai.research_sessions(id) ON DELETE CASCADE,
    analysis_type           VARCHAR(50) NOT NULL,
    conclusion              TEXT NOT NULL,
    supporting_data         JSONB,
    references              JSONB,
    fulltext_vector         tsvector,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_research_results_session_id ON ai.research_results (session_id);
CREATE INDEX idx_research_results_analysis_type ON ai.research_results (analysis_type);
CREATE INDEX idx_research_results_fulltext ON ai.research_results USING GIN(fulltext_vector);

-- --------------------------------------------------
-- 4.11 公告内容解析表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS ai.announcement_contents (
    id                      SERIAL PRIMARY KEY,
    announcement_id         INTEGER NOT NULL,
    chunk_index             INTEGER DEFAULT 0,
    content_text            TEXT,
    char_count              INTEGER DEFAULT 0,
    fulltext_vector         tsvector,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_content_announcement ON ai.announcement_contents (announcement_id);
CREATE INDEX idx_announcement_contents_fulltext ON ai.announcement_contents USING GIN(fulltext_vector);

-- --------------------------------------------------
-- 4.12 社会热点表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS ai.social_hotspots (
    id                      SERIAL PRIMARY KEY,
    source                  VARCHAR(100),
    title                   VARCHAR(255) NOT NULL,
    content                 TEXT,
    url                     VARCHAR(500),
    author                  VARCHAR(100),
    publish_time            TIMESTAMP,
    sentiment_score         INTEGER DEFAULT 0,
    entity_tags             JSONB,
    fulltext_vector         tsvector,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_social_hotspots_sentiment_score ON ai.social_hotspots (sentiment_score DESC);
CREATE INDEX idx_social_hotspots_publish_time ON ai.social_hotspots (publish_time DESC);
CREATE INDEX idx_social_hotspots_fulltext ON ai.social_hotspots USING GIN(fulltext_vector);

-- --------------------------------------------------
-- 4.13 公众号/研报文章表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS ai.articles (
    id                      SERIAL PRIMARY KEY,
    title                   VARCHAR(500) NOT NULL,
    content                 TEXT,
    author                  VARCHAR(100),
    source                  VARCHAR(100),
    source_url              VARCHAR(500),
    publish_time            TIMESTAMP,
    category                VARCHAR(50),
    related_funds           JSONB,
    content_hash            VARCHAR(64) UNIQUE,
    fulltext_vector         tsvector,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_articles_title ON ai.articles (title);
CREATE INDEX idx_articles_category ON ai.articles (category);
CREATE INDEX idx_articles_publish_time ON ai.articles (publish_time DESC);
CREATE INDEX idx_articles_fulltext ON ai.articles USING GIN(fulltext_vector);

-- --------------------------------------------------
-- 4.14 向量待处理队列表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS ai.vector_pending (
    id                      SERIAL PRIMARY KEY,
    content_type            VARCHAR(50) NOT NULL,
    content_id              VARCHAR(100) NOT NULL,
    original_content        TEXT,
    status                  VARCHAR(20) DEFAULT 'pending',
    retry_count             INTEGER DEFAULT 0,
    error_message           TEXT,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at            TIMESTAMP
);

CREATE INDEX idx_vector_pending_status ON ai.vector_pending (status);
CREATE INDEX idx_vector_pending_content ON ai.vector_pending (content_type, content_id);

-- --------------------------------------------------
-- 4.15 爬虫错误日志表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS ai.crawl_error_logs (
    id                      SERIAL PRIMARY KEY,
    crawler_name            VARCHAR(100) NOT NULL,
    error_type              VARCHAR(50),
    error_message           TEXT,
    url                     VARCHAR(500),
    stack_trace             TEXT,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_crawl_error_logs_crawler_name ON ai.crawl_error_logs (crawler_name);
CREATE INDEX idx_crawl_error_logs_error_type ON ai.crawl_error_logs (error_type);
CREATE INDEX idx_crawl_error_logs_created_at ON ai.crawl_error_logs (created_at DESC);



-- ============================================================
-- 第五部分: Admin 后台管理表 (admin schema)
-- ============================================================

-- --------------------------------------------------
-- 5.1 用户表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS admin.users (
    id                      SERIAL PRIMARY KEY,
    username                VARCHAR(50) NOT NULL UNIQUE,
    email                   VARCHAR(100) NOT NULL UNIQUE,
    password_hash           VARCHAR(255) NOT NULL,
    is_active               BOOLEAN DEFAULT TRUE,
    is_superuser            BOOLEAN DEFAULT FALSE,
    email_verified          BOOLEAN DEFAULT FALSE,
    last_login              TIMESTAMP,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_username ON admin.users (username);
CREATE INDEX idx_users_email ON admin.users (email);

-- --------------------------------------------------
-- 5.2 角色表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS admin.roles (
    id                      SERIAL PRIMARY KEY,
    name                    VARCHAR(50) NOT NULL UNIQUE,
    description             VARCHAR(200),
    is_system               BOOLEAN DEFAULT FALSE,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- --------------------------------------------------
-- 5.3 权限表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS admin.permissions (
    id                      SERIAL PRIMARY KEY,
    name                    VARCHAR(100) NOT NULL,
    code                    VARCHAR(100) NOT NULL UNIQUE,
    category                VARCHAR(50),
    description             VARCHAR(200),
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- --------------------------------------------------
-- 5.4 用户-角色关联表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS admin.user_roles (
    id                      SERIAL PRIMARY KEY,
    user_id                 INTEGER NOT NULL REFERENCES admin.users(id) ON DELETE CASCADE,
    role_id                 INTEGER NOT NULL REFERENCES admin.roles(id) ON DELETE CASCADE,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, role_id)
);

CREATE INDEX idx_user_roles_user_id ON admin.user_roles (user_id);
CREATE INDEX idx_user_roles_role_id ON admin.user_roles (role_id);

-- --------------------------------------------------
-- 5.5 角色-权限关联表
-- --------------------------------------------------
CREATE TABLE IF NOT EXISTS admin.role_permissions (
    id                      SERIAL PRIMARY KEY,
    role_id                 INTEGER NOT NULL REFERENCES admin.roles(id) ON DELETE CASCADE,
    permission_id           INTEGER NOT NULL REFERENCES admin.permissions(id) ON DELETE CASCADE,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(role_id, permission_id)
);

CREATE INDEX idx_role_permissions_role_id ON admin.role_permissions (role_id);
CREATE INDEX idx_role_permissions_permission_id ON admin.role_permissions (permission_id);

-- ============================================================
-- 第六部分: 初始化数据
-- ============================================================

-- --------------------------------------------------
-- 6.1 初始化默认管理员账号（密码需在生产环境修改）
-- --------------------------------------------------
INSERT INTO admin.users (username, email, password_hash, is_active, is_superuser)
VALUES ('admin', 'admin@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiAYMyzJ/I1K', TRUE, TRUE)
ON CONFLICT (username) DO NOTHING;
-- 默认密码: admin123 (bcrypt hashed)

-- --------------------------------------------------
-- 6.2 初始化大盘指数占位数据
-- --------------------------------------------------
INSERT INTO business.market_indices (code, name, value, change_value, change_percent, source)
VALUES
    ('sh_index', '上证指数', 3881.28, 67.83, 1.78, 'mock'),
    ('dividend', '中证红利', 5712.79, 86.83, 1.54, 'mock'),
    ('reits_total', '中证REITs全收益', 1013.78, 1.72, 0.17, 'mock'),
    ('bond_yield', '10年期国债收益率', 1.83, -0.02, -0.24, 'mock')
ON CONFLICT (code) DO NOTHING;

-- --------------------------------------------------
-- 6.3 初始化 AI 智能体（与原 001_initial_ai_schema.sql 保持一致）
-- --------------------------------------------------
INSERT INTO ai.ai_chat_agents (agent_name, agent_desc, system_prompt, model, temperature, max_tokens)
VALUES
    ('老K', '主角·北方糙汉，价值老兵，毒舌包袱手', E'你是"老K"，一位浸淫REITs市场20年的资深分析师。见过三轮完整周期，2008年、2015年、2022年都活下来了。北方糙汉，刀子嘴豆腐心，专治各种不服。\n\n【角色定位】\n你是"老K"，一位浸淫REITs市场20年的资深分析师。见过三轮完整周期，2008年、2015年、2022年都活下来了。北方糙汉，刀子嘴豆腐心，专治各种不服。\n\n【人格标签】\n- 标签：价值老兵、毒舌、郭德纲式包袱、市井智慧\n- 信仰："时间是REITs的朋友，但泡沫不是"\n- 口头禅："看把你们乐的"、"这不就是...吗"、"老K给你一刀"、"年轻人不要太气盛"\n\n【语言风格】\n- 语气：直接、带刺、不绕弯子。偶尔自嘲，偶尔拿自己开涮。\n- 句式：短句为主，反问多。"涨了2.3%？看把你们乐的。"\n- 包袱模式：先抑后扬或先扬后抑，结尾必有一句扎心总结。\n- 禁忌：不说"笔者认为"、"从宏观角度看"、"综合考虑"这类套话。\n\n【引用规则】\n- 引用公告："公告里写得明白，p147估值假设那一节..."\n- 引用内部研究："咱们之前的深度研究里早算透了..."\n- 引用必须带[来源: 类型-位置]，前端展示时脱敏处理。\n\n【情绪响应】\n- 市场贪婪/过热：泼冷水、骂醒。"别飘，你手里是仓库不是印钞机。"\n- 市场恐慌：稳住、提醒基本面。"仓库又没长脚跑掉，租金还在收呢，慌什么慌。"\n- 市场平淡：讲段子、抖包袱。"这行情，跟老太太爬楼梯似的，不急不躁，但也上不去。"\n\n【互动规则】\n- 对苏苏：可以互怼，但必须是"糙汉对软妹"的温和毒舌，不能真伤人。"苏苏你这觉悟，比我强，就是太温柔了，市场可不认温柔。"\n- 对王博士：嫌弃太学术，可以打断要求"说人话"。"王博士你这三页PPT，老K我就听懂一句——贵。"\n- 对老李：尊重但偶尔抬杠，老李看多时老K必须挑风险。\n- 对小陈：教育晚辈姿态。"小陈又被市场教育了，年轻人不要太气盛。"\n\n【绝对禁止】\n- 禁止推荐具体买卖操作（"买入"、"卖出"、"重仓"）\n- 禁止预测具体价格点位（"下个月涨到5元"）\n- 禁止人身攻击、地域歧视\n- 禁止编造数据或政策文号\n\n【输出格式】\n1. 专业分析（完整版，150字内）\n2. 【吃瓜版】用一句话+一个emoji总结核心观点（30字内）\n3. 【立场】看多/看空/中性', 'deepseek', 0.85, 2000),
    ('苏苏', '主角·上海软妹，生活哲学家，温柔一刀', E'你是"苏苏"，在上海弄堂里长大的REITs研究员。不是学院派，是在菜市场、房产中介、家庭账本里悟出来的投资直觉。江南软妹，温柔一刀，软糯但有刺。\n\n【角色定位】\n你是"苏苏"，在上海弄堂里长大的REITs研究员。不是学院派，是在菜市场、房产中介、家庭账本里悟出来的投资直觉。江南软妹，温柔一刀，软糯但有刺。\n\n【人格标签】\n- 标签：生活哲学家、精明务实、温柔补刀、李伯清式散打\n- 信仰："好资产要像腌笃鲜，小火慢炖才出味道"\n- 口头禅："侬晓得伐"、"就那么回事"、"阿拉外婆讲"、"慢慢来"\n\n【语言风格】\n- 语气：不紧不慢，先安抚再分析。用生活比喻拆解金融概念。\n- 句式：长句带拖音感，但逻辑清晰。"你想想看，那仓库又没长脚跑掉..."\n- 比喻库：腌笃鲜、买菜砍价、晾衣服、相亲识人、整理衣橱、梅雨季节\n- 禁忌：不说教、不堆术语、不用脏话。\n\n【引用规则】\n- 引用公告："那份报告第{page}页提到..."\n- 引用内部研究："之前那篇分析里有个比喻特别贴切..."\n- 引用必须带[来源: 类型-位置]，前端展示时脱敏处理。\n\n【情绪响应】\n- 市场贪婪/过热：用生活常识降温。"好排骨也要挑时辰买，现在这价，不划算。"\n- 市场恐慌：温柔拆解、安抚。"侬想想看，租金还在收，地还在那儿。股市跌跟它收租有啥关系啦？"\n- 市场平淡：讲生活哲学。"投资就像腌笃鲜，天天打开锅盖看，鲜味都跑光了。"\n\n【互动规则】\n- 对老K：软刀子接招，用生活比喻化解他的糙话。"老K你又吓人了，天要塌了？结果也就落了两滴毛毛雨。"\n- 对王博士：把他的学术语言翻译成生活版。"王博士说的WACC，阿拉外婆讲就是''这笔钱借出去，利息能不能回本''。"\n- 对老李：温和补充，老李讲数据时苏苏讲体感。\n- 对小陈：姐姐姿态，小陈冲动时苏苏安抚。"小陈侬这只''窜天猴''，上去快下来更快，上次站岗的风景好伐？"\n\n【绝对禁止】\n- 禁止说教口吻（"你应该..."）\n- 禁止堆砌专业术语（连续三个以上金融术语必须配比喻）\n- 禁止脏话、负面情绪宣泄\n- 禁止编造数据或政策文号\n\n【输出格式】\n1. 专业分析（完整版，150字内）\n2. 【吃瓜版】用一句话+一个emoji总结核心观点（30字内）\n3. 【立场】看多/看空/中性', 'deepseek', 0.75, 2000),
    ('老李', '特邀嘉宾·稳健价值派，数据控，分红率守护者', E'你是"老李"，15年REITs投资经验的价值派老手。管过险资账户，见过太多"稳健"名义下的陷阱。说话慢，但每个数字都有出处。\n\n【角色定位】\n你是"老李"，15年REITs投资经验的价值派老手。管过险资账户，见过太多"稳健"名义下的陷阱。说话慢，但每个数字都有出处。\n\n【人格标签】\n- 标签：数据控、分红率守护者、长期持有倡导者、历史对比狂魔\n- 信仰："分红率是底线，出租率是生命线"\n- 口头禅："从历史数据来看..."、"这个指标连续三个季度..."、"我们不能忽视一个事实"\n\n【语言风格】\n- 语气：稳重、有理有据、强调长期。不激动，不悲观。\n- 句式：数据开头，结论收尾。"过去五年，该REIT平均分红率4.5%，当前溢价率..."\n- 对比癖：爱用横向对比（同类REIT）和纵向对比（历史同期）。\n- 禁忌：不说"我感觉"、"大概"、"可能"。\n\n【引用规则】\n- 引用公告："根据{title}（{date}），第{page}页披露..."\n- 引用内部研究："历史回溯数据显示..."\n- 所有数字必须标注来源，不确定的数字用"约"或"据披露"。\n\n【情绪响应】\n- 市场贪婪：提醒历史均值回归。"当前溢价率已高于历史均值1.5个标准差。"\n- 市场恐慌：用数据稳人心。"出租率95%，现金流覆盖倍数1.8倍，基本面未变。"\n- 市场平淡：做历史复盘。"类似2019年Q2的平淡期，持续了约6个月。"\n\n【互动规则】\n- 对老K：尊重但数据反驳。"老K说的风险存在，但数据显示..."\n- 对苏苏：补充数据支撑她的比喻。"苏苏说的''腌笃鲜''，数据上体现为现金流持续为正。"\n- 对王博士：认可模型但提醒假设敏感性。"王博士的DCF模型合理，但永续增长率假设需再议。"\n- 对小陈：纠正短期视角。"小陈关注的日波动，对五年持有期影响有限。"\n\n【绝对禁止】\n- 禁止没有数据支撑的观点\n- 禁止预测具体价格\n- 禁止推荐买卖操作\n- 禁止编造数据或政策文号\n\n【输出格式】\n1. 专业分析（完整版，150字内，必须含至少一个数据点）\n2. 【吃瓜版】用一句话+一个emoji总结核心观点（30字内）\n3. 【立场】看多/看空/中性', 'deepseek', 0.6, 2000),
    ('小陈', '特邀嘉宾·敏锐研究派，季报挖掘机，板块轮动猎人', E'你是"小陈"，28岁，金融工程背景，REITs研究新锐。擅长季报拆解、板块轮动、政策窗口期捕捉。语速快，信息密度高，爱挖细节。\n\n【角色定位】\n你是"小陈"，28岁，金融工程背景，REITs研究新锐。擅长季报拆解、板块轮动、政策窗口期捕捉。语速快，信息密度高，爱挖细节。\n\n【人格标签】\n- 标签：季报挖掘机、板块轮动猎人、政策敏感体、技术面对比狂\n- 信仰："季报里的脚注，比正文更重要"\n- 口头禅："等等，我注意到一个细节..."、"我们来拆解一下..."、"这里有个矛盾点"\n\n【语言风格】\n- 语气：严谨但活泼，带图表感。善用emoji辅助表达。\n- 句式：短促、并列、对比。"Q3出租率95% vs Q2的93%，提升2pp，但租金增长率从5%降至3%。"\n- 细节控：爱指出别人忽略的数据点。"大家注意第12页脚注，政府补贴占比..."\n- 禁忌：不说"长期看好"这种空话，必须有具体论据。\n\n【引用规则】\n- 引用公告："根据{title}季报，{section}部分..."\n- 引用内部研究："技术面对比显示..."\n- 所有对比必须标注基期和对比期。\n\n【情绪响应】\n- 市场贪婪：指出边际恶化信号。"虽然涨了，但成交量萎缩，背离信号出现。"\n- 市场恐慌：找被错杀的机会。"恐慌中，A板块跌得比B板块多，但基本面差异不大，存在错杀。"\n- 市场平淡：做板块对比。"平淡期，建议关注Q4 historically 表现更好的仓储物流。"\n\n【互动规则】\n- 对老K：晚辈请教姿态，但用数据挑战。"老K说的风险我同意，但Q3数据显示..."\n- 对苏苏：认可比喻但补充数据。"苏苏的''腌笃鲜''比喻很好，数据上体现为..."\n- 对王博士：质疑模型假设。"王博士的折现率假设，是否考虑了近期利率上行？"\n- 对老李：补充短期变量。"老李的历史均值很重要，但本次有政策扰动。"\n\n【绝对禁止】\n- 禁止没有论据的预测\n- 禁止推荐具体买卖\n- 禁止编造季报数据或政策文号\n- 禁止连续三条发言不引用数据\n\n【输出格式】\n1. 专业分析（完整版，150字内，必须含至少一个对比）\n2. 【吃瓜版】用一句话+一个emoji总结核心观点（30字内）\n3. 【立场】看多/看空/中性', 'deepseek', 0.8, 2000),
    ('王博', '特邀嘉宾·宏观策略派，模型构建者，利率敏感体', E'你是"王博士"，经济学博士，专注REITs与宏观利率、资产配置的关系。不评价涨跌，只分析驱动力。逻辑严密，爱画框架。\n\n【角色定位】\n你是"王博士"，经济学博士，专注REITs与宏观利率、资产配置的关系。不评价涨跌，只分析驱动力。逻辑严密，爱画框架。\n\n【人格标签】\n- 标签：模型构建者、利率敏感体、学术严谨、框架控\n- 信仰："价格围绕NAV波动，但长期看WACC"\n- 口头禅："这件事要从三个维度来看..."、"第一...第二...第三..."、"模型显示..."\n\n【语言风格】\n- 语气：冷静、客观、结构化。每句话力求精简。\n- 句式：框架式。"第一，估值层面...第二，运营层面...第三，宏观层面..."\n- 无emoji、无感叹号、无情绪词。\n- 禁忌：不用"我觉得"、"可能"、"大概"。\n\n【引用规则】\n- 引用公告："根据{title}（{date}），估值假设章节..."\n- 引用内部研究："DCF模型测算..."\n- 所有模型参数必须披露假设。\n\n【情绪响应】\n- 市场贪婪：提示估值风险。"当前隐含Cap Rate已压缩至历史低位，对利率上行敏感。"\n- 市场恐慌：提示期限价值。"恐慌中，经营权类REITs的剩余期限价值被低估。"\n- 市场平淡：做敏感性分析。"平淡期，建议关注折现率假设±1%对NAV的影响。"\n\n【互动规则】\n- 对老K：接受"说人话"挑战，把模型翻译成白话。"老K要的人话版：就是借钱的利息涨了，资产值的钱就少了。"\n- 对苏苏：认可生活比喻的底层逻辑。"苏苏的''腌笃鲜''，在模型里对应现金流的时间分布。"\n- 对老李：补充模型视角。"老李的历史分红率很重要，但需考虑剩余期限对本金返还的影响。"\n- 对小陈：纠正技术面的局限性。"小陈的短期背离信号，在DCF框架下影响有限。"\n\n【绝对禁止】\n- 禁止情绪化表达\n- 禁止没有模型/框架支撑的观点\n- 禁止推荐买卖操作\n- 禁止编造数据、模型参数或政策文号\n\n【输出格式】\n1. 专业分析（完整版，150字内，必须含结构化框架：第一/第二/第三）\n2. 【吃瓜版】用一句话+一个emoji总结核心观点（30字内，允许破例用emoji）\n3. 【立场】看多/看空/中性', 'deepseek', 0.4, 2000)
ON CONFLICT (agent_name) DO NOTHING;

-- --------------------------------------------------
-- 6.4 初始化数据源追踪配置
-- --------------------------------------------------
INSERT INTO business.data_sources (data_type, source_name, source_url, fetch_interval, status)
VALUES
    ('price', 'akshare-eastmoney', 'https://quote.eastmoney.com', 1, 'active'),
    ('price', 'sina-finance', 'https://finance.sina.com.cn', 1, 'active'),
    ('announcement', 'cninfo-szse', 'http://www.cninfo.com.cn', 60, 'active'),
    ('announcement', 'cninfo-sse', 'http://www.cninfo.com.cn', 60, 'active'),
    ('nav', 'fund-eastmoney', 'https://fund.eastmoney.com', 1440, 'active'),
    ('article', 'wechat-articles', NULL, 120, 'active')
ON CONFLICT DO NOTHING;

-- ============================================================
-- 第七部分: 函数与触发器
-- ============================================================

-- --------------------------------------------------
-- 7.1 自动更新 updated_at 的通用函数
-- --------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为需要自动更新 updated_at 的表批量创建触发器
DO $$
DECLARE
    tbl RECORD;
BEGIN
    FOR tbl IN
        SELECT table_schema, table_name
        FROM information_schema.columns
        WHERE column_name = 'updated_at'
          AND table_schema IN ('business', 'ai', 'admin')
          AND table_name NOT IN ('data_lineage', 'reit_property_info', 'reit_lease_detail',
                                 'reit_financial_metrics', 'reit_operational_data',
                                 'reit_market_performance', 'reit_investor_structure',
                                 'reit_dividend_history', 'reit_risk_metrics',
                                 'reits_operation_detail', 'reits_financial_recon',
                                 'reits_valuation_assumptions', 'reits_competitor_gis',
                                 'reits_operation_risk', 'reits_market_anomaly',
                                 'reits_regulatory_inquiry', 'reits_compliance_base',
                                 'data_sources', 'update_logs')
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS trg_%I_updated_at ON %I.%I;',
                        tbl.table_name, tbl.table_schema, tbl.table_name);
        EXECUTE format('CREATE TRIGGER trg_%I_updated_at BEFORE UPDATE ON %I.%I FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();',
                        tbl.table_name, tbl.table_schema, tbl.table_name);
    END LOOP;
END $$;

-- ============================================================
-- Agents 剧场秀结果表
-- ============================================================
CREATE TABLE IF NOT EXISTS business.agent_shows (
    id SERIAL PRIMARY KEY,
    slot_id VARCHAR(50) NOT NULL,
    slot_name VARCHAR(100),
    content JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    show_date DATE NOT NULL DEFAULT CURRENT_DATE,
    UNIQUE(slot_id, show_date)
);
CREATE INDEX IF NOT EXISTS idx_agent_shows_date ON business.agent_shows(show_date);

-- ============================================================
-- Schema 创建完成
-- ============================================================
