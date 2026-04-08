/**
 * AKShare 数据接口
 * 路径: /api/akshare
 */

const express = require('express');
const router = express.Router();
const { 
    getReitsList, 
    getReitsSpot, 
    getReitsHistory,
    crawlReitsSpot,
    crawlReitsHistory 
} = require('../crawlers/akshare');

/**
 * GET /api/akshare/list
 * 获取 REITs 基金列表
 */
router.get('/list', async (req, res) => {
    try {
        const result = await getReitsList();
        res.json(result);
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * GET /api/akshare/spot
 * 获取 REITs 实时行情
 */
router.get('/spot', async (req, res) => {
    try {
        const result = await getReitsSpot();
        res.json(result);
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * GET /api/akshare/history/:code
 * 获取单只 REITs 历史数据
 * Query: start=YYYYMMDD&end=YYYYMMDD
 */
router.get('/history/:code', async (req, res) => {
    try {
        const { code } = req.params;
        const { start, end } = req.query;
        const result = await getReitsHistory(code, start, end);
        res.json(result);
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * POST /api/akshare/crawl/spot
 * 立即爬取实时行情
 */
router.post('/crawl/spot', async (req, res) => {
    try {
        const result = await crawlReitsSpot();
        res.json({
            success: true,
            message: '实时行情爬取完成',
            data: result
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * POST /api/akshare/crawl/history/:code
 * 立即爬取历史数据
 * Body: { days: 365 }
 */
router.post('/crawl/history/:code', async (req, res) => {
    try {
        const { code } = req.params;
        const { days = 365 } = req.body;
        const result = await crawlReitsHistory(code, days);
        res.json({
            success: true,
            message: '历史数据爬取完成',
            data: result
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

module.exports = router;
