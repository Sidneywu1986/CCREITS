/**
 * 行情数据爬虫
 * 来源：新浪财经API（免费，无需认证）
 * 接口格式：https://hq.sinajs.cn/list=sh508056,sz180201
 */

const axios = require('axios');
const iconv = require('iconv-lite');
const { db, logUpdate, updateSourceStatus } = require('../database/db');

/**
 * 从数据库获取所有REITs基金代码
 */
async function getFundCodesFromDB() {
    return new Promise((resolve, reject) => {
        db.all(
            "SELECT code FROM funds WHERE status = 'listed' OR status IS NULL ORDER BY code",
            [],
            (err, rows) => {
                if (err) {
                    console.error('获取基金代码失败:', err);
                    reject(err);
                } else {
                    // 转换为新浪格式：上交所sh前缀，深交所sz前缀
                    const codes = rows.map(row => {
                        const code = row.code;
                        // 上交所REITs以5开头，深交所以1开头
                        const prefix = code.startsWith('5') ? 'sh' : 'sz';
                        return prefix + code;
                    });
                    resolve(codes);
                }
            }
        );
    });
}

/**
 * 解析新浪行情数据
 * 返回格式：var hq_str_sh508056="中金普洛斯REIT,4.215,4.200,4.215,4.230,4.200,4.215,4.216,85420,360269.6,508056,0.12,5.2,32.1,4.13,58.6";
 */
function parseSinaQuote(data, code) {
    const match = data.match(new RegExp(`var hq_str_${code}="([^"]*)"`));
    if (!match || !match[1]) return null;
    
    const parts = match[1].split(',');
    if (parts.length < 10) return null;
    
    // 提取纯数字代码
    const pureCode = code.replace(/^(sh|sz)/, '');
    
    // 计算涨跌幅
    const price = parseFloat(parts[3]);
    const prevClose = parseFloat(parts[2]);
    const changePercent = prevClose > 0 ? ((price - prevClose) / prevClose * 100) : 0;
    
    return {
        fund_code: pureCode,
        name: parts[0],               // 名称
        price: price,                 // 当前价
        open: parseFloat(parts[1]),   // 开盘价
        close: prevClose,             // 昨收
        high: parseFloat(parts[4]),   // 最高价
        low: parseFloat(parts[5]),    // 最低价
        volume: parseInt(parts[8]),   // 成交量
        change_percent: changePercent, // 计算涨跌幅
        // 以下字段新浪API不提供，保持为null等待其他数据源
        yield: null,
        debt_ratio: null,
        nav: null,
        market_cap: null
    };
}

/**
 * 保存行情数据到数据库
 */
async function saveQuotes(quotes) {
    for (const quote of quotes) {
        // 先确保基金记录存在（不覆盖已有信息）
        await new Promise((resolve, reject) => {
            db.run(
                `INSERT INTO business.funds (fund_code, fund_name, created_at)
                 VALUES (?, ?, CURRENT_TIMESTAMP) ON CONFLICT DO NOTHING`,
                [quote.fund_code, quote.name],
                (err) => {
                    if (err) reject(err);
                    else resolve();
                }
            );
        });
        
        // 更新基金的实时数据（仅当新数据有效时更新）
        if (quote.nav || quote.debt_ratio) {
            await new Promise((resolve, reject) => {
                db.run(
                    `UPDATE business.funds 
                     SET nav = COALESCE(?, nav),
                         debt_ratio = COALESCE(?, debt_ratio),
                         updated_at = CURRENT_TIMESTAMP
                     WHERE fund_code = ?`,
                    [quote.nav, quote.debt_ratio, quote.fund_code],
                    (err) => {
                        if (err) reject(err);
                        else resolve();
                    }
                );
            });
        }
        
        // 插入行情数据（溢价率、派息率、市值暂时为null）
        await new Promise((resolve, reject) => {
            db.run(
                `INSERT INTO business.quotes (fund_code, price, open_price, high_price, low_price, change_percent, volume, premium, yield, market_cap)
                 VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL)`,
                [quote.fund_code, quote.price, quote.open, quote.high, quote.low,
                 quote.change_percent, quote.volume],
                (err) => {
                    if (err) reject(err);
                    else resolve();
                }
            );
        });
        
        // 插入历史数据
        await new Promise((resolve, reject) => {
            db.run(
                `INSERT INTO business.price_history 
                 (fund_code, trade_date, open_price, close_price, high_price, low_price, volume)
                 VALUES (?, CURRENT_DATE, ?, ?, ?, ?, ?)
                 ON CONFLICT (fund_code, trade_date) DO UPDATE SET
                 open_price = EXCLUDED.open_price, close_price = EXCLUDED.close_price,
                 high_price = EXCLUDED.high_price, low_price = EXCLUDED.low_price,
                 volume = EXCLUDED.volume`,
                [quote.fund_code, quote.open, quote.price, quote.high, quote.low, quote.volume],
                (err) => {
                    if (err) reject(err);
                    else resolve();
                }
            );
        });
    }
}

/**
 * 爬取实时行情
 */
async function crawlPrices() {
    console.log('🚀 开始爬取行情数据...', new Date().toLocaleString());
    const startTime = Date.now();
    
    try {
        // 从数据库获取所有基金代码
        const fundCodes = await getFundCodesFromDB();
        console.log(`📊 从数据库获取 ${fundCodes.length} 只基金代码`);
        
        // 分批请求（每批20个）
        const batchSize = 20;
        const results = [];
        
        for (let i = 0; i < fundCodes.length; i += batchSize) {
            const batch = fundCodes.slice(i, i + batchSize);
            const codesStr = batch.join(',');
            
            const url = `https://hq.sinajs.cn/list=${codesStr}`;
            
            const response = await axios.get(url, {
                responseType: 'arraybuffer',
                headers: {
                    'Referer': 'https://finance.sina.com.cn',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                },
                timeout: 10000
            });
            
            // 解码GBK
            const html = iconv.decode(response.data, 'gb2312');
            
            // 解析每个基金
            for (const code of batch) {
                const quote = parseSinaQuote(html, code);
                if (quote) {
                    results.push(quote);
                }
            }
            
            // 防止请求过快
            await sleep(500);
        }
        
        // 保存到数据库
        await saveQuotes(results);
        
        const duration = Date.now() - startTime;
        console.log(`✅ 行情更新完成: ${results.length} 只基金, 耗时 ${duration}ms`);
        
        // 记录日志
        await logUpdate('price', 'sina-finance', 'success', results.length, duration);
        await updateSourceStatus('price', 'sina-finance', 'active');
        
        return results;
        
    } catch (error) {
        const duration = Date.now() - startTime;
        console.error('❌ 行情爬取失败:', error.message);
        
        await logUpdate('price', 'sina-finance', 'error', 0, duration, error.message);
        await updateSourceStatus('price', 'sina-finance', 'error', error.message);
        
        throw error;
    }
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// 如果直接运行此文件
if (require.main === module) {
    crawlPrices().then(() => {
        console.log('完成');
        process.exit(0);
    }).catch(err => {
        console.error(err);
        process.exit(1);
    });
}

module.exports = { crawlPrices };
