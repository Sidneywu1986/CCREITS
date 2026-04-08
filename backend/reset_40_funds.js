/**
 * 重置REITs数据库 - 40只基金完整版
 * 运行: node reset_40_funds.js
 */

const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const fs = require('fs');

// 40只基金完整数据
const REITS_40 = [
    // 第1-20只: 深交所 (180开头)
    { code: "180101", name: "博时蛇口产园REIT", sector: "industrial", sector_name: "产业园区" },
    { code: "180102", name: "华夏合肥高新REIT", sector: "industrial", sector_name: "产业园区" },
    { code: "180103", name: "华夏和达高科REIT", sector: "industrial", sector_name: "产业园区" },
    { code: "180105", name: "易方达广开产园REIT", sector: "industrial", sector_name: "产业园区" },
    { code: "180106", name: "广发成都高投产业REIT", sector: "industrial", sector_name: "产业园区" },
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
    { code: "180603", name: "华夏大悦城商业REIT", sector: "consumer", sector_name: "消费基础设施" },
    
    // 第21-40只
    { code: "180605", name: "易方达华威市场REIT", sector: "consumer", sector_name: "消费基础设施" },
    { code: "180606", name: "中金中国绿发商业REIT", sector: "consumer", sector_name: "消费基础设施" },
    { code: "180607", name: "华夏中海商业REIT", sector: "consumer", sector_name: "消费基础设施" },
    { code: "180701", name: "银华绍兴原水水利REIT", sector: "water", sector_name: "水利设施" },
    { code: "180801", name: "中航首钢绿能REIT", sector: "eco", sector_name: "生态环保" },
    { code: "180901", name: "南方润泽科技数据中心REIT", sector: "datacenter", sector_name: "数据中心" },
    { code: "180503", name: "中航北京昌保租赁REIT", sector: "housing", sector_name: "租赁住房" },
    { code: "508000", name: "华安张江产业园REIT", sector: "industrial", sector_name: "产业园区" },
    { code: "508001", name: "浙商沪杭甬REIT", sector: "transport", sector_name: "交通基础设施" },
    { code: "508002", name: "华安百联消费REIT", sector: "consumer", sector_name: "消费基础设施" },
    { code: "508003", name: "中金联东科创REIT", sector: "industrial", sector_name: "产业园区" },
    { code: "508005", name: "华夏首创奥莱REIT", sector: "consumer", sector_name: "消费基础设施" },
    { code: "508006", name: "富国首创水务REIT", sector: "eco", sector_name: "生态环保" },
    { code: "508007", name: "中金山东高速REIT", sector: "transport", sector_name: "交通基础设施" },
    { code: "508008", name: "国金中国铁建REIT", sector: "logistics", sector_name: "仓储物流" },
    { code: "508009", name: "中金安徽交控REIT", sector: "transport", sector_name: "交通基础设施" },
    { code: "508010", name: "中金重庆两江REIT", sector: "industrial", sector_name: "产业园区" },
    { code: "508011", name: "嘉实物美消费REIT", sector: "consumer", sector_name: "消费基础设施" },
    { code: "508012", name: "招商科创REIT", sector: "industrial", sector_name: "产业园区" },
    { code: "508015", name: "中信建投明阳智能REIT", sector: "energy", sector_name: "能源基础设施" }
];

const DB_PATH = path.join(__dirname, '..', '消费看板5（前端）', 'backend', 'database', 'reits.db');

async function resetDatabase() {
    console.log('🔄 开始重置数据库为40只基金...');
    console.log(`📁 数据库路径: ${DB_PATH}`);
    
    const db = new sqlite3.Database(DB_PATH);
    
    return new Promise((resolve, reject) => {
        db.serialize(() => {
            // 1. 清空所有表
            console.log('\n1️⃣ 清空数据表...');
            db.run("DELETE FROM quotes");
            db.run("DELETE FROM price_history");
            db.run("DELETE FROM announcements");
            db.run("DELETE FROM funds");
            db.run("DELETE FROM sqlite_sequence WHERE name IN ('funds', 'quotes', 'price_history', 'announcements')");
            console.log('   ✓ 所有表已清空');
            
            // 2. 插入40只基金
            console.log('\n2️⃣ 插入40只基金数据...');
            
            const stmt = db.prepare(`
                INSERT INTO funds (code, name, sector, sector_name) 
                VALUES (?, ?, ?, ?)
            `);
            
            let count = 0;
            REITS_40.forEach((fund, index) => {
                stmt.run(fund.code, fund.name, fund.sector, fund.sector_name, function(err) {
                    if (err) {
                        console.error(`   ✗ ${fund.code} 插入失败: ${err.message}`);
                    } else {
                        count++;
                        process.stdout.write(`   ✓ ${fund.code} ${fund.name}\n`);
                    }
                    
                    if (count === REITS_40.length) {
                        stmt.finalize();
                        showStats(db, resolve);
                    }
                });
            });
        });
    });
}

function showStats(db, resolve) {
    console.log('\n3️⃣ 统计结果:');
    console.log('='.repeat(50));
    
    // 按板块统计
    db.all(`
        SELECT sector_name, COUNT(*) as count,
        GROUP_CONCAT(code, ', ') as codes
        FROM funds 
        GROUP BY sector_name 
        ORDER BY count DESC
    `, (err, rows) => {
        if (!err) {
            console.log('\n📊 按板块分布:');
            rows.forEach(row => {
                console.log(`   ${row.sector_name}: ${row.count}只`);
            });
        }
        
        // 按交易所统计
        db.all(`
            SELECT 
                CASE 
                    WHEN code LIKE '180%' THEN '深交所'
                    WHEN code LIKE '508%' THEN '上交所'
                    ELSE '其他'
                END as exchange,
                COUNT(*) as count
            FROM funds
            GROUP BY exchange
        `, (err, rows) => {
            if (!err) {
                console.log('\n📊 按交易所分布:');
                rows.forEach(row => {
                    console.log(`   ${row.exchange}: ${row.count}只`);
                });
            }
            
            console.log('\n' + '='.repeat(50));
            console.log(`✅ 数据库重置完成！共 ${REITS_40.length} 只基金`);
            console.log('='.repeat(50));
            
            db.close();
            resolve();
        });
    });
}

// 运行
resetDatabase().catch(err => {
    console.error('❌ 重置失败:', err);
    process.exit(1);
});
