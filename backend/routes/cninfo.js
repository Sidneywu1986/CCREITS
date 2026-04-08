/**
 * 巨潮资讯网爬虫API
 * 路径：/api/cninfo
 */

const express = require('express');
const router = express.Router();
const { crawlSingleREIT, crawlAllREITs } = require('../crawlers/cninfo_crawler_wrapper');

/**
 * POST /api/cninfo/crawl
 * 爬取单只REIT公告
 * Body: { code: string, maxCount: number }
 */
router.post('/crawl', async (req, res) => {
    try {
        const { code, maxCount = 30 } = req.body;
        
        if (!code) {
            return res.status(400).json({
                success: false,
                error: '请提供REIT代码'
            });
        }
        
        console.log(`🎯 开始爬取 ${code} 的公告...`);
        const result = await crawlSingleREIT(code, maxCount);
        
        res.json({
            success: true,
            message: `成功爬取 ${code} 的公告`,
            data: result
        });
    } catch (error) {
        console.error('爬取失败:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * POST /api/cninfo/crawl-all
 * 批量爬取全部REIT公告
 * Body: { maxWorkers: number, maxCount: number }
 */
router.post('/crawl-all', async (req, res) => {
    try {
        const { maxWorkers = 3, maxCount = 30 } = req.body;
        
        console.log('🚀 开始批量爬取全部REIT...');
        
        // 使用setImmediate让请求立即返回，爬虫在后台运行
        res.json({
            success: true,
            message: '批量爬取任务已启动，正在后台运行',
            data: {
                maxWorkers,
                maxCount,
                status: 'running'
            }
        });
        
        // 后台运行爬虫
        crawlAllREITs({ maxWorkers, maxCount })
            .then(result => {
                console.log('✅ 批量爬取完成:', result);
            })
            .catch(error => {
                console.error('❌ 批量爬取失败:', error);
            });
            
    } catch (error) {
        console.error('启动批量爬取失败:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * GET /api/cninfo/status
 * 获取爬虫状态
 */
router.get('/status', (req, res) => {
    res.json({
        success: true,
        data: {
            source: '巨潮资讯网 (CNInfo)',
            crawlerVersion: '2.0.0',
            supportedMarkets: ['SSE', 'SZSE'],
            totalREITs: 79
        }
    });
});

module.exports = router;
