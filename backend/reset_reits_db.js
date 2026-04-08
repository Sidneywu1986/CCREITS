/**
 * 重置REITs数据库 - 只保留20只基金
 * 运行: node reset_reits_db.js
 */

const sqlite3 = require('sqlite3').verbose();
const path = require('path');

// 20只基金数据（以图片为准）
const REITS_20 = [
    { code: "180101", name: "博时蛇口产园REIT", sector: "产业园区", sector_name: "产业园区" },
    { code: "180102", name: "华夏合肥高新REIT", sector: "产业园区", sector_name: "产业园区" },
    { code: "180103", name: "华夏和达高科REIT", sector: "产业园区", sector_name: "产业园区" },
    { code: "180105", name: "易方达广开产园REIT", sector: "产业园区", sector_name: "产业园区" },
    { code: "180106", name: "广发成都高投产业REIT", sector: "产业园区", sector_name: "产业园区" },
    { code: "180201", name: "平安广州广河REIT", sector: "transport", sector_name: "交通基础设施" },
    { code: "180202", name: "华夏越秀高速REIT", sector: "transport", sector_name: "交通基础设施" },
    { code: "180203", name: "招商高速公路REIT", sector: "transport", sector_name: "交通基础设施" },
    { code: "180301", name: "红土创新盐田港REIT", sector: "logistics", sector_name: "仓储物流" },
    { code: "180302", name: "华夏深国际REIT", sector: "logistics", sector_name: "仓储物流" },
    { code: "180303", name: "华泰宝湾物流REIT", sector: "logistics", sector_name: "仓储物流" },
    { code: "180305", name: "南方顺丰物流REIT", sector: "logistics", sector_name: "仓储物流" },
    { code: "180306", name: "华夏安博仓储REIT", sector: "logistics", sector_name: "仓储物流" },
    { code: "180401", name: "鹏华深圳能源REIT", sector: "energy", sector_name: "能源基础设施" },
    { code: "180402", name: "工银蒙能清洁能源REIT", sector: "energy", sector_name: "能源基础设施" },
    { code: "180501", name: "红土创新深圳安居REIT", sector: "housing", sector_name: "租赁住房" },
    { code: "180502", name: "招商基金蛇口租赁REIT", sector: "housing", sector_name: "租赁住房" },
    { code: "180601", name: "华夏华润商业REIT", sector: "consumer", sector_name: "消费基础设施" },
    { code: "180602", name: "中金印力消费REIT", sector: "consumer", sector_name: "消费基础设施" },
    { code: "180603", name: "华夏大悦城商业REIT", sector: "consumer", sector_name: "消费基础设施" }
];

const DB_PATH = path.join(__dirname, '..', '消费看板5（前端）', 'backend', 'database', 'reits.db');

async function resetDatabase() {
    const db = new sqlite3.Database(DB_PATH);
    
    console.log('🔄 开始重置数据库...');
    console.log(`📁 数据库路径: ${DB_PATH}`);
    
    return new Promise((resolve, reject) => {
        db.serialize(() => {
            // 1. 清空相关表（先清空有外键依赖的表）
            console.log('\n1️⃣ 清空行情数据表 (quotes)...');
            db.run("DELETE FROM quotes", (err) => {
                if (err) console.error('  清空quotes失败:', err.message);
                else console.log('  ✓ quotes表已清空');
            });
            
            console.log('2️⃣ 清空历史数据表 (price_history)...');
            db.run("DELETE FROM price_history", (err) => {
                if (err) console.error('  清空price_history失败:', err.message);
                else console.log('  ✓ price_history表已清空');
            });
            
            console.log('3️⃣ 清空公告表 (announcements)...');
            db.run("DELETE FROM announcements", (err) => {
                if (err) console.error('  清空announcements失败:', err.message);
                else console.log('  ✓ announcements表已清空');
            });
            
            console.log('4️⃣ 清空基金表 (funds)...');
            db.run("DELETE FROM funds", (err) => {
                if (err) console.error('  清空funds失败:', err.message);
                else console.log('  ✓ funds表已清空');
            });
            
            // 2. 重置自增ID（可选）
            db.run("DELETE FROM sqlite_sequence WHERE name IN ('funds', 'quotes', 'price_history', 'announcements')", (err) => {
                if (!err) console.log('  ✓ 自增ID已重置');
            });
            
            // 3. 插入20只基金数据
            console.log('\n5️⃣ 插入20只基金数据...');
            
            const stmt = db.prepare(`
                INSERT INTO funds (code, name, sector, sector_name, manager, listing_date, scale, property_type, remaining_years)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            `);
            
            let inserted = 0;
            REITS_20.forEach((fund, index) => {
                stmt.run(
                    fund.code,
                    fund.name,
                    fund.sector,
                    fund.sector_name,
                    '',  // manager
                    '',  // listing_date
                    0,   // scale
                    '',  // property_type
                    ''   // remaining_years
                , function(err) {
                    if (err) {
                        console.error(`  ✗ ${fund.code} ${fund.name} 插入失败:`, err.message);
                    } else {
                        inserted++;
                        process.stdout.write(`  ✓ ${fund.code} ${fund.name}\n`);
                    }
                    
                    if (inserted === REITS_20.length) {
                        console.log(`\n✅ 数据库重置完成！共插入 ${inserted} 只基金`);
                        console.log('\n📊 统计:');
                        
                        // 统计各板块数量
                        const sectors = {};
                        REITS_20.forEach(f => {
                            sectors[f.sector_name] = (sectors[f.sector_name] || 0) + 1;
                        });
                        
                        Object.entries(sectors).forEach(([name, count]) => {
                            console.log(`  ${name}: ${count}只`);
                        });
                        
                        stmt.finalize();
                        db.close();
                        resolve();
                    }
                });
            });
        });
    });
}

// 运行
resetDatabase().catch(err => {
    console.error('❌ 重置失败:', err);
    process.exit(1);
});
