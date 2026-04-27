/**
 * 大盘指数爬虫
 * 获取：中证REITs全收益、上证指数、中证红利、10年期国债收益率
 */

const axios = require('axios');
const iconv = require('iconv-lite');
const { db, logUpdate, updateSourceStatus } = require('../database/db');

const SOURCE_NAME = 'sina-index';

// 指数代码映射
const INDEX_CODES = {
    // 中证REITs全收益指数 (实际代码可能是H30207或自定义)
    'reits_total': { sinaCode: 'sh000001', name: '中证REITs全收益', fallbackValue: 1013.78 },
    // 上证指数
    'sh_index': { sinaCode: 'sh000001', name: '上证指数' },
    // 中证红利
    'dividend': { sinaCode: 'sh000922', name: '中证红利' },
    // 10年期国债收益率 (东方财富或新浪财经有)
    'bond_yield': { sinaCode: 's_sh000001', name: '10年期国债收益率' }
};

class MarketIndexCrawler {
    async fetchData() {
        console.log(`[${SOURCE_NAME}] 开始获取大盘指数数据...`);
        
        const results = [];
        
        // 获取上证指数和中证红利
        const stockIndices = await this.fetchStockIndices();
        results.push(...stockIndices);
        
        // 获取国债收益率
        const bondYield = await this.fetchBondYield();
        if (bondYield) results.push(bondYield);
        
        // 获取中证REITs指数 (如有真实代码可替换)
        const reitsIndex = await this.fetchREITsIndex();
        if (reitsIndex) results.push(reitsIndex);
        
        console.log(`[${SOURCE_NAME}] 获取完成: ${results.length} 条数据`);
        return results;
    }
    
    // 获取股票指数
    async fetchStockIndices() {
        const results = [];
        
        // 1. 获取上证指数（新浪财经）
        const shIndex = await this.fetchShIndex();
        if (shIndex) results.push(shIndex);
        
        // 2. 获取中证红利（东方财富）
        const dividendIndex = await this.fetchDividendIndex();
        if (dividendIndex) results.push(dividendIndex);
        
        return results;
    }
    
    // 获取上证指数
    async fetchShIndex() {
        const url = 'https://hq.sinajs.cn/list=sh000001';
        
        try {
            const response = await axios.get(url, {
                responseType: 'arraybuffer',
                timeout: 10000,
                headers: { 'Referer': 'https://finance.sina.com.cn' }
            });
            
            const data = iconv.decode(response.data, 'gb2312');
            const match = data.match(/var hq_str_sh000001="([^"]*)"/);
            if (!match || !match[1]) return null;
            
            const parts = match[1].split(',');
            if (parts.length < 10) return null;
            
            const name = parts[0];
            const price = parseFloat(parts[3]);
            const prevClose = parseFloat(parts[2]);
            const changePercent = prevClose > 0 ? ((price - prevClose) / prevClose * 100) : 0;
            
            return {
                code: 'sh_index',
                name: name,
                value: price,
                change: price - prevClose,
                changePercent: changePercent,
                source: SOURCE_NAME,
                updateTime: new Date().toISOString()
            };
        } catch (error) {
            console.error(`[${SOURCE_NAME}] 上证指数获取失败:`, error.message);
            return null;
        }
    }
    
    // 获取中证红利指数（东方财富数据源）
    async fetchDividendIndex() {
        // 东方财富API: 1.000922 表示上海市场000922
        const url = 'https://push2.eastmoney.com/api/qt/stock/get?secid=1.000922&fields=f43,f44,f45,f46,f47,f48,f57,f58,f60,f170';
        
        try {
            const response = await axios.get(url, {
                timeout: 10000,
                headers: { 
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            });
            
            const data = response.data;
            if (!data || !data.data) {
                console.error(`[${SOURCE_NAME}] 中证红利数据格式异常`);
                return null;
            }
            
            const d = data.data;
            // f43: 当前价(需除以100), f60: 昨收(除以100), f170: 涨跌幅(除以100)
            const price = (d.f43 || 0) / 100;
            const prevClose = (d.f60 || 0) / 100;
            const changePercent = (d.f170 || 0) / 100;
            
            if (price === 0) {
                console.warn(`[${SOURCE_NAME}] 中证红利价格为0，可能非交易时间`);
                return null;
            }
            
            return {
                code: 'dividend',
                name: d.f58 || '中证红利',
                value: price,
                change: price - prevClose,
                changePercent: changePercent,
                source: 'eastmoney',
                updateTime: new Date().toISOString()
            };
        } catch (error) {
            console.error(`[${SOURCE_NAME}] 中证红利获取失败:`, error.message);
            return null;
        }
    }
    
    // 获取国债收益率 (从东方财富或新浪财经)
    async fetchBondYield() {
        try {
            // 尝试从新浪财经获取国债相关数据
            // 10年期国债收益率代码可能需要查询
            // 这里先返回模拟数据，实际部署时需要找到正确数据源
            
            // TODO: 找到真实的数据源URL
            // 目前先使用模拟数据，但格式正确
            return {
                code: 'bond_yield',
                name: '10年期国债收益率',
                value: 1.83,  // 单位：%
                change: -0.02,
                changePercent: -0.24,
                source: SOURCE_NAME,
                updateTime: new Date().toISOString()
            };
        } catch (error) {
            console.error(`[${SOURCE_NAME}] 国债收益率获取失败:`, error.message);
            return null;
        }
    }
    
    // 获取中证REITs指数
    async fetchREITsIndex() {
        // 中证REITs指数代码可能是 H30207 或 932006
        // 由于是新指数，可能新浪财经暂未收录
        // 这里可以先计算一个基于成分股的模拟值，或使用固定值
        
        try {
            // 尝试获取，如失败则使用基于REITs基金计算的模拟值
            const url = 'https://hq.sinajs.cn/list=sh932006';
            const response = await axios.get(url, {
                responseType: 'arraybuffer',
                timeout: 5000,
                headers: { 'Referer': 'https://finance.sina.com.cn' }
            });
            
            const data = iconv.decode(response.data, 'gb2312');
            const match = data.match(/var hq_str_sh932006="([^"]*)"/);
            
            if (match && match[1] && match[1] !== '') {
                const parts = match[1].split(',');
                const price = parseFloat(parts[3]);
                const prevClose = parseFloat(parts[2]);
                const changePercent = prevClose > 0 ? ((price - prevClose) / prevClose * 100) : 0;
                
                return {
                    code: 'reits_total',
                    name: '中证REITs全收益',
                    value: price,
                    change: price - prevClose,
                    changePercent: changePercent,
                    source: SOURCE_NAME,
                    updateTime: new Date().toISOString()
                };
            }
        } catch (e) {
            // 忽略错误，使用计算值
        }
        
        // 如果没有真实数据源，基于REITs基金计算一个加权指数
        return this.calculateREITsIndex();
    }
    
    // 基于REITs基金计算模拟指数
    async calculateREITsIndex() {
        try {
            // 从数据库获取所有REITs的最新行情
            const quotes = await new Promise((resolve, reject) => {
                db.all(`
                    SELECT q.fund_code, q.price, q.change_percent
                    FROM business.quotes q
                    INNER JOIN (
                        SELECT fund_code, MAX(id) as max_id 
                        FROM business.quotes 
                        GROUP BY fund_code
                    ) latest ON q.fund_code = latest.fund_code AND q.id = latest.max_id
                `, [], (err, rows) => {
                    if (err) reject(err);
                    else resolve(rows);
                });
            });
            
            if (!quotes || quotes.length === 0) {
                return null;
            }
            
            // 简单平均涨跌幅作为指数涨跌幅
            const avgChange = quotes.reduce((sum, q) => sum + (q.change_percent || 0), 0) / quotes.length;
            
            // 基准值1013.78，根据涨跌幅调整
            const baseValue = 1013.78;
            const currentValue = baseValue * (1 + avgChange / 100);
            
            return {
                code: 'reits_total',
                name: '中证REITs全收益',
                value: parseFloat(currentValue.toFixed(2)),
                change: parseFloat((currentValue - baseValue).toFixed(2)),
                changePercent: parseFloat(avgChange.toFixed(2)),
                source: 'calculated',
                updateTime: new Date().toISOString()
            };
        } catch (error) {
            console.error('计算REITs指数失败:', error);
            return null;
        }
    }
    
    // 保存到数据库
    async saveToDatabase(data) {
        for (const item of data) {
            try {
                await new Promise((resolve, reject) => {
                    db.run(`
                        INSERT INTO business.market_indices (code, name, value, change, change_percent, source, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, NOW())
                        ON CONFLICT(code) DO UPDATE SET
                            value = excluded.value,
                            change = excluded.change,
                            change_percent = excluded.change_percent,
                            source = excluded.source,
                            updated_at = excluded.updated_at
                    `, [item.code, item.name, item.value, item.change, item.changePercent, item.source], 
                    (err) => {
                        if (err) reject(err);
                        else resolve();
                    });
                });
                
                console.log(`[${SOURCE_NAME}] 已更新 ${item.name}: ${item.value}`);
            } catch (error) {
                console.error(`[${SOURCE_NAME}] 保存 ${item.code} 失败:`, error);
            }
        }
    }
}

module.exports = MarketIndexCrawler;
