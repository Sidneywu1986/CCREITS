-- REITs基金完整数据 - 共40只 (1-20 深交所, 21-40 混合)
-- 清空并重新插入所有数据

-- 1. 清空所有相关表
DELETE FROM quotes;
DELETE FROM price_history;
DELETE FROM announcements;
DELETE FROM funds;
DELETE FROM sqlite_sequence WHERE name IN ('funds', 'quotes', 'price_history', 'announcements');

-- 2. 插入40只基金完整数据
INSERT INTO funds (code, name, sector, sector_name) VALUES
-- ========== 第1-20只: 深交所 (180开头) ==========
-- 产业园区 (5只: 1-5)
('180101', '博时蛇口产园REIT', 'industrial', '产业园区'),
('180102', '华夏合肥高新REIT', 'industrial', '产业园区'),
('180103', '华夏和达高科REIT', 'industrial', '产业园区'),
('180105', '易方达广开产园REIT', 'industrial', '产业园区'),
('180106', '广发成都高投产业REIT', 'industrial', '产业园区'),

-- 交通基础设施 (3只: 6-8)
('180201', '平安广州广河REIT', 'transport', '交通基础设施'),
('180202', '华夏越秀高速REIT', 'transport', '交通基础设施'),
('180203', '招商高速公路REIT', 'transport', '交通基础设施'),

-- 仓储物流 (5只: 9-13)
('180301', '红土创新盐田港REIT', 'logistics', '仓储物流'),
('180302', '华夏深国际REIT', 'logistics', '仓储物流'),
('180303', '华泰宝湾物流REIT', 'logistics', '仓储物流'),
('180305', '南方顺丰物流REIT', 'logistics', '仓储物流'),
('180306', '华夏安博仓储REIT', 'logistics', '仓储物流'),

-- 能源基础设施 (2只: 14-15)
('180401', '鹏华深圳能源REIT', 'energy', '能源基础设施'),
('180402', '工银蒙能清洁能源REIT', 'energy', '能源基础设施'),

-- 租赁住房 (2只: 16-17)
('180501', '红土创新深圳安居REIT', 'housing', '租赁住房'),
('180502', '招商基金蛇口租赁REIT', 'housing', '租赁住房'),

-- 消费基础设施 (3只: 18-20)
('180601', '华夏华润商业REIT', 'consumer', '消费基础设施'),
('180602', '中金印力消费REIT', 'consumer', '消费基础设施'),
('180603', '华夏大悦城商业REIT', 'consumer', '消费基础设施'),

-- ========== 第21-40只 ==========
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

-- 上交所 - 产业园区 (4只: 28, 31, 37, 39)
('508000', '华安张江产业园REIT', 'industrial', '产业园区'),
('508003', '中金联东科创REIT', 'industrial', '产业园区'),
('508010', '中金重庆两江REIT', 'industrial', '产业园区'),
('508012', '招商科创REIT', 'industrial', '产业园区'),

-- 上交所 - 交通基础设施 (3只: 29, 34, 36)
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

-- 3. 验证结果
SELECT '数据库重置完成 - 共40只基金' as status;

SELECT 
    sector_name as 板块, 
    COUNT(*) as 数量,
    GROUP_CONCAT(code, ', ') as 代码列表
FROM funds 
GROUP BY sector_name 
ORDER BY 数量 DESC;

SELECT 
    CASE 
        WHEN code LIKE '180%' THEN '深交所'
        WHEN code LIKE '508%' THEN '上交所'
        ELSE '其他'
    END as 交易所,
    COUNT(*) as 数量
FROM funds
GROUP BY 交易所;

SELECT code as 代码, name as 基金名称, sector_name as 板块 FROM funds ORDER BY code;
