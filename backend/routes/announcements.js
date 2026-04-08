/**
 * 公告相关API
 * 路径：/api/announcements
 */

const express = require('express');
const router = express.Router();
const { db } = require('../database/db');
const { crawlAnnouncements } = require('../crawlers/announcement_v2');

/**
 * GET /api/announcements
 * 获取公告列表
 * Query参数：
 * - category: 分类过滤（operation/dividend/inquiry/financial）
 * - fund_code: 基金代码过滤
 * - days: 最近N天（默认30天）
 * - limit: 数量限制（默认100）
 * - exchange: 交易所过滤（SSE/SZSE）
 */
router.get('/', (req, res) => {
    const { 
        category, 
        fund_code, 
        days = 30, 
        limit = 100,
        search,
        exchange
    } = req.query;
    
    let sql = `
        SELECT 
            a.*,
            f.name as fund_name,
            f.sector_name
        FROM announcements a
        LEFT JOIN funds f ON a.fund_code = f.code
        WHERE 1=1
    `;
    
    const params = [];
    
    // 时间筛选
    if (parseInt(days) > 0) {
        sql += ` AND a.publish_date >= date('now', '-${days} days')`;
    }
    
    // 分类筛选
    if (category && category !== 'all') {
        sql += ` AND a.category = ?`;
        params.push(category);
    }
    
    // 交易所筛选
    if (exchange && exchange !== 'all') {
        sql += ` AND a.exchange = ?`;
        params.push(exchange);
    }
    
    // 基金代码筛选
    if (fund_code) {
        sql += ` AND a.fund_code = ?`;
        params.push(fund_code);
    }
    
    // 搜索筛选
    if (search) {
        sql += ` AND (a.title LIKE ? OR a.summary LIKE ?)`;
        params.push(`%${search}%`, `%${search}%`);
    }
    
    sql += ` ORDER BY a.publish_date DESC, a.id DESC LIMIT ?`;
    params.push(parseInt(limit));
    
    db.all(sql, params, (err, announcements) => {
        if (err) {
            console.error('获取公告列表失败:', err);
            return res.status(500).json({
                success: false,
                error: err.message
            });
        }
        
        // 为每个公告添加巨潮资讯网链接
        const enrichedAnnouncements = announcements.map(ann => ({
            ...ann,
            // 巨潮资讯网搜索链接（按基金代码）
            cninfo_url: `http://www.cninfo.com.cn/new/information/topSearch/query?keyWord=${ann.fund_code}`,
            // 如果有source_url，优先使用（存储的是公告详情页或PDF链接）
            pdf_url: ann.source_url && ann.source_url.includes('static.cninfo.com.cn') 
                ? ann.source_url 
                : null
        }));
        
        res.json({
            success: true,
            count: enrichedAnnouncements.length,
            data: enrichedAnnouncements
        });
    });
});

/**
 * POST /api/announcements/crawl
 * 手动触发公告爬取
 */
router.post('/crawl', async (req, res) => {
    try {
        console.log('🔄 手动触发公告爬取...');
        const results = await crawlAnnouncements();
        
        res.json({
            success: true,
            message: '爬取完成',
            count: results.length,
            data: results
        });
    } catch (error) {
        console.error('手动爬取失败:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * GET /api/announcements/stats
 * 获取公告统计
 */
router.get('/stats', (req, res) => {
    const sql = `
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN exchange = 'SSE' THEN 1 ELSE 0 END) as sse_count,
            SUM(CASE WHEN exchange = 'SZSE' THEN 1 ELSE 0 END) as szse_count,
            SUM(CASE WHEN publish_date = date('now') THEN 1 ELSE 0 END) as today_count,
            category,
            COUNT(*) as category_count
        FROM announcements
        GROUP BY category
    `;
    
    db.all(sql, [], (err, rows) => {
        if (err) {
            return res.status(500).json({
                success: false,
                error: err.message
            });
        }
        
        const stats = {
            total: rows.length > 0 ? rows[0].total : 0,
            sse_count: rows.length > 0 ? rows[0].sse_count : 0,
            szse_count: rows.length > 0 ? rows[0].szse_count : 0,
            today_count: rows.length > 0 ? rows[0].today_count : 0,
            categories: rows.reduce((acc, r) => {
                acc[r.category] = r.category_count;
                return acc;
            }, {})
        };
        
        res.json({
            success: true,
            data: stats
        });
    });
});

/**
 * GET /api/announcements/:id
 * 获取公告详情
 */
router.get('/:id', (req, res) => {
    const { id } = req.params;
    
    const sql = `
        SELECT a.*, f.name as fund_name
        FROM announcements a
        LEFT JOIN funds f ON a.fund_code = f.code
        WHERE a.id = ?
    `;
    
    db.get(sql, [id], (err, announcement) => {
        if (err) {
            console.error('获取公告详情失败:', err);
            return res.status(500).json({
                success: false,
                error: err.message
            });
        }
        
        if (!announcement) {
            return res.status(404).json({
                success: false,
                error: '公告不存在'
            });
        }
        
        res.json({
            success: true,
            data: announcement
        });
    });
});

module.exports = router;
