-- REITs数据平台 - SQLite数据库Schema
-- 阶段一：快速可用版本

-- 1. 基金基础信息表
CREATE TABLE IF NOT EXISTS funds (
    code TEXT PRIMARY KEY,           -- 基金代码（如 508056）
    name TEXT NOT NULL,              -- 基金名称
    sector TEXT,                     -- 板块（transport/logistics等）
    sector_name TEXT,                -- 板块显示名
    manager TEXT,                    -- 基金管理人
    listing_date TEXT,               -- 成立日期（YYYY-MM-DD）
    scale REAL,                      -- 规模（亿）
    nav REAL,                        -- 最新单位净值
    debt_ratio REAL,                 -- 债务率（%）
    property_type TEXT,              -- 资产类型
    remaining_years TEXT,            -- 剩余期限
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2. 实时行情表（高频更新）
CREATE TABLE IF NOT EXISTS quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_code TEXT NOT NULL,
    price REAL NOT NULL,             -- 当前价
    change_percent REAL,             -- 涨跌幅（%）
    change_amount REAL,              -- 涨跌额
    volume INTEGER,                  -- 成交量
    premium REAL,                    -- 溢价率（%）
    yield REAL,                      -- 派息率（%）
    market_cap REAL,                 -- 流通市值（亿）
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fund_code) REFERENCES funds(code)
);

-- 3. 历史价格表（日K线）
CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_code TEXT NOT NULL,
    date TEXT NOT NULL,              -- 日期（YYYY-MM-DD）
    open REAL,                       -- 开盘价
    close REAL,                      -- 收盘价
    high REAL,                       -- 最高价
    low REAL,                        -- 最低价
    volume INTEGER,                  -- 成交量
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(fund_code, date),
    FOREIGN KEY (fund_code) REFERENCES funds(code)
);

-- 4. 公告表
CREATE TABLE IF NOT EXISTS announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_code TEXT,                  -- 关联基金（可为空，表示市场公告）
    title TEXT NOT NULL,             -- 公告标题
    category TEXT,                   -- 分类（operation/dividend/inquiry/financial）
    summary TEXT,                    -- AI摘要
    publish_date TEXT,               -- 发布日期
    source_url TEXT,                 -- 原文链接
    pdf_url TEXT,                    -- PDF下载链接
    exchange TEXT,                   -- 交易所（SSE/SZSE）
    confidence REAL,                 -- AI分类置信度
    is_read INTEGER DEFAULT 0,       -- 是否已读
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fund_code) REFERENCES funds(code)
);

-- 5. 数据源追踪表（血缘管理简化版）
CREATE TABLE IF NOT EXISTS data_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_type TEXT NOT NULL,         -- 数据类型（price/announcement/nav等）
    source_name TEXT NOT NULL,       -- 来源名称（sina-finance/sse等）
    source_url TEXT,                 -- 来源地址
    last_updated DATETIME,           -- 最后更新时间
    update_count INTEGER DEFAULT 0,  -- 更新次数
    status TEXT DEFAULT 'active',    -- 状态（active/error/disabled）
    error_msg TEXT,                  -- 错误信息
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 6. 数据更新日志
CREATE TABLE IF NOT EXISTS update_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_type TEXT NOT NULL,         -- 数据类型
    source TEXT,                     -- 数据来源
    status TEXT,                     -- 状态（success/error）
    records_count INTEGER,           -- 更新记录数
    duration_ms INTEGER,             -- 耗时（毫秒）
    error_msg TEXT,                  -- 错误信息
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_quotes_fund_code ON quotes(fund_code);
CREATE INDEX IF NOT EXISTS idx_quotes_updated ON quotes(updated_at);
CREATE INDEX IF NOT EXISTS idx_price_history_fund_date ON price_history(fund_code, date);
CREATE INDEX IF NOT EXISTS idx_announcements_fund ON announcements(fund_code);
CREATE INDEX IF NOT EXISTS idx_announcements_date ON announcements(publish_date);

-- 初始化基金基础数据（81只REITs）
-- 注意：实际数据通过脚本导入或前端common.js同步
