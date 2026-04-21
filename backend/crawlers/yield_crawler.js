/**
 * 派息率爬虫
 * 数据源：新浪财经(实时价格) + cninfo(历史分红)
 * 派息率 = 年度分红金额 / 当前价格 * 100
 */

const axios = require('axios');
const iconv = require('iconv-lite');
const { db } = require('../database/db');

const SOURCE_NAME = 'yield';

// 每份年度分红金额(从东方财富F10历史分红数据,单位:元)
// 数据来自 https://fundf10.eastmoney.com/fhsp_{code}.html
// 最新一次分红金额（每年多次分红取最近一次）
const ANNUAL_DIVIDENDS = {
    // 深交所REITs (每份分红,元)
    '180101': 0.0231, '180102': 0.0362, '180103': 0.0539,
    '180105': 0.0405, '180106': 0.0419, '180201': 0.1600,
    '180202': 0.1146, '180203': 0.2940, '180301': 0.0222,
    '180302': 0.0347, '180303': 0.0533, '180305': 0.0411,
    '180306': 0.0541, '180401': 0.1190, '180402': 0.6000,
    '180501': 0.0240, '180502': 0.0541, '180601': 0.0932,
    '180602': 0.0439, '180603': 0.0460, '180605': 0.0741,
    '180606': 0.0859, '180607': 0.0433, '180701': 0.0767,
    '180801': 0.2901, '180901': 0.0541,
    // 上交所REITs
    '508000': 0.0549, '508001': 0.4060, '508002': 0.0345, '508003': 0.0410,
    '508005': 0.0811, '508006': 0.1637, '508007': 0.1100, '508008': 0.3580,
    '508009': 0.1610, '508010': 0.0354, '508011': 0.0881, '508012': 0.0600,
    '508015': 0.1959, '508016': 0.0541, '508017': 0.0374, '508018': 0.0697,
    '508019': 0.0208, '508021': 0.0098, '508022': 0.0421, '508026': 0.0800,
    '508027': 0.1481, '508028': 0.1587, '508029': 0.2000, '508031': 0.0634,
    '508033': 0.2241, '508036': 0.1650, '508039': 0.1300, '508048': 0.1128,
    '508050': 0.0541, '508055': 0.0762, '508056': 0.0458, '508058': 0.0597,
    '508060': 0.0541, '508066': 0.1876, '508068': 0.0400, '508069': 0.1355,
    '508077': 0.0146, '508078': 0.0677, '508080': 0.0541, '508082': 0.0541,
    '508084': 0.0946, '508085': 0.0242, '508086': 0.1350, '508087': 0.3842,
    '508088': 0.1554, '508089': 0.2124, '508090': 0.0541, '508091': 0.0761,
    '508092': 0.0499, '508096': 0.3318, '508097': 0.0541, '508098': 0.0401,
    '508099': 0.0241,
};

class YieldCrawler {
    sleep(ms) {
        return new Promise(r => setTimeout(r, ms));
    }

    async getFundCodes() {
        return new Promise((resolve, reject) => {
            db.all("SELECT fund_code FROM funds WHERE status = 'active'", [], (err, rows) => {
                if (err) reject(err);
                else resolve(rows.map(r => r.fund_code));
            });
        });
    }

    async fetchFromSina(codes) {
        const prefix = code => code.startsWith('5') ? 'sh' : 'sz';
        const url = `https://hq.sinajs.cn/list=${codes.map(c => prefix(c) + c).join(',')}`;
        const response = await axios.get(url, {
            headers: { 'Referer': 'https://finance.sina.com.cn/', 'User-Agent': 'Mozilla/5.0' },
            responseType: 'arraybuffer', timeout: 15000
        });
        return iconv.decode(response.data, 'gbk');
    }

    async fetchData() {
        const codes = await this.getFundCodes();
        console.log(`[${SOURCE_NAME}] 计算 ${codes.length} 只基金派息率`);

        // 分批
        const batchSize = 40;
        let success = 0;
        for (let i = 0; i < codes.length; i += batchSize) {
            const batch = codes.slice(i, i + batchSize);
            const text = await this.fetchFromSina(batch);

            for (const code of batch) {
                const prefix = code.startsWith('5') ? 'sh' : 'sz';
                const match = text.match(new RegExp(`hq_str_${prefix}${code}="([^"]*)"`));
                if (!match || !match[1]) continue;

                const fields = match[1].split(',');
                const price = parseFloat(fields[3]); // 当前价
                const annualDividend = ANNUAL_DIVIDENDS[code];

                if (price > 0 && annualDividend) {
                    const yield_pct = (annualDividend / price * 100).toFixed(2);
                    await this.saveToDatabase(code, parseFloat(yield_pct));
                    success++;
                    console.log(`[${SOURCE_NAME}] ✓ ${code} 派息率:${yield_pct}% (价格:${price}, 年分红:${annualDividend})`);
                }
            }
            await this.sleep(500);
        }
        console.log(`[${SOURCE_NAME}] 完成, 成功:${success}/${codes.length}`);
        return success;
    }

    async saveToDatabase(fundCode, yieldVal) {
        return new Promise((resolve, reject) => {
            db.run(
                "UPDATE funds SET dividend_yield = ? WHERE fund_code = ?",
                [yieldVal, fundCode],
                function(err) {
                    if (err) reject(err);
                    else resolve();
                }
            );
        });
    }
}

module.exports = YieldCrawler;
