/**
 * 基金相关API
 * 路径：/api/funds
 */

const express = require('express');
const router = express.Router();
const { db } = require('../database/db');

/**
 * 计算溢价率
 * @param {number} price - 当前市价
 * @param {number} nav - 单位净值
 * @returns {number|null} 溢价率（%）
 */
function calculatePremium(price, nav) {
    if (!price || !nav || nav <= 0) return null;
    return parseFloat(((price - nav) / nav * 100).toFixed(2));
}

/**
 * 计算流通市值
 * @param {number} price - 当前市价
 * @param {number} shares - 流通份额（万份）
 * @returns {number|null} 流通市值（亿元）
 */
function calculateMarketCap(price, shares) {
    if (!price || !shares) return null;
    return parseFloat((price * shares / 10000).toFixed(2));
}

/**
 * 计算派息率（年化）
 * @param {number} price - 当前市价
 * @param {Array} dividends - 分红历史
 * @returns {number|null} 派息率（%）
 */
function calculateYield(price, dividends) {
    if (!price || !dividends || dividends.length === 0) return null;
    
    const oneYearAgo = new Date();
    oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1);
    
    const annualDividend = dividends
        .filter(d => new Date(d.date) >= oneYearAgo)
        .reduce((sum, d) => sum + (d.amount || 0), 0);
    
    if (annualDividend <= 0) return null;
    
    return parseFloat((annualDividend / price * 100).toFixed(2));
}

// REITs 板块映射表（代码段 -> 板块信息）- 基于Excel导入的真实数据
// 注意：数据库中的 sector 字段是主要数据来源，此为后备映射
const SECTOR_MAP = {
    // 交通基础设施 (13只)
    '180201': { sector: 'transport', sector_name: '交通基础设施' },
    '180202': { sector: 'transport', sector_name: '交通基础设施' },
    '180203': { sector: 'transport', sector_name: '交通基础设施' },
    '508001': { sector: 'transport', sector_name: '交通基础设施' },
    '508007': { sector: 'transport', sector_name: '交通基础设施' },
    '508009': { sector: 'transport', sector_name: '交通基础设施' },
    '508018': { sector: 'transport', sector_name: '交通基础设施' },
    '508020': { sector: 'transport', sector_name: '交通基础设施' },
    '508033': { sector: 'transport', sector_name: '交通基础设施' },
    '508036': { sector: 'transport', sector_name: '交通基础设施' },
    '508066': { sector: 'transport', sector_name: '交通基础设施' },
    '508069': { sector: 'transport', sector_name: '交通基础设施' },
    '508086': { sector: 'transport', sector_name: '交通基础设施' },
    // 仓储物流 (11只)
    '180301': { sector: 'logistics', sector_name: '仓储物流' },
    '180302': { sector: 'logistics', sector_name: '仓储物流' },
    '180303': { sector: 'logistics', sector_name: '仓储物流' },
    '180305': { sector: 'logistics', sector_name: '仓储物流' },
    '180306': { sector: 'logistics', sector_name: '仓储物流' },
    '508008': { sector: 'logistics', sector_name: '仓储物流' },
    '508056': { sector: 'logistics', sector_name: '仓储物流' },
    '508078': { sector: 'logistics', sector_name: '仓储物流' },
    '508084': { sector: 'logistics', sector_name: '仓储物流' },
    '508090': { sector: 'logistics', sector_name: '仓储物流' },
    '508098': { sector: 'logistics', sector_name: '仓储物流' },
    // 产业园区 (21只)
    '180101': { sector: 'industrial', sector_name: '产业园区' },
    '180102': { sector: 'industrial', sector_name: '产业园区' },
    '180103': { sector: 'industrial', sector_name: '产业园区' },
    '180105': { sector: 'industrial', sector_name: '产业园区' },
    '180106': { sector: 'industrial', sector_name: '产业园区' },
    '508000': { sector: 'industrial', sector_name: '产业园区' },
    '508003': { sector: 'industrial', sector_name: '产业园区' },
    '508010': { sector: 'industrial', sector_name: '产业园区' },
    '508012': { sector: 'industrial', sector_name: '产业园区' },
    '508019': { sector: 'industrial', sector_name: '产业园区' },
    '508021': { sector: 'industrial', sector_name: '产业园区' },
    '508022': { sector: 'industrial', sector_name: '产业园区' },
    '508027': { sector: 'industrial', sector_name: '产业园区' },
    '508029': { sector: 'industrial', sector_name: '产业园区' },
    '508048': { sector: 'industrial', sector_name: '产业园区' },
    '508058': { sector: 'industrial', sector_name: '产业园区' },
    '508080': { sector: 'industrial', sector_name: '产业园区' },
    '508088': { sector: 'industrial', sector_name: '产业园区' },
    '508092': { sector: 'industrial', sector_name: '产业园区' },
    '508097': { sector: 'industrial', sector_name: '产业园区' },
    '508099': { sector: 'industrial', sector_name: '产业园区' },
    // 消费基础设施 (13只)
    '180601': { sector: 'consumer', sector_name: '消费基础设施' },
    '180602': { sector: 'consumer', sector_name: '消费基础设施' },
    '180603': { sector: 'consumer', sector_name: '消费基础设施' },
    '180605': { sector: 'consumer', sector_name: '消费基础设施' },
    '180606': { sector: 'consumer', sector_name: '消费基础设施' },
    '180607': { sector: 'consumer', sector_name: '消费基础设施' },
    '508002': { sector: 'consumer', sector_name: '消费基础设施' },
    '508005': { sector: 'consumer', sector_name: '消费基础设施' },
    '508011': { sector: 'consumer', sector_name: '消费基础设施' },
    '508017': { sector: 'consumer', sector_name: '消费基础设施' },
    '508039': { sector: 'consumer', sector_name: '消费基础设施' },
    '508082': { sector: 'consumer', sector_name: '消费基础设施' },
    '508091': { sector: 'consumer', sector_name: '消费基础设施' },
    // 能源基础设施 (9只)
    '180401': { sector: 'energy', sector_name: '能源基础设施' },
    '180402': { sector: 'energy', sector_name: '能源基础设施' },
    '508015': { sector: 'energy', sector_name: '能源基础设施' },
    '508016': { sector: 'energy', sector_name: '能源基础设施' },
    '508026': { sector: 'energy', sector_name: '能源基础设施' },
    '508028': { sector: 'energy', sector_name: '能源基础设施' },
    '508050': { sector: 'energy', sector_name: '能源基础设施' },
    '508089': { sector: 'energy', sector_name: '能源基础设施' },
    '508096': { sector: 'energy', sector_name: '能源基础设施' },
    // 租赁住房 (8只)
    '180501': { sector: 'housing', sector_name: '租赁住房' },
    '180502': { sector: 'housing', sector_name: '租赁住房' },
    '180503': { sector: 'housing', sector_name: '租赁住房' },
    '508031': { sector: 'housing', sector_name: '租赁住房' },
    '508055': { sector: 'housing', sector_name: '租赁住房' },
    '508068': { sector: 'housing', sector_name: '租赁住房' },
    '508077': { sector: 'housing', sector_name: '租赁住房' },
    '508085': { sector: 'housing', sector_name: '租赁住房' },
    // 生态环保 (2只)
    '180801': { sector: 'eco', sector_name: '生态环保' },
    '508006': { sector: 'eco', sector_name: '生态环保' },
    // 水利设施 (1只)
    '180701': { sector: 'water', sector_name: '水利设施' },
    // 数据中心 (2只)
    '180901': { sector: 'datacenter', sector_name: '数据中心' },
    '508060': { sector: 'datacenter', sector_name: '数据中心' },
    // 市政设施 (1只)
    '508087': { sector: 'municipal', sector_name: '市政设施' },
    // 其他未分类的默认
    'default': { sector: 'other', sector_name: '其他' }
};

// 根据代码前三位判断板块
function getSectorByCode(code) {
    // 直接查找
    if (SECTOR_MAP[code]) return SECTOR_MAP[code];
    
    // 根据代码段判断
    const prefix = code.substring(0, 3);
    const prefixMap = {
        '180': 'industrial',  // 深市产业园区
        '508': 'logistics'    // 沪市仓储物流
    };
    
    return {
        sector: prefixMap[prefix] || 'industrial',
        sector_name: prefix === '180' ? '产业园区' : '仓储物流'
    };
}

/**
 * GET /api/funds
 * 获取所有基金列表（基础信息+最新行情）
 */
router.get('/', (req, res) => {
    const sql = `
        SELECT 
            f.code,
            f.name,
            f.sector,
            f.sector_name,
            f.manager,
            f.listing_date,
            f.scale,
            f.property_type,
            f.remaining_years,
            f.circulating_shares,
            f.nav,
            f.debt_ratio,
            f.institution_hold,
            q.price,
            q.change_percent,
            q.yield,
            q.premium,
            q.volume,
            q.market_cap,
            q.updated_at as quote_time
        FROM funds f
        LEFT JOIN quotes q ON f.code = q.fund_code
        WHERE q.id = (
            SELECT MAX(id) FROM quotes WHERE fund_code = f.code
        )
        ORDER BY f.code
    `;
    
    db.all(sql, [], (err, funds) => {
        if (err) {
            console.error('获取基金列表失败:', err);
            return res.status(500).json({
                success: false,
                error: err.message
            });
        }
        
        // 补充缺失的 sector 信息，并统一字段命名（驼峰式）
        // 同时计算溢价率和流通市值
        const enrichedFunds = funds.map(fund => {
            if (!fund.sector) {
                const sectorInfo = getSectorByCode(fund.code);
                fund.sector = sectorInfo.sector;
                fund.sector_name = sectorInfo.sector_name;
            }
            
            // 实时计算溢价率和流通市值
            const premium = calculatePremium(fund.price, fund.nav);
            const marketCap = calculateMarketCap(fund.price, fund.circulating_shares);
            
            // 统一转换为驼峰命名，兼容前端
            return {
                code: fund.code,
                name: fund.name,
                sector: fund.sector,
                sectorName: fund.sector_name,
                manager: fund.manager,
                listingDate: fund.listing_date,
                scale: fund.scale,
                propertyType: fund.property_type,
                remainingYears: fund.remaining_years,
                price: fund.price,
                change: fund.change_percent,
                changePercent: fund.change_percent,
                yield: fund.yield,
                premium: premium !== null ? premium : fund.premium,
                volume: fund.volume,
                marketCap: marketCap !== null ? marketCap : fund.market_cap,
                nav: fund.nav,
                debt: fund.debt_ratio,
                institutionHold: fund.institution_hold,
                quoteTime: fund.quote_time
            };
        });
        
        res.json({
            success: true,
            count: enrichedFunds.length,
            data: enrichedFunds,
            timestamp: new Date().toISOString()
        });
    });
});

/**
 * GET /api/funds/:code
 * 获取单个基金详情
 */
router.get('/:code', (req, res) => {
    const { code } = req.params;
    
    // 基础信息+最新行情
    const fundSql = `
        SELECT 
            f.*,
            q.price, q.open, q.high, q.low, q.prev_close, 
            q.change_percent, q.volume, q.premium, q.yield,
            q.market_cap, q.updated_at
        FROM funds f
        LEFT JOIN quotes q ON f.code = q.fund_code
        WHERE f.code = ?
        ORDER BY q.id DESC
        LIMIT 1
    `;
    
    db.get(fundSql, [code], (err, fund) => {
        if (err) {
            console.error('获取基金详情失败:', err);
            return res.status(500).json({
                success: false,
                error: err.message
            });
        }
        
        if (!fund) {
            return res.status(404).json({
                success: false,
                error: '基金不存在'
            });
        }
        
        // 最近30天历史价格（用于K线）
        const historySql = `
            SELECT date, open, close, high, low, volume
            FROM price_history
            WHERE fund_code = ?
            ORDER BY date DESC
            LIMIT 30
        `;
        
        db.all(historySql, [code], (err, history) => {
            if (err) {
                console.error('获取历史数据失败:', err);
                return res.status(500).json({
                    success: false,
                    error: err.message
                });
            }
            
            // 如果 sector 为 null，根据 code 前缀自动映射
            if (!fund.sector && fund.code) {
                fund.sector = SECTOR_MAP[fund.code] || 'other';
            }

            // 确保返回 sector_name
            if (fund.sector && !fund.sector_name) {
                const SECTOR_CONFIG = {
                    'transport': { name: '交通基础设施' },
                    'logistics': { name: '仓储物流' },
                    'industrial': { name: '产业园区' },
                    'housing': { name: '租赁住房' },
                    'energy': { name: '能源基础设施' },
                    'eco': { name: '生态环保' },
                    'datacenter': { name: '数据中心' },
                    'tourism': { name: '文旅' },
                    'urban': { name: '城市更新' },
                    'other': { name: '其他' }
                };
                fund.sector_name = SECTOR_CONFIG[fund.sector]?.name || '其他';
            }
            
            // 实时计算溢价率和流通市值
            const premium = calculatePremium(fund.price, fund.nav);
            const marketCap = calculateMarketCap(fund.price, fund.circulating_shares);
            
            res.json({
                success: true,
                data: {
                    ...fund,
                    premium: premium !== null ? premium : fund.premium,
                    marketCap: marketCap !== null ? marketCap : fund.market_cap,
                    history: history.reverse() // 按时间正序
                }
            });
        });
    });
});

/**
 * GET /api/funds/:code/kline
 * 获取K线数据
 * Query: period=1d/1w/1m
 */
router.get('/:code/kline', (req, res) => {
    const { code } = req.params;
    const { period = '1d', limit = 100 } = req.query;
    
    // 日K
    const sql = `
        SELECT date, open, close, high, low, volume
        FROM price_history
        WHERE fund_code = ?
        ORDER BY date DESC
        LIMIT ?
    `;
    
    db.all(sql, [code, parseInt(limit) * (period === '1w' ? 5 : 1)], (err, data) => {
        if (err) {
            console.error('获取K线数据失败:', err);
            return res.status(500).json({
                success: false,
                error: err.message
            });
        }
        
        let result = data.reverse();
        
        // 周K数据聚合
        if (period === '1w') {
            result = aggregateWeeklyData(result);
        }
        
        res.json({
            success: true,
            period,
            data: result.slice(-parseInt(limit))
        });
    });
});

/**
 * 将日线数据聚合为周线数据
 */
function aggregateWeeklyData(dailyData) {
    const weeklyMap = new Map();
    
    dailyData.forEach(day => {
        const date = new Date(day.date);
        const year = date.getFullYear();
        const weekNum = getWeekNumber(date);
        const weekKey = `${year}-W${weekNum}`;
        
        if (!weeklyMap.has(weekKey)) {
            weeklyMap.set(weekKey, {
                date: day.date, // 周一日期
                open: day.open,
                close: day.close,
                high: day.high,
                low: day.low,
                volume: day.volume,
                _firstDate: date
            });
        } else {
            const week = weeklyMap.get(weekKey);
            // 更新周高低价
            week.high = Math.max(week.high, day.high);
            week.low = Math.min(week.low, day.low);
            // 更新收盘价（最后一天的收盘价）
            week.close = day.close;
            // 累计成交量
            week.volume += day.volume;
            // 保持最早的日期作为周一
            if (date < week._firstDate) {
                week._firstDate = date;
                week.date = day.date;
            }
        }
    });
    
    // 转换为数组并按日期排序
    return Array.from(weeklyMap.values())
        .map(week => ({
            date: week.date,
            open: week.open,
            close: week.close,
            high: week.high,
            low: week.low,
            volume: week.volume
        }))
        .sort((a, b) => new Date(a.date) - new Date(b.date));
}

/**
 * 获取日期所在的周数（ISO周数）
 */
function getWeekNumber(date) {
    const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
    const dayNum = d.getUTCDay() || 7;
    d.setUTCDate(d.getUTCDate() + 4 - dayNum);
    const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
    return Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
}

module.exports = router;
