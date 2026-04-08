-- 重置REITs数据库 - 只保留20只基金
-- 执行方式: 在SQLite中运行 .read reset_reits_db.sql

-- 1. 清空所有相关表
DELETE FROM quotes;
DELETE FROM price_history;
DELETE FROM announcements;
DELETE FROM funds;

-- 2. 重置自增ID
DELETE FROM sqlite_sequence WHERE name IN ('funds', 'quotes', 'price_history', 'announcements');

-- 3. 插入20只基金数据（以图片为准）
INSERT INTO funds (code, name, sector, sector_name) VALUES
-- 产业园区 (5只)
('180101', '博时蛇口产园REIT', 'industrial', '产业园区'),
('180102', '华夏合肥高新REIT', 'industrial', '产业园区'),
('180103', '华夏和达高科REIT', 'industrial', '产业园区'),
('180105', '易方达广开产园REIT', 'industrial', '产业园区'),
('180106', '广发成都高投产业REIT', 'industrial', '产业园区'),

-- 交通基础设施 (3只)
('180201', '平安广州广河REIT', 'transport', '交通基础设施'),
('180202', '华夏越秀高速REIT', 'transport', '交通基础设施'),
('180203', '招商高速公路REIT', 'transport', '交通基础设施'),

-- 仓储物流 (5只)
('180301', '红土创新盐田港REIT', 'logistics', '仓储物流'),
('180302', '华夏深国际REIT', 'logistics', '仓储物流'),
('180303', '华泰宝湾物流REIT', 'logistics', '仓储物流'),
('180305', '南方顺丰物流REIT', 'logistics', '仓储物流'),
('180306', '华夏安博仓储REIT', 'logistics', '仓储物流'),

-- 能源基础设施 (2只)
('180401', '鹏华深圳能源REIT', 'energy', '能源基础设施'),
('180402', '工银蒙能清洁能源REIT', 'energy', '能源基础设施'),

-- 租赁住房 (2只)
('180501', '红土创新深圳安居REIT', 'housing', '租赁住房'),
('180502', '招商基金蛇口租赁REIT', 'housing', '租赁住房'),

-- 消费基础设施 (3只)
('180601', '华夏华润商业REIT', 'consumer', '消费基础设施'),
('180602', '中金印力消费REIT', 'consumer', '消费基础设施'),
('180603', '华夏大悦城商业REIT', 'consumer', '消费基础设施');

-- 验证结果
SELECT '重置完成' as status;
SELECT sector_name as 板块, COUNT(*) as 数量 FROM funds GROUP BY sector_name ORDER BY 数量 DESC;
SELECT code as 代码, name as 基金名称, sector_name as 板块 FROM funds ORDER BY code;
