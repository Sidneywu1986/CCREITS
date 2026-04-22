-- ============================================================
-- RSDS v1.1.2 SQLite 对齐版 DDL
-- 产权类 8+1 张表 + 经营权类 9+1 张表
-- 特性：SQLite 兼容（替代 JSONB->TEXT, SERIAL->AUTOINCREMENT）
-- ============================================================

-- ============================================================
-- 第一部分：产权类 REITs（Property REITs）
-- ============================================================

-- 表0：数据血缘追踪表（两类共用）
CREATE TABLE IF NOT EXISTS data_lineage (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name          VARCHAR(50) NOT NULL,
    record_id           VARCHAR(50) NOT NULL,
    project_code        VARCHAR(20) NOT NULL,
    agent_name          VARCHAR(50),
    source_type         VARCHAR(20),
    source_document     VARCHAR(200),
    source_url          VARCHAR(500) NOT NULL,
    source_page         INTEGER,
    extracted_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confidence_score    REAL CHECK (confidence_score BETWEEN 0 AND 1),
    raw_snapshot        TEXT,
    operator_id         VARCHAR(50),
    data_verified       INTEGER DEFAULT 0 CHECK (data_verified IN (0,1))
);

CREATE INDEX IF NOT EXISTS idx_lineage_project ON data_lineage (project_code, extracted_at);
CREATE INDEX IF NOT EXISTS idx_lineage_source ON data_lineage (source_url);
CREATE INDEX IF NOT EXISTS idx_lineage_unverified ON data_lineage (data_verified) WHERE data_verified = 0;

-- 表1：产品信息表（产权类）
CREATE TABLE IF NOT EXISTS reit_product_info (
    fund_code               VARCHAR(20) PRIMARY KEY,
    fund_name               VARCHAR(200) NOT NULL,
    fund_short_name         VARCHAR(100),
    fund_type               VARCHAR(20) NOT NULL DEFAULT '产权类' CHECK (fund_type IN ('产权类', '经营权类')),
    asset_type              VARCHAR(50),                -- 产业园/仓储物流/保障性租赁住房/购物中心等
    manager_name            VARCHAR(100) NOT NULL,      -- 基金管理人
    custodian_name          VARCHAR(100),               -- 基金托管人
    operating_manager       VARCHAR(200),               -- 运营管理机构
    issue_date              DATE,                       -- 发行日期
    listing_date            DATE,                       -- 上市日期
    issue_price             REAL,                       -- 发行价/元
    issue_amount            REAL,                       -- 发行规模/亿元
    fund_shares             REAL,                       -- 基金份额/亿份
    management_fee_rate     REAL,                       -- 管理费率
    custody_fee_rate        REAL,                       -- 托管费率
    investment_scope        TEXT,                       -- 投资范围
    lineage_id              INTEGER REFERENCES data_lineage(id),
    data_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_verified           INTEGER DEFAULT 0 CHECK (data_verified IN (0,1))
);

CREATE INDEX IF NOT EXISTS idx_product_asset_type ON reit_product_info (asset_type);
CREATE INDEX IF NOT EXISTS idx_product_manager ON reit_product_info (manager_name);
CREATE INDEX IF NOT EXISTS idx_product_listing ON reit_product_info (listing_date);

-- 表2：资产信息表（产权类）
CREATE TABLE IF NOT EXISTS reit_property_info (
    property_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_code               VARCHAR(20) NOT NULL REFERENCES reit_product_info(fund_code),
    property_name           VARCHAR(200),               -- 项目名称
    city                    VARCHAR(50),                -- 城市
    district                VARCHAR(50),                -- 区县
    address                 VARCHAR(500),               -- 详细地址
    property_type           VARCHAR(50),                -- 办公楼/商业综合体/产业园/仓储物流等
    building_area           REAL,                       -- 建筑面积/㎡
    leasable_area           REAL,                       -- 可出租面积/㎡
    valuation_date          DATE,                       -- 评估基准日
    appraised_value         REAL,                       -- 评估价值/万元
    value_per_sqm           REAL,                       -- 单价/元/㎡
    tenant_count            INTEGER,                    -- 租户数量
    occupancy_rate          REAL CHECK (occupancy_rate BETWEEN 0 AND 100), -- 出租率%
    average_rent            REAL,                       -- 平均租金/元/㎡/月
    weighted_lease_term     REAL,                       -- 加权平均租期/年
    expiration_date         DATE,                       -- 数据有效期
    lineage_id              INTEGER REFERENCES data_lineage(id),
    data_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_verified           INTEGER DEFAULT 0 CHECK (data_verified IN (0,1))
);

CREATE INDEX IF NOT EXISTS idx_property_fund ON reit_property_info (fund_code);
CREATE INDEX IF NOT EXISTS idx_property_city ON reit_property_info (city);
CREATE INDEX IF NOT EXISTS idx_property_type ON reit_property_info (property_type);

-- 表2.5：租约明细表（产权类）
CREATE TABLE IF NOT EXISTS reit_lease_detail (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_code               VARCHAR(20) NOT NULL REFERENCES reit_product_info(fund_code),
    lease_id                VARCHAR(50) NOT NULL,
    tenant_name             VARCHAR(100) NOT NULL,
    industry_gics           VARCHAR(20),
    tenant_credit_rating    VARCHAR(10),
    lease_area_sqm          REAL,
    area_ratio_pct          REAL CHECK (area_ratio_pct BETWEEN 0 AND 100),
    rent_per_sqm            REAL,
    market_rent_per_sqm     REAL,
    rent_discount_pct       REAL,                       -- 租金折扣率%，<-15% 触发利益输送标记
    lease_start             DATE,
    lease_end               DATE,
    remaining_months        INTEGER,
    expiry_year             INTEGER,
    rent_free_months        INTEGER,
    is_related_party        INTEGER DEFAULT 0 CHECK (is_related_party IN (0,1)),
    related_party_name      VARCHAR(100),
    renewal_option          VARCHAR(50),
    deposit_months          INTEGER,
    effective_date          DATE DEFAULT CURRENT_DATE,
    expiration_date         DATE DEFAULT '9999-12-31',
    lineage_id              INTEGER REFERENCES data_lineage(id),
    data_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(fund_code, lease_id)
);

CREATE INDEX IF NOT EXISTS idx_lease_fund_expiry ON reit_lease_detail (fund_code, expiry_year);
CREATE INDEX IF NOT EXISTS idx_lease_related_discount ON reit_lease_detail (fund_code, rent_discount_pct) WHERE is_related_party = 1;
CREATE INDEX IF NOT EXISTS idx_lease_current ON reit_lease_detail (fund_code, effective_date, expiration_date) WHERE expiration_date = '9999-12-31';
CREATE INDEX IF NOT EXISTS idx_lease_2026 ON reit_lease_detail (fund_code, area_ratio_pct) WHERE expiry_year = 2026;

-- 表3：财务指标表（产权类）
CREATE TABLE IF NOT EXISTS reit_financial_metrics (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_code               VARCHAR(20) NOT NULL REFERENCES reit_product_info(fund_code),
    report_period           VARCHAR(10) NOT NULL,       -- 如2024Q3
    total_revenue           REAL,                       -- 营业总收入/万元
    operating_revenue       REAL,                       -- 运营收入/万元
    net_profit              REAL,                       -- 净利润/万元
    total_assets            REAL,                       -- 总资产/万元
    net_assets              REAL,                       -- 净资产/万元
    fund_nav_per_share      REAL,                       -- 基金净值/元/份
    distributeable_amount   REAL,                       -- 可供分配金额/万元
    distribution_per_share  REAL,                       -- 每份可供分配金额/元
    lineage_id              INTEGER REFERENCES data_lineage(id),
    data_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_verified           INTEGER DEFAULT 0 CHECK (data_verified IN (0,1)),
    UNIQUE(fund_code, report_period)
);

CREATE INDEX IF NOT EXISTS idx_fin_fund_period ON reit_financial_metrics (fund_code, report_period);
CREATE INDEX IF NOT EXISTS idx_fin_distributable ON reit_financial_metrics (distributeable_amount) WHERE distributeable_amount IS NOT NULL;

-- 表4：运营数据表（产权类）
CREATE TABLE IF NOT EXISTS reit_operational_data (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_code               VARCHAR(20) NOT NULL REFERENCES reit_product_info(fund_code),
    report_period           VARCHAR(10) NOT NULL,
    occupancy_rate          REAL CHECK (occupancy_rate BETWEEN 0 AND 100), -- 整体出租率%
    cap_rate                REAL,                       -- 资本化率%
    average_rent            REAL,                       -- 平均租金/元/㎡/月
    rent_growth_rate        REAL,                       -- 租金增长率%
    operating_expense       REAL,                       -- 运营成本/万元
    expense_ratio           REAL CHECK (expense_ratio BETWEEN 0 AND 100), -- 费用率%
    top_ten_tenant_concentration REAL CHECK (top_ten_tenant_concentration BETWEEN 0 AND 100), -- 前十大租户集中度%
    tenant_turnover_rate    REAL,                       -- 租户更替率%
    lineage_id              INTEGER REFERENCES data_lineage(id),
    data_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_verified           INTEGER DEFAULT 0 CHECK (data_verified IN (0,1)),
    UNIQUE(fund_code, report_period)
);

CREATE INDEX IF NOT EXISTS idx_ops_fund_period ON reit_operational_data (fund_code, report_period);
CREATE INDEX IF NOT EXISTS idx_ops_cap_rate ON reit_operational_data (cap_rate);

-- 表5：市场表现表（产权类）
CREATE TABLE IF NOT EXISTS reit_market_performance (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_code               VARCHAR(20) NOT NULL REFERENCES reit_product_info(fund_code),
    trade_date              DATE NOT NULL,
    opening_price           REAL,                       -- 开盘价
    closing_price           REAL,                       -- 收盘价
    highest_price           REAL,                       -- 最高价
    lowest_price            REAL,                       -- 最低价
    turnover                REAL,                       -- 成交额/万元
    volume                  REAL,                       -- 成交量/万手
    turnover_rate           REAL,                       -- 换手率%
    market_cap              REAL,                       -- 市值/万元
    daily_return            REAL,                       -- 日收益率%
    nav_premium_rate        REAL,                       -- 溢价率%
    lineage_id              INTEGER REFERENCES data_lineage(id),
    data_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_verified           INTEGER DEFAULT 0 CHECK (data_verified IN (0,1)),
    UNIQUE(fund_code, trade_date)
);

CREATE INDEX IF NOT EXISTS idx_mkt_fund_date ON reit_market_performance (fund_code, trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_mkt_premium ON reit_market_performance (nav_premium_rate);

-- 表6：投资者结构表（产权类）
CREATE TABLE IF NOT EXISTS reit_investor_structure (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_code               VARCHAR(20) NOT NULL REFERENCES reit_product_info(fund_code),
    report_period           VARCHAR(10) NOT NULL,
    investor_type           VARCHAR(20) NOT NULL CHECK (investor_type IN ('个人投资者', '机构投资者')),
    holder_count            INTEGER,                    -- 持有人户数
    holding_shares          REAL,                       -- 持有份额/万份
    holding_ratio           REAL CHECK (holding_ratio BETWEEN 0 AND 100), -- 持有比例%
    avg_holding_per_investor REAL,                      -- 户均持有/万份
    lineage_id              INTEGER REFERENCES data_lineage(id),
    data_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_verified           INTEGER DEFAULT 0 CHECK (data_verified IN (0,1)),
    UNIQUE(fund_code, report_period, investor_type)
);

CREATE INDEX IF NOT EXISTS idx_inv_fund_period ON reit_investor_structure (fund_code, report_period);
CREATE INDEX IF NOT EXISTS idx_inv_type ON reit_investor_structure (investor_type);

-- 表7：收益分配表（产权类）
CREATE TABLE IF NOT EXISTS reit_dividend_history (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_code               VARCHAR(20) NOT NULL REFERENCES reit_product_info(fund_code),
    dividend_year           INTEGER NOT NULL,           -- 分红年度
    dividend_round          INTEGER NOT NULL,           -- 分红轮次
    record_date             DATE,                       -- 权益登记日
    ex_dividend_date        DATE,                       -- 除息日
    dividend_payment_date   DATE,                       -- 红利发放日
    dividend_per_share      REAL,                       -- 每份分红金额/元
    total_dividend          REAL,                       -- 分红总额/万元
    dividend_yield          REAL,                       -- 分红收益率%
    lineage_id              INTEGER REFERENCES data_lineage(id),
    data_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_verified           INTEGER DEFAULT 0 CHECK (data_verified IN (0,1)),
    UNIQUE(fund_code, dividend_year, dividend_round)
);

CREATE INDEX IF NOT EXISTS idx_div_fund_year ON reit_dividend_history (fund_code, dividend_year);
CREATE INDEX IF NOT EXISTS idx_div_payment ON reit_dividend_history (dividend_payment_date);

-- 表8：风险指标表（产权类）
CREATE TABLE IF NOT EXISTS reit_risk_metrics (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_code               VARCHAR(20) NOT NULL REFERENCES reit_product_info(fund_code),
    report_period           VARCHAR(10) NOT NULL,
    debt_ratio              REAL CHECK (debt_ratio BETWEEN 0 AND 100), -- 资产负债率%
    debt_asset_ratio        REAL,                       -- 债务资产比%
    volatility_30d          REAL,                       -- 30日波动率%
    volatility_60d          REAL,                       -- 60日波动率%
    volatility_90d          REAL,                       -- 90日波动率%
    property_concentration  REAL CHECK (property_concentration BETWEEN 0 AND 100), -- 资产集中度%
    tenant_concentration    REAL CHECK (tenant_concentration BETWEEN 0 AND 100), -- 租户集中度%
    geographic_concentration REAL CHECK (geographic_concentration BETWEEN 0 AND 100), -- 区域集中度%
    liquidity_ratio         REAL,                       -- 流动性比率%
    credit_rating           VARCHAR(10),                -- 信用评级
    lineage_id              INTEGER REFERENCES data_lineage(id),
    data_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_verified           INTEGER DEFAULT 0 CHECK (data_verified IN (0,1)),
    UNIQUE(fund_code, report_period)
);

CREATE INDEX IF NOT EXISTS idx_risk_fund_period ON reit_risk_metrics (fund_code, report_period);
CREATE INDEX IF NOT EXISTS idx_risk_credit ON reit_risk_metrics (credit_rating);


-- ============================================================
-- 第二部分：经营权类 REITs（Concession REITs）
-- ============================================================

-- 表1：项目基础档案（经营权类）
CREATE TABLE IF NOT EXISTS reits_project_profile (
    project_code            VARCHAR(20) PRIMARY KEY,
    project_name            VARCHAR(100) NOT NULL,
    fund_short_name         VARCHAR(100),
    fund_type               VARCHAR(20) NOT NULL DEFAULT '经营权类' CHECK (fund_type = '经营权类'),
    asset_type              VARCHAR(20) NOT NULL CHECK (asset_type IN ('生态环保', '高速公路', '新能源')),
    manager_name            VARCHAR(100),               -- 基金管理人
    custodian_name          VARCHAR(100),               -- 基金托管人
    operating_manager       VARCHAR(200),               -- 运营管理机构
    abs_manager             VARCHAR(100),               -- ABS管理人
    original_equity_holder  VARCHAR(100) NOT NULL,      -- 原始权益人
    concession_period_years INTEGER,                    -- 特许经营权年限
    concession_start_date   DATE,                       -- 特许经营起始日
    concession_end_date     DATE,                       -- 特许经营到期日
    operation_start_date    DATE,                       -- 运营起始日
    remaining_concession_years INTEGER,                 -- 剩余特许经营年限
    annual_handling_capacity REAL,                      -- 年处理能力
    daily_handling_capacity REAL,                       -- 日处理能力
    capacity_unit           VARCHAR(20),                -- 能力单位
    province                VARCHAR(50),                -- 省
    city                    VARCHAR(50),                -- 市
    district                VARCHAR(50),                -- 区县
    address                 VARCHAR(500),               -- 详细地址
    total_assets            REAL,                       -- 总资产
    total_liabilities       REAL,                       -- 总负债
    net_assets              REAL,                       -- 净资产
    debt_ratio              REAL CHECK (debt_ratio BETWEEN 0 AND 100), -- 资产负债率
    issue_date              DATE,                       -- 发行日期
    listing_date            DATE,                       -- 上市日期
    issue_price             REAL,                       -- 发行价
    fund_shares             REAL,                       -- 基金份额
    credit_rating           VARCHAR(10),                -- 信用评级
    compliance_defect_flag  INTEGER DEFAULT 0 CHECK (compliance_defect_flag IN (0,1)), -- 合规缺陷标记
    missing_certificates    TEXT,                       -- 缺失证照清单（JSON）
    rights_restriction_amount REAL,                     -- 权利限制金额
    unpooled_asset_ratio    REAL CHECK (unpooled_asset_ratio BETWEEN 0 AND 100), -- 未入池资产比例
    competition_coefficient REAL,                       -- 竞争系数
    lineage_id              INTEGER REFERENCES data_lineage(id),
    data_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_verified           INTEGER DEFAULT 0 CHECK (data_verified IN (0,1))
);

CREATE INDEX IF NOT EXISTS idx_reits_profile_type ON reits_project_profile (asset_type);
CREATE INDEX IF NOT EXISTS idx_reits_profile_credit ON reits_project_profile (credit_rating) WHERE credit_rating IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_reits_profile_remaining ON reits_project_profile (remaining_concession_years) WHERE remaining_concession_years < 10;
CREATE INDEX IF NOT EXISTS idx_reits_profile_compliance ON reits_project_profile (compliance_defect_flag) WHERE compliance_defect_flag = 1;

-- 表2：运营数据明细表（经营权类）
CREATE TABLE IF NOT EXISTS reits_operation_detail (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    project_code            VARCHAR(20) NOT NULL REFERENCES reits_project_profile(project_code),
    report_period           VARCHAR(10) NOT NULL,
    waste_processing_volume REAL,                       -- 垃圾处理量
    waste_capacity_utilization REAL,                    -- 产能利用率
    power_generation        REAL,                       -- 发电量
    grid_settlement_volume  REAL,                       -- 电网结算量
    equivalent_utilization_hours REAL,                  -- 等效利用小时数
    kitchen_waste_collection REAL,                      -- 餐厨垃圾收运量
    kitchen_waste_disposal  REAL,                       -- 餐厨垃圾处置量
    avg_daily_collection    REAL,                       -- 日均收运量
    avg_daily_disposal      REAL,                       -- 日均处置量
    waste_treatment_fee     REAL,                       -- 垃圾处理费
    kitchen_collection_fee  REAL,                       -- 餐厨收运费
    kitchen_disposal_fee    REAL,                       -- 餐厨处置费
    power_price_on_grid     REAL,                       -- 上网电价
    power_price_baseline    REAL,                       -- 基准电价
    subsidy_national        REAL,                       -- 国家补贴
    subsidy_provincial      REAL,                       -- 省级补贴
    subsidy_dependency_ratio REAL,                      -- 补贴依赖度
    grid_company_name       VARCHAR(100),               -- 电网公司名称
    major_client_concentration REAL,                    -- 大客户集中度
    government_client_ratio REAL,                       -- 政府客户占比
    market_client_ratio     REAL,                       -- 市场客户占比
    accounts_receivable_amount REAL,                    -- 应收账款金额
    arrear_aging_days       INTEGER,                    -- 账龄天数
    collection_rate         REAL,                       -- 收缴率
    operating_cost          REAL,                       -- 运营成本
    unit_operating_cost     REAL,                       -- 单位运营成本
    lineage_id              INTEGER REFERENCES data_lineage(id),
    data_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_verified           INTEGER DEFAULT 0 CHECK (data_verified IN (0,1)),
    UNIQUE(project_code, report_period)
);

CREATE INDEX IF NOT EXISTS idx_reits_ops_project ON reits_operation_detail (project_code, report_period);
CREATE INDEX IF NOT EXISTS idx_reits_ops_collection ON reits_operation_detail (collection_rate) WHERE collection_rate < 95;
CREATE INDEX IF NOT EXISTS idx_reits_ops_subsidy ON reits_operation_detail (subsidy_dependency_ratio) WHERE subsidy_dependency_ratio > 50;

-- 表3：财务数据勾稽表（经营权类 SheetA/B/C 三层结构）
CREATE TABLE IF NOT EXISTS reits_financial_recon (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    project_code            VARCHAR(20) NOT NULL REFERENCES reits_project_profile(project_code),
    report_period           VARCHAR(10) NOT NULL,
    -- SheetA：利润表起点
    operating_income        REAL,                       -- 营业收入
    operating_cost          REAL,                       -- 营业成本
    ebitda                  REAL,
    depreciation_amortization REAL,                     -- 折旧摊销
    interest_expense        REAL,                       -- 利息费用
    net_profit              REAL,                       -- 净利润
    distributable_amount    REAL,                       -- 可供分配金额（初算）
    distribution_per_unit   REAL,                       -- 每份可供分配金额
    actual_distribution     REAL,                       -- 实际分配金额
    distribution_yield_annual REAL,                     -- 年化分派率
    -- SheetB：调整项
    net_profit_start        REAL,                       -- 净利润起点
    add_depreciation        REAL,                       -- 加回折旧
    add_interest            REAL,                       -- 加回利息
    add_other_adjustments   REAL,                       -- 其他调整项
    less_capex              REAL,                       -- 减资本性支出
    less_reserve_capital    REAL,                       -- 减资本性预留
    less_reserve_unforeseen REAL,                       -- 减不可预见费预留
    less_working_capital    REAL,                       -- 减营运资金变动
    less_next_year_opex     REAL,                       -- 减下一年运营支出
    less_current_distribution REAL,                     -- 减本期已分配
    -- SheetC：最终可供分配金额
    final_distributable     REAL,                       -- 最终可供分配金额
    -- 勾稽校验
    reconciliation_diff     REAL,                       -- 勾稽差异
    reconciliation_flag     INTEGER CHECK (reconciliation_flag IN (0,1)), -- 勾稽通过标记
    -- 现金流与应收监控
    operating_cash_flow     REAL,                       -- 经营活动现金流
    major_client_cash_inflow_ratio REAL,                -- 大客户现金流入占比
    subsidy_receivable      REAL,                       -- 补贴应收账款
    government_receivable   REAL,                       -- 政府应收账款
    lineage_id              INTEGER REFERENCES data_lineage(id),
    data_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_verified           INTEGER DEFAULT 0 CHECK (data_verified IN (0,1)),
    UNIQUE(project_code, report_period)
);

CREATE INDEX IF NOT EXISTS idx_reits_fin_project ON reits_financial_recon (project_code, report_period);
CREATE INDEX IF NOT EXISTS idx_reits_fin_flag ON reits_financial_recon (reconciliation_flag) WHERE reconciliation_flag = 0;
CREATE INDEX IF NOT EXISTS idx_reits_fin_yield ON reits_financial_recon (distribution_yield_annual) WHERE distribution_yield_annual IS NOT NULL;

-- 表4：估值假设拆解表（经营权类）
CREATE TABLE IF NOT EXISTS reits_valuation_assumptions (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    project_code            VARCHAR(20) NOT NULL REFERENCES reits_project_profile(project_code),
    valuation_date          DATE NOT NULL,
    primary_method          VARCHAR(50),                -- 主要估值方法
    cross_check_method      VARCHAR(50),                -- 交叉验证方法
    discount_rate           REAL,                       -- 折现率
    discount_rate_pre_tax   REAL,                       -- 税前折现率
    annual_cash_flow_forecast_1y REAL,                  -- 首年现金流预测
    annual_cash_flow_forecast_5y REAL,                  -- 第五年现金流预测
    cagr_cash_flow_pct      REAL,                       -- 现金流复合增长率
    price_mechanism         VARCHAR(100),               -- 定价机制
    price_adjustment_mechanism VARCHAR(100),            -- 价格调整机制
    subsidy_duration_years  INTEGER,                    -- 补贴持续年限
    sensitivity_volume_down_10pct REAL,                 -- 产量下降10%敏感性
    sensitivity_price_down_10pct REAL,                  -- 价格下降10%敏感性
    sensitivity_discount_up_1pct REAL,                  -- 折现率上升1%敏感性
    sensitivity_subsidy_cancel REAL,                    -- 补贴取消敏感性
    comparable_cases        TEXT,                       -- 可比案例（JSON）
    lineage_id              INTEGER REFERENCES data_lineage(id),
    data_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_verified           INTEGER DEFAULT 0 CHECK (data_verified IN (0,1))
);

CREATE INDEX IF NOT EXISTS idx_reits_val_project ON reits_valuation_assumptions (project_code, valuation_date DESC);
CREATE INDEX IF NOT EXISTS idx_reits_val_method ON reits_valuation_assumptions (primary_method, discount_rate);

-- 表5：同业竞争定位表（经营权类）
CREATE TABLE IF NOT EXISTS reits_competitor_gis (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    project_code            VARCHAR(20) NOT NULL REFERENCES reits_project_profile(project_code),
    competitor_name         VARCHAR(100),               -- 竞品名称
    competitor_operator     VARCHAR(100),               -- 竞品运营方
    distance_km             REAL,                       -- 距离（公里）
    competitor_capacity     REAL,                       -- 竞品产能
    competitor_capacity_unit VARCHAR(20),               -- 产能单位
    competitor_status       VARCHAR(50),                -- 竞品状态
    competitor_opening_date DATE,                       -- 竞品开业日期
    service_overlap_area    REAL,                       -- 服务重叠区域
    service_overlap_ratio   REAL,                       -- 服务重叠比例
    competition_threat_level VARCHAR(20),               -- 竞争威胁等级
    cooperation_agreement   INTEGER CHECK (cooperation_agreement IN (0,1)), -- 是否存在合作协议
    cooperation_type        VARCHAR(50),                -- 合作类型
    data_source             VARCHAR(100),               -- 数据来源
    source_page             VARCHAR(50),                -- 来源页码
    lineage_id              INTEGER REFERENCES data_lineage(id),
    data_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_verified           INTEGER DEFAULT 0 CHECK (data_verified IN (0,1))
);

CREATE INDEX IF NOT EXISTS idx_reits_comp_project ON reits_competitor_gis (project_code);
CREATE INDEX IF NOT EXISTS idx_reits_comp_distance ON reits_competitor_gis (distance_km);

-- 表6：运营风险信号表（经营权类）
CREATE TABLE IF NOT EXISTS reits_operation_risk (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    project_code            VARCHAR(20) NOT NULL REFERENCES reits_project_profile(project_code),
    calc_date               DATE NOT NULL,
    single_client_revenue_ratio REAL,                   -- 单一客户收入占比
    top3_client_concentration REAL,                     -- 前三大客户集中度
    government_dependency_ratio REAL,                   -- 政府依赖度
    collection_rate         REAL,                       -- 收缴率
    arrear_aging_1y         REAL,                       -- 1年以上账龄占比
    government_receivable_days INTEGER,                 -- 政府应收账款天数
    subsidy_receivable_delay_days INTEGER,              -- 补贴应收账款延迟天数
    remaining_concession_years REAL,                    -- 剩余特许经营年限
    expiry_risk_level       VARCHAR(10),                -- 到期风险等级
    capacity_utilization_volatility REAL,               -- 产能利用率波动率
    maintenance_cost_spike_flag INTEGER DEFAULT 0 CHECK (maintenance_cost_spike_flag IN (0,1)), -- 维护成本激增标记
    related_party_transaction_ratio REAL,               -- 关联交易占比
    related_party_pricing_deviation REAL,               -- 关联交易定价偏离度
    risk_level              VARCHAR(10) CHECK (risk_level IN ('绿', '橙', '红')), -- 风险等级
    risk_flags              TEXT,                       -- 风险标记（JSON）
    lineage_id              INTEGER REFERENCES data_lineage(id),
    data_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_verified           INTEGER DEFAULT 0 CHECK (data_verified IN (0,1)),
    UNIQUE(project_code, calc_date)
);

CREATE INDEX IF NOT EXISTS idx_reits_risk_project ON reits_operation_risk (project_code, calc_date DESC);
CREATE INDEX IF NOT EXISTS idx_reits_risk_red ON reits_operation_risk (project_code, calc_date) WHERE risk_level = '红';
CREATE INDEX IF NOT EXISTS idx_reits_risk_orange ON reits_operation_risk (project_code, calc_date) WHERE risk_level = '橙';
CREATE INDEX IF NOT EXISTS idx_reits_risk_collection ON reits_operation_risk (collection_rate) WHERE collection_rate < 95;
CREATE INDEX IF NOT EXISTS idx_reits_risk_gov ON reits_operation_risk (government_dependency_ratio) WHERE government_dependency_ratio > 50;

-- 表7：二级市场异常表（经营权类）
CREATE TABLE IF NOT EXISTS reits_market_anomaly (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    project_code            VARCHAR(20) NOT NULL REFERENCES reits_project_profile(project_code),
    trade_date              DATE NOT NULL,
    opening_price           REAL,                       -- 开盘价
    closing_price           REAL,                       -- 收盘价
    highest_price           REAL,                       -- 最高价
    lowest_price            REAL,                       -- 最低价
    turnover                REAL,                       -- 成交额
    volume                  REAL,                       -- 成交量
    turnover_rate           REAL,                       -- 换手率
    market_cap              REAL,                       -- 市值
    nav_per_share           REAL,                       -- 每份净值
    premium_rate            REAL,                       -- 溢价率
    remaining_years_at_trade REAL,                     -- 交易时剩余年限
    implied_discount_rate   REAL,                       -- 隐含折现率
    abnormal_volatility_flag INTEGER DEFAULT 0 CHECK (abnormal_volatility_flag IN (0,1)), -- 异常波动标记
    price_deviation_from_sector REAL,                   -- 相对板块价格偏离
    lineage_id              INTEGER REFERENCES data_lineage(id),
    data_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_verified           INTEGER DEFAULT 0 CHECK (data_verified IN (0,1)),
    UNIQUE(project_code, trade_date)
);

CREATE INDEX IF NOT EXISTS idx_reits_mkt_project ON reits_market_anomaly (project_code, trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_reits_mkt_anomaly ON reits_market_anomaly (abnormal_volatility_flag) WHERE abnormal_volatility_flag = 1;

-- 表8：监管问询追踪表（经营权类）
CREATE TABLE IF NOT EXISTS reits_regulatory_inquiry (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    project_code            VARCHAR(20) NOT NULL REFERENCES reits_project_profile(project_code),
    inquiry_id              VARCHAR(50) NOT NULL UNIQUE, -- 问询编号
    inquiry_date            DATE NOT NULL,              -- 问询日期
    inquiry_round           INTEGER DEFAULT 1,          -- 问询轮次
    question_category       VARCHAR(50),                -- 问题类别
    specific_question       TEXT,                       -- 具体问题
    regulatory_focus        VARCHAR(200),               -- 监管关注点
    response_filing_date    DATE,                       -- 回复提交日期
    response_summary        TEXT,                       -- 回复摘要
    revision_summary        TEXT,                       -- 修订摘要
    data_correction_flag    INTEGER DEFAULT 0 CHECK (data_correction_flag IN (0,1)), -- 数据更正标记
    correction_detail       TEXT,                       -- 更正详情（JSON）
    event_type              VARCHAR(50),                -- 事件类型
    personnel_name          VARCHAR(50),                -- 人员姓名
    position                VARCHAR(50),                -- 职位
    change_type             VARCHAR(50),                -- 变更类型
    lineage_id              INTEGER REFERENCES data_lineage(id),
    data_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_verified           INTEGER DEFAULT 0 CHECK (data_verified IN (0,1))
);

CREATE INDEX IF NOT EXISTS idx_reits_inq_project ON reits_regulatory_inquiry (project_code, inquiry_date);
CREATE INDEX IF NOT EXISTS idx_reits_inq_correction ON reits_regulatory_inquiry (project_code, inquiry_date) WHERE data_correction_flag = 1;
CREATE INDEX IF NOT EXISTS idx_reits_inq_round ON reits_regulatory_inquiry (inquiry_round) WHERE inquiry_round > 1;

-- 表9：合规与权利限制表（经营权类）
CREATE TABLE IF NOT EXISTS reits_compliance_base (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    project_code            VARCHAR(20) NOT NULL REFERENCES reits_project_profile(project_code),
    concession_agreement_valid INTEGER CHECK (concession_agreement_valid IN (0,1)), -- 特许经营协议有效
    concession_agreement_expiry DATE,                   -- 特许经营协议到期日
    government_approval_status VARCHAR(50),             -- 政府审批状态
    environmental_permits   INTEGER CHECK (environmental_permits IN (0,1)), -- 环评批复
    pollution_discharge_permit_no VARCHAR(50),         -- 排污许可证号
    electricity_business_license VARCHAR(50),            -- 电力业务许可证
    power_grid_connection_agreement INTEGER CHECK (power_grid_connection_agreement IN (0,1)), -- 并网协议
    land_use_planning_cert  INTEGER CHECK (land_use_planning_cert IN (0,1)), -- 用地规划许可证
    construction_planning_cert INTEGER CHECK (construction_planning_cert IN (0,1)), -- 工程规划许可证
    construction_permit     INTEGER CHECK (construction_permit IN (0,1)), -- 施工许可证
    completion_acceptance   INTEGER CHECK (completion_acceptance IN (0,1)), -- 竣工验收
    fire_acceptance         INTEGER CHECK (fire_acceptance IN (0,1)), -- 消防验收
    mortgage_amount         REAL,                       -- 抵押金额
    pledge_amount           REAL,                       -- 质押金额
    guarantee_amount        REAL,                       -- 担保金额
    total_rights_restriction REAL,                      -- 权利限制合计（应用层计算）
    restriction_release_progress REAL,                  -- 解除进度
    completion_rate         REAL,                       -- 完工率
    nine_articles_rate      REAL,                       -- 九项合规完成率
    compliance_risk_level   VARCHAR(10),                -- 合规风险等级
    -- 九项合规布尔字段
    article_1_compliance    INTEGER CHECK (article_1_compliance IN (0,1)),
    article_2_compliance    INTEGER CHECK (article_2_compliance IN (0,1)),
    article_3_compliance    INTEGER CHECK (article_3_compliance IN (0,1)),
    article_4_compliance    INTEGER CHECK (article_4_compliance IN (0,1)),
    article_5_compliance    INTEGER CHECK (article_5_compliance IN (0,1)),
    article_6_compliance    INTEGER CHECK (article_6_compliance IN (0,1)),
    article_7_compliance    INTEGER CHECK (article_7_compliance IN (0,1)),
    article_8_compliance    INTEGER CHECK (article_8_compliance IN (0,1)),
    article_9_concession    INTEGER CHECK (article_9_concession IN (0,1)),
    lineage_id              INTEGER REFERENCES data_lineage(id),
    data_timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_verified           INTEGER DEFAULT 0 CHECK (data_verified IN (0,1)),
    UNIQUE(project_code)
);

CREATE INDEX IF NOT EXISTS idx_reits_comp_base_project ON reits_compliance_base (project_code);
CREATE INDEX IF NOT EXISTS idx_reits_comp_base_nine ON reits_compliance_base (nine_articles_rate) WHERE nine_articles_rate < 100;
