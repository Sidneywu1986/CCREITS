/**
 * PostgreSQL 数据库连接模块
 * 兼容旧版 SQLite API，支持 Node.js 爬虫系统
 */

const { Pool } = require('pg');
const path = require('path');

// 尝试加载 .env，失败则使用环境变量或默认值
try {
    require('dotenv').config({ path: path.join(__dirname, '..', '.env') });
} catch (e) {
    // dotenv 未安装，忽略
}

const pool = new Pool({
    host: process.env.PG_HOST || 'localhost',
    port: parseInt(process.env.PG_PORT || '5432'),
    database: process.env.PG_DB || 'reits',
    user: process.env.PG_USER || 'postgres',
    password: process.env.PG_PASSWORD || 'postgres',
});

pool.on('error', (err) => {
    console.error('PostgreSQL pool error:', err);
});

// 已知冲突列映射（用于 INSERT OR REPLACE / INSERT OR IGNORE 转换）
const CONFLICT_COLUMNS = {
    'business.price_history': 'fund_code, trade_date',
    'business.fund_prices': 'fund_code, trade_date',
    'business.funds': 'fund_code',
    'business.data_sources': 'data_type, source_name',
    'business.announcements': 'id',
};

// SQL 翻译：SQLite → PostgreSQL
function translateSql(sql) {
    let result = sql;

    // 1. SQLite 函数 → PostgreSQL
    result = result.replace(/datetime\('now'\)/gi, 'NOW()');
    result = result.replace(/date\('now'\)/gi, 'CURRENT_DATE');

    // 2. 表名添加 business. 前缀（避免重复）
    const tables = [
        'funds', 'quotes', 'price_history', 'announcements',
        'data_sources', 'update_logs', 'fund_prices',
        'wechat_articles', 'dividends', 'article_vectors'
    ];
    for (const t of tables) {
        // 使用负向后行断言确保前面没有 business.
        const re = new RegExp(`(?<!business\\.)\\b${t}\\b`, 'g');
        result = result.replace(re, `business.${t}`);
    }

    // 3. INSERT OR REPLACE → INSERT ... ON CONFLICT DO UPDATE
    const orReplaceRe = /INSERT\s+OR\s+REPLACE\s+INTO\s+(\w+)\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\)/i;
    let m;
    while ((m = result.match(orReplaceRe)) !== null) {
        const table = m[1];
        const cols = m[2];
        const vals = m[3];
        const colArr = cols.split(',').map(c => c.trim());
        const conflictCols = CONFLICT_COLUMNS[table] || CONFLICT_COLUMNS[`business.${table}`] || 'id';
        const updateSets = colArr.map(c => `${c} = EXCLUDED.${c}`).join(', ');
        const replacement = `INSERT INTO ${table} (${cols}) VALUES (${vals}) ON CONFLICT (${conflictCols}) DO UPDATE SET ${updateSets}`;
        result = result.replace(m[0], replacement);
    }

    // 4. INSERT OR IGNORE → INSERT ... ON CONFLICT DO NOTHING
    const orIgnoreRe = /INSERT\s+OR\s+IGNORE\s+INTO\s+(\w+)\s*\(([^)]+)\)\s*VALUES\s*\(/i;
    while ((m = result.match(orIgnoreRe)) !== null) {
        const table = m[1];
        const cols = m[2];
        const conflictCols = CONFLICT_COLUMNS[table] || CONFLICT_COLUMNS[`business.${table}`] || 'id';
        // 找到匹配的 VALUES 结束位置
        const startIdx = result.indexOf(m[0]);
        let parenDepth = 1;
        let endIdx = startIdx + m[0].length;
        while (parenDepth > 0 && endIdx < result.length) {
            if (result[endIdx] === '(') parenDepth++;
            else if (result[endIdx] === ')') parenDepth--;
            endIdx++;
        }
        const original = result.slice(startIdx, endIdx);
        const replacement = `INSERT INTO ${table} (${cols}) VALUES (${original.slice(m[0].length, -1)}) ON CONFLICT (${conflictCols}) DO NOTHING`;
        result = result.slice(0, startIdx) + replacement + result.slice(endIdx);
    }

    return result;
}

// ? → $1, $2...
function convertPlaceholders(sql, params) {
    let idx = 0;
    const pgSql = sql.replace(/\?/g, () => `$${++idx}`);
    return { sql: pgSql, params: params || [] };
}

function executeQuery(sql, params) {
    const translated = translateSql(sql);
    const { sql: pgSql, params: pgParams } = convertPlaceholders(translated, params);
    return pool.query(pgSql, pgParams);
}

// 兼容 SQLite 风格的 db 对象
const db = {
    all(sql, params, callback) {
        if (typeof params === 'function') {
            callback = params;
            params = [];
        }
        executeQuery(sql, params)
            .then(res => callback(null, res.rows))
            .catch(err => callback(err));
    },

    run(sql, params, callback) {
        if (typeof params === 'function') {
            callback = params;
            params = [];
        }
        executeQuery(sql, params)
            .then(res => {
                const context = {
                    lastID: res.rows[0]?.id || 0,
                    changes: res.rowCount || 0
                };
                if (callback) callback.call(context, null);
            })
            .catch(err => {
                if (callback) callback(err);
            });
    },

    get(sql, params, callback) {
        if (typeof params === 'function') {
            callback = params;
            params = [];
        }
        executeQuery(sql, params)
            .then(res => callback(null, res.rows[0] || null))
            .catch(err => callback(err));
    },

    exec(sql, callback) {
        const statements = sql.split(/;\s*\n/).filter(s => s.trim());
        let idx = 0;
        const next = () => {
            if (idx >= statements.length) {
                if (callback) callback(null);
                return;
            }
            const stmt = statements[idx++].trim();
            if (!stmt) { next(); return; }
            executeQuery(stmt, [])
                .then(() => next())
                .catch(err => { if (callback) callback(err); });
        };
        next();
    },

    // 模拟 sqlite3.prepare 返回 statement 对象
    prepare(sql) {
        const translated = translateSql(sql);
        return {
            run(params, callback) {
                const { sql: pgSql, params: pgParams } = convertPlaceholders(translated, params || []);
                pool.query(pgSql, pgParams)
                    .then(res => {
                        const context = { lastID: res.rows[0]?.id || 0, changes: res.rowCount || 0 };
                        if (callback) callback.call(context, null);
                    })
                    .catch(err => { if (callback) callback(err); });
            },
            finalize() {}
        };
    }
};

function initDatabase() {
    // PostgreSQL schema 已由 postgres_schema.sql 初始化
    return Promise.resolve();
}

function logUpdate(dataType, source, status, recordsCount, durationMs, errorMsg = null) {
    return pool.query(
        `INSERT INTO business.update_logs (data_type, source, status, records_count, duration_ms, error_msg)
         VALUES ($1, $2, $3, $4, $5, $6)`,
        [dataType, source, status, recordsCount, durationMs, errorMsg]
    ).then(() => {}).catch(() => {});
}

function updateSourceStatus(dataType, sourceName, status, errorMsg = null) {
    return pool.query(
        `UPDATE business.data_sources
         SET last_updated = CURRENT_TIMESTAMP, status = $1, error_msg = $2, update_count = update_count + 1
         WHERE data_type = $3 AND source_name = $4`,
        [status, errorMsg, dataType, sourceName]
    ).then(() => {}).catch(() => {});
}

function getDataSourcesStatus() {
    return pool.query(
        `SELECT data_type, source_name, last_updated, status, error_msg
         FROM business.data_sources
         ORDER BY data_type`
    ).then(res => res.rows);
}

module.exports = {
    db,
    pool,
    initDatabase,
    logUpdate,
    updateSourceStatus,
    getDataSourcesStatus
};
