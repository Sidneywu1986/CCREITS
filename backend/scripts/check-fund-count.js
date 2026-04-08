const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const DB_PATH = path.join(__dirname, '../database/reits.db');
const db = new sqlite3.Database(DB_PATH);

console.log('🔍 检查基金数量差异\n');

// 1. 基金表总数
db.get('SELECT COUNT(*) as count FROM funds', [], (err, row) => {
    console.log(`📊 funds表基金总数: ${row.count} 只`);
    
    // 2. 有行情的基金
    db.get(`
        SELECT COUNT(DISTINCT fund_code) as count 
        FROM quotes
    `, [], (err, row) => {
        console.log(`📈 quotes表有行情的基金: ${row.count} 只`);
        
        // 3. 找出没有行情的基金
        console.log('\n❌ 没有行情数据的基金:');
        db.all(`
            SELECT f.code, f.name, f.sector_name
            FROM funds f
            LEFT JOIN (SELECT DISTINCT fund_code FROM quotes) q ON f.code = q.fund_code
            WHERE q.fund_code IS NULL
        `, [], (err, rows) => {
            if (rows && rows.length > 0) {
                rows.forEach(row => {
                    console.log(`   ${row.code} | ${row.name} | ${row.sector_name}`);
                });
            } else {
                console.log('   所有基金都有行情数据');
            }
            
            console.log('\n✅ 检查完成');
            db.close();
        });
    });
});
