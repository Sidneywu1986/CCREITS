/**
 * 中央数据处理器
 * 职责：
 * 1. 接收各爬虫采集的原始数据
 * 2. 数据融合与冲突解决
 * 3. 数据质量校验
 * 4. 统一入库
 */

const { db } = require('../database/db');

// 数据源优先级配置
const SOURCE_PRIORITY = {
    'sina': { level: 1, name: '新浪财经' },      // 实时行情优先
    'tencent': { level: 1, name: '腾讯财经' },    // 实时行情优先
    'akshare': { level: 2, name: 'AKShare' },     // REITs数据优先
    'eastmoney': { level: 3, name: '东方财富' },  // 深度数据
    'juchao': { level: 4, name: '巨潮资讯' },     // 官方财务数据
};

// 字段优先级映射
const FIELD_PRIORITY = {
    // Level 1: 基础行情 - 取最新时间戳
    'price': ['sina', 'tencent', 'akshare'],
    'change_percent': ['sina', 'tencent', 'akshare'],
    'volume': ['sina', 'tencent', 'akshare'],
    
    // Level 2: REITs核心 - 优先官方数据源
    'nav': ['juchao', 'akshare', 'eastmoney'],
    'yield': ['juchao', 'akshare', 'eastmoney'],
    'debt_ratio': ['juchao', 'akshare'],
    'premium': ['akshare', 'eastmoney'],
    'market_cap': ['akshare', 'eastmoney'],
    
    // Level 3: 财务数据
    'revenue': ['juchao', 'akshare'],
    'profit': ['juchao', 'akshare'],
    'distributable': ['juchao', 'akshare'],
    
    // Level 4: 市场深度
    'main_inflow': ['eastmoney'],
    'institution_hold': ['eastmoney'],
    'turnover': ['eastmoney'],
};

class CentralProcessor {
    constructor() {
        this.dataCache = new Map(); // 临时数据缓存
        this.pendingData = []; // 待处理数据队列
    }

    /**
     * 接收爬虫数据
     * @param {string} source - 数据源标识
     * @param {Array} data - 数据数组
     */
    async receiveData(source, data) {
        console.log(`[中央处理器] 接收 ${source} 数据: ${data.length} 条`);
        
        for (const item of data) {
            const code = item.fund_code;
            if (!code) continue;
            
            // 为每个基金维护数据源快照
            if (!this.dataCache.has(code)) {
                this.dataCache.set(code, {});
            }
            
            const fundSnapshot = this.dataCache.get(code);
            
            // 记录数据来源和时间戳
            for (const [key, value] of Object.entries(item)) {
                if (value !== null && value !== undefined && value !== '') {
                    if (!fundSnapshot[key]) {
                        fundSnapshot[key] = [];
                    }
                    fundSnapshot[key].push({
                        source: source,
                        value: value,
                        timestamp: new Date().toISOString()
                    });
                }
            }
        }
    }

    /**
     * 融合数据 - 解决冲突
     */
    async fuseData() {
        const results = [];
        
        for (const [code, fields] of this.dataCache) {
            const fused = { fund_code: code };
            
            for (const [field, values] of Object.entries(fields)) {
                // 跳过基金代码等元数据
                if (field === 'fund_code' || field === 'name') {
                    fused[field] = values[0].value;
                    continue;
                }
                
                // 根据字段类型选择融合策略
                const fusedValue = this.resolveConflict(field, values);
                if (fusedValue !== null) {
                    fused[field] = fusedValue;
                }
            }
            
            results.push(fused);
        }
        
        return results;
    }

    /**
     * 冲突解决
     * @param {string} field - 字段名
     * @param {Array} values - 多数据源的值数组
     */
    resolveConflict(field, values) {
        if (!values || values.length === 0) return null;
        if (values.length === 1) return values[0].value;
        
        // 获取该字段的优先级列表
        const priority = FIELD_PRIORITY[field];
        
        if (priority) {
            // 按优先级排序
            const sorted = values.sort((a, b) => {
                const idxA = priority.indexOf(a.source);
                const idxB = priority.indexOf(b.source);
                return (idxA === -1 ? 999 : idxA) - (idxB === -1 ? 999 : idxB);
            });
            
            return sorted[0].value;
        }
        
        // 无优先级配置：取最新时间戳的
        const sorted = values.sort((a, b) => 
            new Date(b.timestamp) - new Date(a.timestamp)
        );
        return sorted[0].value;
    }

    /**
     * 数据质量校验
     */
    validateData(fusedData) {
        const validated = [];
        
        for (const fund of fusedData) {
            const errors = [];
            
            // 基础校验
            if (!fund.fund_code) {
                errors.push('缺少基金代码');
            }
            
            // 价格合理性校验
            if (fund.price !== undefined) {
                if (fund.price <= 0 || fund.price > 1000) {
                    errors.push(`价格异常: ${fund.price}`);
                    fund.price = null; // 标记为无效
                }
            }
            
            // 涨跌幅合理性校验
            if (fund.change_percent !== undefined) {
                if (Math.abs(fund.change_percent) > 20) {
                    errors.push(`涨跌幅异常: ${fund.change_percent}%`);
                }
            }
            
            // 净值与价格对比校验
            if (fund.nav && fund.price) {
                const premium = ((fund.price / fund.nav) - 1) * 100;
                if (Math.abs(premium) > 50) {
                    console.warn(`[校验警告] ${fund.fund_code} 溢折价异常: ${premium.toFixed(2)}%`);
                }
            }
            
            if (errors.length > 0) {
                console.warn(`[数据质量] ${fund.fund_code}:`, errors.join(', '));
            }
            
            validated.push(fund);
        }
        
        return validated;
    }

    /**
     * 统一入库
     */
    async saveToDatabase(fusedData) {
        const stats = { success: 0, failed: 0, skipped: 0 };
        
        for (const fund of fusedData) {
            try {
                await this.saveFundQuote(fund);
                await this.saveFundInfo(fund);
                await this.savePriceHistory(fund);
                stats.success++;
            } catch (error) {
                console.error(`[入库失败] ${fund.fund_code}:`, error.message);
                stats.failed++;
            }
        }
        
        console.log(`[入库完成] 成功: ${stats.success}, 失败: ${stats.failed}`);
        return stats;
    }

    /**
     * 保存行情数据
     */
    async saveFundQuote(fund) {
        return new Promise((resolve, reject) => {
            const premium = fund.nav && fund.price 
                ? ((fund.price / fund.nav) - 1) * 100 
                : null;
            
            db.run(
                `INSERT INTO quotes 
                (fund_code, price, open, high, low, prev_close, change_percent, volume, premium, yield, market_cap)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
                [
                    fund.fund_code,
                    fund.price || null,
                    fund.open || null,
                    fund.high || null,
                    fund.low || null,
                    fund.close || fund.prev_close || null,
                    fund.change_percent || null,
                    fund.volume || null,
                    premium,
                    fund.yield || null,
                    fund.market_cap || null
                ],
                (err) => {
                    if (err) reject(err);
                    else resolve();
                }
            );
        });
    }

    /**
     * 更新基金基本信息
     */
    async saveFundInfo(fund) {
        return new Promise((resolve, reject) => {
            // 使用 COALESCE 保留已有值
            db.run(
                `UPDATE funds 
                SET name = COALESCE(?, name),
                    nav = COALESCE(?, nav),
                    debt_ratio = COALESCE(?, debt_ratio),
                    updated_at = datetime('now')
                WHERE code = ?`,
                [fund.name, fund.nav, fund.debt_ratio, fund.fund_code],
                (err) => {
                    if (err) reject(err);
                    else resolve();
                }
            );
        });
    }

    /**
     * 保存历史价格
     */
    async savePriceHistory(fund) {
        if (!fund.price) return;
        
        return new Promise((resolve, reject) => {
            db.run(
                `INSERT OR REPLACE INTO price_history 
                (fund_code, date, open, close, high, low, volume)
                VALUES (?, date('now'), ?, ?, ?, ?, ?)`,
                [
                    fund.fund_code,
                    fund.open || fund.price,
                    fund.price,
                    fund.high || fund.price,
                    fund.low || fund.price,
                    fund.volume || 0
                ],
                (err) => {
                    if (err) reject(err);
                    else resolve();
                }
            );
        });
    }

    /**
     * 清空缓存
     */
    clearCache() {
        this.dataCache.clear();
    }

    /**
     * 主流程
     */
    async process() {
        console.log('[中央处理器] 开始数据融合...');
        
        // 1. 融合数据
        const fusedData = await this.fuseData();
        console.log(`[中央处理器] 融合完成: ${fusedData.length} 条`);
        
        // 2. 质量校验
        const validatedData = this.validateData(fusedData);
        
        // 3. 入库
        const stats = await this.saveToDatabase(validatedData);
        
        // 4. 清空缓存
        this.clearCache();
        
        return stats;
    }
}

module.exports = CentralProcessor;
