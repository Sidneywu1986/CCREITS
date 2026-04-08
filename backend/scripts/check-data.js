const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const DB_PATH = path.join(__dirname, '../database/reits.db');
const db = new sqlite3.Database(DB_PATH);

console.log('🔍 检查数据库数据情况...\n');

// 1. 检查基金数量
db.get('SELECT COUNT(*) as count FROM funds', [], (err, row) => {
    if (err) {
        console.error('❌ 查询失败:', err);
        return;
    }
    console.log(`📊 基金总数: ${row.count} 只`);
    
    // 2. 检查有净值数据的基金
    db.get("SELECT COUNT(*) as count FROM funds WHERE nav IS NOT NULL AND nav > 0", [], (err, row) => {
        console.log(`📈 有净值数据的基金: ${row.count} 只`);
        
        // 3. 检查有流通份额的基金
        db.get("SELECT COUNT(*) as count FROM funds WHERE circulating_shares IS NOT NULL AND circulating_shares > 0", [], (err, row) => {
            console.log(`💰 有流通份额的基金: ${row.count} 只`);
            
            // 4. 显示部分基金数据示例
            console.log('\n📋 部分基金数据示例:');
            db.all(`
                SELECT code, name, nav, circulating_shares, debt_ratio, institution_hold 
                FROM funds 
                LIMIT 5
            `, [], (err, rows) => {
                if (err) {
                    console.error('❌ 查询失败:', err);
                } else {
                    rows.forEach(row => {
                        console.log(`  ${row.code} | ${row.name.substring(0, 10).padEnd(10)} | 净值:${row.nav || '--'} | 份额:${row.circulating_shares || '--'}`);
                    });
                }
                
                // 5. 检查实时行情数据
                console.log('\n📈 实时行情数据:');
                db.get('SELECT COUNT(*) as count FROM quotes', [], (err, row) => {
                    console.log(`  行情记录数: ${row.count} 条`);
                    
                    db.all(`
                        SELECT q.fund_code, f.name, q.price, q.change_percent, q.updated_at
                        FROM quotes q
                        JOIN funds f ON q.fund_code = f.code
                        ORDER BY q.id DESC
                        LIMIT 3
                    `, [], (err, rows) => {
                        if (!err && rows.length > 0) {
                            rows.forEach(row => {
                                console.log(`  ${row.fund_code} ${row.name.substring(0, 8)} 价格:${row.price} 涨跌:${row.change_percent}%`);
                            });
                        }
                        
                        console.log('\n✅ 数据检查完成');
                        db.close();
                    });
                });
            });
        });
    });
});
