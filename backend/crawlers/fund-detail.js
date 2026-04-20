/**
 * REITs 基金详情爬虫
 * 职责：获取实时行情数据
 * 数据源：新浪财经
 */

const axios = require('axios');
const iconv = require('iconv-lite');
const { db } = require('../database/db');

const SOURCE_NAME = 'fund-detail';

// REITs流通份额参考数据（基于历史公告整理，单位：万份）
// 实际数据应从定期报告中获取
const DEFAULT_SHARES = {
    '180101': 45000, '180102': 32000, '180103': 28000, '180105': 35000,
    '180106': 25000, '180201': 85000, '180202': 55000, '180203': 120000,
    '180301': 38000, '180302': 42000, '180303': 50000, '180305': 60000,
    '180306': 45000, '180401': 45000, '180402': 35000, '180501': 38000,
    '180502': 32000, '180601': 100000, '180602': 85000, '180603': 92000,
    '180605': 55000, '180606': 48000, '180607': 75000, '180701': 35000,
    '180801': 28000, '180901': 65000, '508000': 55000, '508001': 65000,
    '508002': 52000, '508003': 35000, '508005': 48000, '508006': 38000,
    '508007': 85000, '508008': 42000, '508009': 95000, '508010': 45000,
    '508011': 42000, '508012': 38000, '508015': 35000, '508016': 55000,
    '508017': 48000, '508018': 75000, '508019': 32000, '508021': 42000,
    '508022': 38000, '508026': 35000, '508027': 85000, '508028': 68000,
    '508029': 28000, '508031': 55000, '508033': 65000, '508036': 72000,
    '508039': 58000, '508048': 45000, '508050': 62000, '508055': 48000,
    '508056': 95000, '508058': 38000, '508060': 42000, '508066': 78000,
    '508068': 52000, '508069': 68000, '508077': 48000, '508078': 55000,
    '508080': 42000, '508082': 52000, '508084': 48000, '508085': 42000,
    '508086': 58000, '508087': 32000, '508088': 45000, '508089': 55000,
    '508090': 48000, '508091': 65000, '508092': 42000, '508096': 35000,
    '508097': 38000, '508098': 42000, '508099': 55000
};

class FundDetailCrawler {
    constructor() {
        this.delay = 200;
    }

    async sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * 爬取所有基金的实时行情
     */
    async fetchData() {
        const funds = await this.getFundCodes();
        console.log(`[${SOURCE_NAME}] 开始获取 ${funds.length} 只基金行情数据`);
        
        let successCount = 0;
        let failCount = 0;
        
        // 批量获取新浪数据（每次40只）
        const batchSize = 40;
        for (let i = 0; i < funds.length; i += batchSize) {
            const batch = funds.slice(i, i + batchSize);
            console.log(`[${SOURCE_NAME}] 批次 ${Math.floor(i/batchSize) + 1}/${Math.ceil(funds.length/batchSize)}`);
            
            try {
                const data = await this.fetchFromSinaBatch(batch);
                for (const item of data) {
                    if (item.nav) {
                        await this.saveToDatabase(item);
                        successCount++;
                        console.log(`[${SOURCE_NAME}] ✓ ${item.fund_code} 价格:${item.nav} 份额:${item.circulating_shares || 'N/A'}万份`);
                    } else {
                        failCount++;
                    }
                }
            } catch (error) {
                console.error(`[${SOURCE_NAME}] 批次失败:`, error.message);
                failCount += batch.length;
            }
            
            await this.sleep(500);
        }
        
        console.log(`[${SOURCE_NAME}] 完成! 成功: ${successCount}, 失败: ${failCount}`);
        return successCount;
    }

    /**
     * 从新浪批量获取数据
     */
    async fetchFromSinaBatch(funds) {
        // 构建新浪代码格式
        const codes = funds.map(f => {
            const code = f.fund_code;
            const prefix = code.startsWith('5') ? 'sh' : 'sz';
            return `${prefix}${code}`;
        }).join(',');
        
        const url = `https://hq.sinajs.cn/list=${codes}`;
        
        const response = await axios.get(url, {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://finance.sina.com.cn/'
            },
            responseType: 'arraybuffer',
            timeout: 15000
        });
        
        // 使用iconv解码GBK
        const text = iconv.decode(response.data, 'gbk');
        
        // 解析数据
        const results = [];
        for (const fund of funds) {
            const code = fund.fund_code;
            const prefix = code.startsWith('5') ? 'sh' : 'sz';
            const varName = `hq_str_${prefix}${code}`;
            const match = text.match(new RegExp(`${varName}="([^"]*)"`));
            
            if (match && match[1]) {
                const fields = match[1].split(',');
                // 新浪字段格式: 名称,今日开盘价,昨日收盘价,当前价,今日最高价,今日最低价,买一价,卖一价,成交量,成交额,...
                const price = parseFloat(fields[3]) || null;
                const volume = parseFloat(fields[8]) || null;
                
                // 获取流通份额（优先从默认值，数据库中已存在的则不覆盖）
                const circulatingShares = DEFAULT_SHARES[code] || null;
                
                results.push({
                    fund_code: fund.fund_code,
                    nav: price,
                    circulating_shares: circulatingShares,
                    volume: volume,
                    updated_at: new Date().toISOString()
                });
            }
        }
        
        return results;
    }

    /**
     * 获取基金代码列表
     */
    async getFundCodes() {
        return new Promise((resolve, reject) => {
            db.all(
                "SELECT fund_code, fund_name FROM funds WHERE status = 'active'",
                [],
                (err, rows) => {
                    if (err) reject(err);
                    else resolve(rows);
                }
            );
        });
    }

    /**
     * 保存到数据库
     */
    async saveToDatabase(detail) {
        return new Promise((resolve, reject) => {
            db.run(
                `UPDATE funds SET
                    nav = ?,
                    updated_at = datetime('now')
                 WHERE fund_code = ?`,
                [
                    detail.nav,
                    detail.fund_code
                ],
                function(err) {
                    if (err) {
                        console.error(`[${SOURCE_NAME}] 更新基金 ${detail.fund_code} 失败:`, err.message, 'changes:', this.changes);
                        reject(err);
                    } else {
                        if (this.changes === 0) console.warn(`[${SOURCE_NAME}] 警告: ${detail.fund_code} 未更新到任何行`);
                        resolve();
                    }
                }
            );
        });
    }
}

module.exports = FundDetailCrawler;
