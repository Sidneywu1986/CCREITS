/**
 * 数据库连接模块
 * 使用 sqlite3（异步API，兼容性更好）
 */

const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const fs = require('fs');

const DB_PATH = path.join(__dirname, 'reits.db');
const SCHEMA_PATH = path.join(__dirname, 'schema.sql');

// 创建数据库连接
const db = new sqlite3.Database(DB_PATH);

// 启用外键约束
db.run('PRAGMA foreign_keys = ON');
db.run('PRAGMA journal_mode = WAL');

// 初始化表结构
function initDatabase() {
    return new Promise((resolve, reject) => {
        try {
            // 加载主schema
            const schema = fs.readFileSync(SCHEMA_PATH, 'utf8');
            
            // 加载AI聊天schema
            const aiSchemaPath = path.join(__dirname, 'ai_chat_schema.sql');
            let aiSchema = '';
            if (fs.existsSync(aiSchemaPath)) {
                aiSchema = fs.readFileSync(aiSchemaPath, 'utf8');
            }
            
            // 加载大盘指数schema
            const indexSchemaPath = path.join(__dirname, 'index_schema.sql');
            let indexSchema = '';
            if (fs.existsSync(indexSchemaPath)) {
                indexSchema = fs.readFileSync(indexSchemaPath, 'utf8');
            }
            
            // 合并schema并执行
            const combinedSchema = schema + ';\n' + aiSchema + ';\n' + indexSchema;
            
            // 使用exec批量执行（更安全）
            db.exec(combinedSchema, (err) => {
                if (err) {
                    console.error('❌ Schema执行错误:', err);
                    reject(err);
                    return;
                }
                console.log('✅ 数据库表结构初始化成功');
                // 初始化数据源追踪表
                initDataSources().then(resolve).catch(reject);
            });
        } catch (error) {
            console.error('❌ 数据库初始化失败:', error);
            reject(error);
        }
    });
}

// 初始化数据源配置
function initDataSources() {
    return new Promise((resolve, reject) => {
        const sources = [
            { type: 'price', name: 'sina-finance', url: 'https://hq.sinajs.cn/' },
            { type: 'price', name: 'akshare', url: 'https://www.akshare.xyz/' },
            { type: 'history', name: 'akshare', url: 'https://www.akshare.xyz/' },
            { type: 'announcement', name: 'sse-crawler', url: 'http://www.sse.com.cn/' },
            { type: 'announcement', name: 'szse-crawler', url: 'http://www.szse.cn/' },
            { type: 'nav', name: 'china-fund', url: 'http://fund.eastmoney.com/' }
        ];
        
        const stmt = db.prepare(`
            INSERT OR IGNORE INTO data_sources (data_type, source_name, source_url)
            VALUES (?, ?, ?)
        `);
        
        let completed = 0;
        for (const source of sources) {
            stmt.run(source.type, source.name, source.url, function(err) {
                if (err) console.error('插入数据源失败:', err);
                completed++;
                if (completed === sources.length) {
                    stmt.finalize();
                    resolve();
                }
            });
        }
    });
}

// 记录更新日志
function logUpdate(dataType, source, status, recordsCount, durationMs, errorMsg = null) {
    return new Promise((resolve, reject) => {
        const stmt = db.prepare(`
            INSERT INTO update_logs (data_type, source, status, records_count, duration_ms, error_msg)
            VALUES (?, ?, ?, ?, ?, ?)
        `);
        
        stmt.run(dataType, source, status, recordsCount, durationMs, errorMsg, function(err) {
            stmt.finalize();
            if (err) reject(err);
            else resolve();
        });
    });
}

// 更新数据源状态
function updateSourceStatus(dataType, sourceName, status, errorMsg = null) {
    return new Promise((resolve, reject) => {
        const stmt = db.prepare(`
            UPDATE data_sources 
            SET last_updated = CURRENT_TIMESTAMP, 
                status = ?,
                error_msg = ?,
                update_count = update_count + 1
            WHERE data_type = ? AND source_name = ?
        `);
        
        stmt.run(status, errorMsg, dataType, sourceName, function(err) {
            stmt.finalize();
            if (err) reject(err);
            else resolve();
        });
    });
}

// 获取数据源状态（用于前端展示）
function getDataSourcesStatus() {
    return new Promise((resolve, reject) => {
        db.all(`
            SELECT data_type, source_name, last_updated, status, error_msg
            FROM data_sources
            ORDER BY data_type
        `, (err, rows) => {
            if (err) reject(err);
            else resolve(rows);
        });
    });
}

module.exports = {
    db,
    initDatabase,
    logUpdate,
    updateSourceStatus,
    getDataSourcesStatus
};
