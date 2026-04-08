-- 大盘指数表
CREATE TABLE IF NOT EXISTS market_indices (
    code TEXT PRIMARY KEY,           -- 指数代码：sh_index, dividend, reits_total, bond_yield
    name TEXT NOT NULL,              -- 指数名称
    value REAL NOT NULL,             -- 当前值（点数或百分比）
    change REAL,                     -- 涨跌值
    change_percent REAL,             -- 涨跌幅（%）
    source TEXT,                     -- 数据来源
    updated_at DATETIME,             -- 更新时间
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 初始化数据（默认占位值）
INSERT OR IGNORE INTO market_indices (code, name, value, change, change_percent, source) VALUES
('sh_index', '上证指数', 3881.28, 67.83, 1.78, 'mock'),
('dividend', '中证红利', 5712.79, 86.83, 1.54, 'mock'),
('reits_total', '中证REITs全收益', 1013.78, 1.72, 0.17, 'mock'),
('bond_yield', '10年期国债收益率', 1.83, -0.02, -0.24, 'mock');
