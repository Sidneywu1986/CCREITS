/**
 * 大盘指数API
 * 路径：/api/market
 */

const express = require('express');
const router = express.Router();
const { db } = require('../database/db');
const MarketIndexCrawler = require('../crawlers/market-index');

/**
 * GET /api/market/indices
 * 获取所有大盘指数
 */
router.get('/indices', (req, res) => {
    db.all(`
        SELECT code, name, value, change, change_percent as changePercent, source, updated_at as updateTime
        FROM market_indices
        ORDER BY code
    `, [], (err, rows) => {
        if (err) {
            console.error('获取大盘指数失败:', err);
            return res.status(500).json({
                success: false,
                error: err.message
            });
        }
        
        res.json({
            success: true,
            count: rows.length,
            data: rows,
            timestamp: new Date().toISOString()
        });
    });
});

/**
 * GET /api/market/indices/:code
 * 获取单个指数
 */
router.get('/indices/:code', (req, res) => {
    const { code } = req.params;
    
    db.get(`
        SELECT code, name, value, change, change_percent as changePercent, source, updated_at as updateTime
        FROM market_indices
        WHERE code = ?
    `, [code], (err, row) => {
        if (err) {
            return res.status(500).json({
                success: false,
                error: err.message
            });
        }
        
        if (!row) {
            return res.status(404).json({
                success: false,
                error: '指数不存在'
            });
        }
        
        res.json({
            success: true,
            data: row
        });
    });
});

/**
 * POST /api/market/refresh
 * 手动刷新大盘数据
 */
router.post('/refresh', async (req, res) => {
    try {
        const crawler = new MarketIndexCrawler();
        const data = await crawler.fetchData();
        await crawler.saveToDatabase(data);
        
        res.json({
            success: true,
            message: '大盘数据刷新成功',
            count: data.length,
            data: data
        });
    } catch (error) {
        console.error('刷新大盘数据失败:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

module.exports = router;
