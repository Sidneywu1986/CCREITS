/**
 * 测试溢价率和流通市值计算
 */

const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const DB_PATH = path.join(__dirname, '../database/reits.db');
const db = new sqlite3.Database(DB_PATH);

console.log('🧮 测试溢价率和流通市值计算\n');

// 获取几只基金的数据进行测试
db.all(`
    SELECT 
        f.code, f.name, f.nav, f.circulating_shares,
        q.price, q.market_cap as db_market_cap, q.premium as db_premium
    FROM funds f
    LEFT JOIN quotes q ON f.code = q.fund_code
    WHERE q.id = (SELECT MAX(id) FROM quotes WHERE fund_code = f.code)
    LIMIT 5
`, [], (err, rows) => {
    if (err) {
        console.error('❌ 查询失败:', err);
        db.close();
        return;
    }

    console.log('📊 计算结果对比:\n');
    console.log('代码    | 名称      | 价格   | 净值   | 计算溢价率 | 数据溢价率 | 计算市值   | 数据市值');
    console.log('--------|----------|--------|--------|-----------|-----------|-----------|----------');

    rows.forEach(row => {
        // 计算溢价率
        let calcPremium = null;
        if (row.price && row.nav && row.nav > 0) {
            calcPremium = ((row.price - row.nav) / row.nav * 100).toFixed(2);
        }

        // 计算流通市值
        let calcMarketCap = null;
        if (row.price && row.circulating_shares) {
            calcMarketCap = (row.price * row.circulating_shares / 10000).toFixed(2);
        }

        console.log(
            `${row.code} | ${row.name.substring(0, 8).padEnd(8)} | ` +
            `${row.price ? row.price.toFixed(3) : '--'} | ` +
            `${row.nav ? row.nav.toFixed(3) : '--'} | ` +
            `${calcPremium ? calcPremium + '%' : '--'.padEnd(9)} | ` +
            `${row.db_premium ? row.db_premium.toFixed(2) + '%' : '--'.padEnd(9)} | ` +
            `${calcMarketCap ? calcMarketCap + '亿' : '--'.padEnd(9)} | ` +
            `${row.db_market_cap ? row.db_market_cap.toFixed(2) + '亿' : '--'}`
        );
    });

    console.log('\n✅ 测试完成');
    console.log('\n💡 说明:');
    console.log('  - 计算溢价率 = (价格 - 净值) / 净值 * 100%');
    console.log('  - 计算市值 = 价格 * 流通份额 / 10000 (转为亿元)');
    console.log('  - 如果净值或流通份额为null，则无法计算');
    
    db.close();
});
