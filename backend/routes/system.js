/**
 * 系统相关API
 * 路径：/api/system
 */

const express = require('express');
const router = express.Router();
const { db, getDataSourcesStatus } = require('../database/db');

/**
 * GET /api/system/status
 * 获取系统状态和数据源健康度
 */
router.get('/status', async (req, res) => {
    try {
        // 数据库统计
        const statsSql = `
            SELECT 
                (SELECT COUNT(*) FROM funds) as fund_count,
                (SELECT COUNT(*) FROM quotes) as quote_count,
                (SELECT COUNT(*) FROM announcements WHERE publish_date >= date('now', '-7 days')) as announcement_count,
                (SELECT MAX(updated_at) FROM quotes) as last_quote_time
        `;
        
        const stats = await new Promise((resolve, reject) => {
            db.get(statsSql, [], (err, row) => {
                if (err) reject(err);
                else resolve(row);
            });
        });
        
        // 数据源状态
        const sources = await getDataSourcesStatus();
        
        res.json({
            success: true,
            data: {
                stats,
                sources,
                server_time: new Date().toISOString(),
                version: '1.0.0'
            }
        });
        
    } catch (error) {
        console.error('获取系统状态失败:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * GET /api/system/logs
 * 获取最近更新日志
 */
router.get('/logs', (req, res) => {
    const { limit = 20 } = req.query;
    
    const sql = `
        SELECT * FROM update_logs
        ORDER BY created_at DESC
        LIMIT ?
    `;
    
    db.all(sql, [parseInt(limit)], (err, logs) => {
        if (err) {
            console.error('获取日志失败:', err);
            return res.status(500).json({
                success: false,
                error: err.message
            });
        }
        
        res.json({
            success: true,
            data: logs
        });
    });
});

module.exports = router;
