-- 添加第21-40只REITs基金
-- 执行方式: 在SQLite中运行 .read update_reits_21_40.sql

-- 插入20只基金数据
INSERT INTO funds (code, name, sector, sector_name) VALUES
-- 消费基础设施 (3只: 21-23)
('180605', '易方达华威市场REIT', 'consumer', '消费基础设施'),
('180606', '中金中国绿发商业REIT', 'consumer', '消费基础设施'),
('180607', '华夏中海商业REIT', 'consumer', '消费基础设施'),

-- 水利设施 (1只: 24)
('180701', '银华绍兴原水水利REIT', 'water', '水利设施'),

-- 生态环保 (1只: 25)
('180801', '中航首钢绿能REIT', 'eco', '生态环保'),

-- 数据中心 (1只: 26)
('180901', '南方润泽科技数据中心REIT', 'datacenter', '数据中心'),

-- 租赁住房 (1只: 27)
('180503', '中航北京昌保租赁REIT', 'housing', '租赁住房'),

-- 上交所 - 产业园区 (2只: 28, 31, 37, 39)
('508000', '华安张江产业园REIT', 'industrial', '产业园区'),
('508003', '中金联东科创REIT', 'industrial', '产业园区'),
('508010', '中金重庆两江REIT', 'industrial', '产业园区'),
('508012', '招商科创REIT', 'industrial', '产业园区'),

-- 上交所 - 交通基础设施 (2只: 29, 34, 36)
('508001', '浙商沪杭甬REIT', 'transport', '交通基础设施'),
('508007', '中金山东高速REIT', 'transport', '交通基础设施'),
('508009', '中金安徽交控REIT', 'transport', '交通基础设施'),

-- 上交所 - 消费基础设施 (3只: 30, 32, 38)
('508002', '华安百联消费REIT', 'consumer', '消费基础设施'),
('508005', '华夏首创奥莱REIT', 'consumer', '消费基础设施'),
('508011', '嘉实物美消费REIT', 'consumer', '消费基础设施'),

-- 上交所 - 生态环保 (1只: 33)
('508006', '富国首创水务REIT', 'eco', '生态环保'),

-- 上交所 - 仓储物流 (1只: 35)
('508008', '国金中国铁建REIT', 'logistics', '仓储物流'),

-- 上交所 - 能源基础设施 (1只: 40)
('508015', '中信建投明阳智能REIT', 'energy', '能源基础设施');

-- 验证结果
SELECT '第21-40只基金添加完成' as status;
SELECT sector_name as 板块, COUNT(*) as 数量 FROM funds GROUP BY sector_name ORDER BY 数量 DESC;
SELECT code as 代码, name as 基金名称, sector_name as 板块 FROM funds WHERE code >= '180605' OR code LIKE '508%' ORDER BY code;
