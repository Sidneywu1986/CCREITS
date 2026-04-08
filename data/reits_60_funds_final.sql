-- REITs基金完整数据 - 共60只 (去重后)
-- 序号1-60完整清单

-- 1. 清空所有相关表
DELETE FROM quotes;
DELETE FROM price_history;
DELETE FROM announcements;
DELETE FROM funds;
DELETE FROM sqlite_sequence WHERE name IN ('funds', 'quotes', 'price_history', 'announcements');

-- 2. 插入60只基金完整数据（已去重）
INSERT INTO funds (code, name, sector, sector_name) VALUES
-- ========== 第1-20只: 深交所 ==========
('180101', '博时蛇口产园REIT', 'industrial', '产业园区'),
('180102', '华夏合肥高新REIT', 'industrial', '产业园区'),
('180103', '华夏和达高科REIT', 'industrial', '产业园区'),
('180105', '易方达广开产园REIT', 'industrial', '产业园区'),
('180106', '广发成都高投产业REIT', 'industrial', '产业园区'),
('180201', '平安广州广河REIT', 'transport', '交通基础设施'),
('180202', '华夏越秀高速REIT', 'transport', '交通基础设施'),
('180203', '招商高速公路REIT', 'transport', '交通基础设施'),
('180301', '红土创新盐田港REIT', 'logistics', '仓储物流'),
('180302', '华夏深国际REIT', 'logistics', '仓储物流'),
('180303', '华泰宝湾物流REIT', 'logistics', '仓储物流'),
('180305', '南方顺丰物流REIT', 'logistics', '仓储物流'),
('180306', '华夏安博仓储REIT', 'logistics', '仓储物流'),
('180401', '鹏华深圳能源REIT', 'energy', '能源基础设施'),
('180402', '工银蒙能清洁能源REIT', 'energy', '能源基础设施'),
('180501', '红土创新深圳安居REIT', 'housing', '租赁住房'),
('180502', '招商基金蛇口租赁REIT', 'housing', '租赁住房'),
('180601', '华夏华润商业REIT', 'consumer', '消费基础设施'),
('180602', '中金印力消费REIT', 'consumer', '消费基础设施'),
('180603', '华夏大悦城商业REIT', 'consumer', '消费基础设施'),

-- ========== 第21-40只 ==========
('180605', '易方达华威市场REIT', 'consumer', '消费基础设施'),
('180606', '中金中国绿发商业REIT', 'consumer', '消费基础设施'),
('180607', '华夏中海商业REIT', 'consumer', '消费基础设施'),
('180701', '银华绍兴原水水利REIT', 'water', '水利设施'),
('180801', '中航首钢绿能REIT', 'eco', '生态环保'),
('180901', '南方润泽科技数据中心REIT', 'datacenter', '数据中心'),
('180503', '中航北京昌保租赁REIT', 'housing', '租赁住房'),
('508000', '华安张江产业园REIT', 'industrial', '产业园区'),
('508001', '浙商沪杭甬REIT', 'transport', '交通基础设施'),
('508002', '华安百联消费REIT', 'consumer', '消费基础设施'),
('508003', '中金联东科创REIT', 'industrial', '产业园区'),
('508005', '华夏首创奥莱REIT', 'consumer', '消费基础设施'),
('508006', '富国首创水务REIT', 'eco', '生态环保'),
('508007', '中金山东高速REIT', 'transport', '交通基础设施'),
('508008', '国金中国铁建REIT', 'logistics', '仓储物流'),
('508009', '中金安徽交控REIT', 'transport', '交通基础设施'),
('508010', '中金重庆两江REIT', 'industrial', '产业园区'),
('508011', '嘉实物美消费REIT', 'consumer', '消费基础设施'),
('508012', '招商科创REIT', 'industrial', '产业园区'),
('508015', '中信建投明阳智能REIT', 'energy', '能源基础设施'),

-- ========== 第41-60只 ==========
('508018', '华夏中国交建REIT', 'transport', '交通基础设施'),
('508019', '中金湖北科投光谷REIT', 'industrial', '产业园区'),
('508021', '华夏中核清洁能源REIT', 'energy', '能源基础设施'),
('508022', '招商科创REIT', 'industrial', '产业园区'),
('508026', '嘉实中国电建清洁能源REIT', 'energy', '能源基础设施'),
('508027', '东吴苏园产业REIT', 'industrial', '产业园区'),
('508028', '华夏和达高科REIT', 'industrial', '产业园区'),
('508029', '国泰君安东久新经济REIT', 'industrial', '产业园区'),
('508031', '国泰海通济南能源REIT', 'energy', '能源基础设施'),
('508033', '易方达深高速REIT', 'transport', '交通基础设施'),
('508036', '招商高速公路REIT', 'transport', '交通基础设施'),
('508039', '中金中国绿发商业REIT', 'consumer', '消费基础设施'),
('508048', '华夏大悦城商业REIT', 'consumer', '消费基础设施'),
('508056', '中金普洛斯REIT', 'logistics', '仓储物流'),
('508058', '中金厦门安居REIT', 'housing', '租赁住房'),
('508066', '华夏南京交通高速公路REIT', 'transport', '交通基础设施'),
('508077', '国泰海通东久新经济REIT', 'industrial', '产业园区'),
('508078', '华夏首创奥特莱斯REIT', 'consumer', '消费基础设施'),
('508080', '中金亦庄产业园REIT', 'industrial', '产业园区'),
('508081', '中银中外运仓储物流REIT', 'logistics', '仓储物流');

-- 3. 统计
SELECT '数据库重置完成' as status;
SELECT COUNT(*) as 总数量 FROM funds;
SELECT sector_name as 板块, COUNT(*) as 数量 FROM funds GROUP BY sector_name ORDER BY 数量 DESC;
