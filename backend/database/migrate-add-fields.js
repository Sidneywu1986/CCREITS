/**
 * 数据库迁移脚本
 * 添加 circulating_shares 和 institution_hold 字段
 */

const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const DB_PATH = path.join(__dirname, 'reits.db');

const db = new sqlite3.Database(DB_PATH);

console.log('🔄 开始数据库迁移...');

// 检查字段是否存在
function columnExists(table, column) {
    return new Promise((resolve, reject) => {
        db.all(`PRAGMA table_info(${table})`, [], (err, rows) => {
            if (err) {
                reject(err);
            } else {
                const exists = rows.some(row => row.name === column);
                resolve(exists);
            }
        });
    });
}

// 添加字段
async function addColumn(table, column, type) {
    const exists = await columnExists(table, column);
    if (exists) {
        console.log(`✅ 字段 ${column} 已存在，跳过`);
        return;
    }

    return new Promise((resolve, reject) => {
        db.run(`ALTER TABLE ${table} ADD COLUMN ${column} ${type}`, [], function(err) {
            if (err) {
                console.error(`❌ 添加字段 ${column} 失败:`, err.message);
                reject(err);
            } else {
                console.log(`✅ 成功添加字段 ${column}`);
                resolve();
            }
        });
    });
}

// 执行迁移
async function migrate() {
    try {
        // 添加流通份额字段
        await addColumn('funds', 'circulating_shares', 'REAL');
        
        // 添加机构持仓字段
        await addColumn('funds', 'institution_hold', 'REAL');
        
        console.log('✅ 数据库迁移完成！');
        process.exit(0);
    } catch (error) {
        console.error('❌ 迁移失败:', error);
        process.exit(1);
    }
}

migrate();
