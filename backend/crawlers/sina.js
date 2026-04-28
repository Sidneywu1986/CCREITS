/**
 * 新浪行情爬虫
 * 职责：获取实时价格、涨跌、成交量等基础行情
 */

const axios = require('axios');
const iconv = require('iconv-lite');
const { db } = require('../database/db');

const SOURCE_NAME = 'sina';

class SinaCrawler {
    async fetchData() {
        const codes = await this.getFundCodes();
        console.log(`[${SOURCE_NAME}] 获取 ${codes.length} 只基金行情`);
        
        // 分批请求（新浪限制URL长度）
        const batchSize = 50;
        const results = [];
        
        for (let i = 0; i < codes.length; i += batchSize) {
            const batch = codes.slice(i, i + batchSize);
            const data = await this.fetchBatch(batch);
            results.push(...data);
            
            // 延时避免请求过快
            if (i + batchSize < codes.length) {
                await new Promise(r => setTimeout(r, 500));
            }
        }
        
        return results;
    }

    async getFundCodes() {
        return new Promise((resolve, reject) => {
            db.all(
                "SELECT fund_code FROM business.funds WHERE status = 'active'",
                [],
                (err, rows) => {
                    if (err) {
                        reject(err);
                    } else {
                        const codes = rows.map(row => {
                            const prefix = row.fund_code.startsWith('5') ? 'sh' : 'sz';
                            return prefix + row.fund_code;
                        });
                        resolve(codes);
                    }
                }
            );
        });
    }

    async fetchBatch(codes) {
        const url = `https://hq.sinajs.cn/list=${codes.join(',')}`;
        
        try {
            const response = await axios.get(url, {
                responseType: 'arraybuffer',
                timeout: 10000,
                headers: {
                    'Referer': 'https://finance.sina.com.cn'
                }
            });
            
            const data = iconv.decode(response.data, 'gb2312');
            return this.parseData(data, codes);
        } catch (error) {
            console.error(`[${SOURCE_NAME}] 请求失败:`, error.message);
            return [];
        }
    }

    async saveToDatabase(quotes) {
        const today = new Date().toISOString().split('T')[0];
        let saved = 0;
        for (const q of quotes) {
            await new Promise((resolve, reject) => {
                db.run(`
                    INSERT INTO business.fund_prices
                    (fund_code, trade_date, close_price, change_pct, volume)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT (fund_code, trade_date) DO UPDATE SET
                    close_price = EXCLUDED.close_price, change_pct = EXCLUDED.change_pct,
                    volume = EXCLUDED.volume
                `, [q.fund_code, today, q.price, q.change_percent, q.volume],
                function(err) {
                    if (err) {
                        if (!err.message.includes('UNIQUE')) {
                            console.error(`[${SOURCE_NAME}] 保存失败 ${q.fund_code}:`, err.message);
                        }
                    } else {
                        saved++;
                    }
                    resolve();
                });
            });

            // 同步到 price_history
            await new Promise((resolve, reject) => {
                db.run(`
                    INSERT INTO business.price_history
                    (fund_code, trade_date, open_price, close_price, high_price, low_price, volume, amount, daily_return)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (fund_code, trade_date) DO UPDATE SET
                    open_price = EXCLUDED.open_price, close_price = EXCLUDED.close_price,
                    high_price = EXCLUDED.high_price, low_price = EXCLUDED.low_price,
                    volume = EXCLUDED.volume, amount = EXCLUDED.amount, daily_return = EXCLUDED.daily_return
                `, [q.fund_code, today, q.open, q.price, q.high, q.low, q.volume, q.amount, q.change_percent],
                function(err) {
                    if (err) {
                        if (!err.message.includes('UNIQUE') && !err.message.includes('duplicate')) {
                            console.error(`[${SOURCE_NAME}] price_history 保存失败 ${q.fund_code}:`, err.message);
                        }
                    }
                    resolve();
                });
            });
        }
        console.log(`[${SOURCE_NAME}] 保存 ${saved} 条日线数据`);
    }

    parseData(data, codes) {
        const results = [];
        
        for (const code of codes) {
            const match = data.match(new RegExp(`var hq_str_${code}="([^"]*)"`));
            if (!match || !match[1]) continue;
            
            const parts = match[1].split(',');
            if (parts.length < 10) continue;
            
            const pureCode = code.replace(/^(sh|sz)/, '');
            const price = parseFloat(parts[3]);
            const prevClose = parseFloat(parts[2]);
            
            // 只提供基础行情数据
            results.push({
                fund_code: pureCode,
                name: parts[0],
                price: price,
                open: parseFloat(parts[1]),
                high: parseFloat(parts[4]),
                low: parseFloat(parts[5]),
                prev_close: prevClose,
                volume: parseInt(parts[8]),
                amount: parseFloat(parts[9]) || null,
                change_percent: prevClose > 0 ? ((price - prevClose) / prevClose * 100) : 0,
                // 新浪不提供以下REITs特有数据
                nav: null,
                yield: null,
                debt_ratio: null,
                market_cap: null,
                // 元数据
                _source: SOURCE_NAME,
                _fetch_time: new Date().toISOString()
            });
        }
        
        return results;
    }
}

module.exports = SinaCrawler;
