/**
 * 公告爬虫
 * 上交所：http://www.sse.com.cn/disclosure/announcement/announcement/
 * 深交所：http://www.szse.cn/disclosure/announcement/
 * 
 * 技术方案：爬取列表页，解析标题和链接，AI分类（简化版用关键词匹配）
 */

const axios = require('axios');
const cheerio = require('cheerio');
const crypto = require('crypto');
const { db, logUpdate, updateSourceStatus } = require('../database/db');

// 公告分类关键词
const CATEGORY_KEYWORDS = {
    operation: ['运营', '管理', '租赁', '出租率', '车流量', '收入'],
    dividend: ['分红', '派息', '收益分配', '权益分派'],
    inquiry: ['问询函', '关注函', '回复', '说明'],
    financial: ['年报', '季报', '半年报', '审计', '财务报告', '业绩预告']
};

/**
 * 上交所公告爬虫
 */
async function crawlSSE() {
    console.log('🚀 爬取上交所公告...');
    const startTime = Date.now();
    
    try {
        // 上交所REITs公告接口
        const url = 'http://www.sse.com.cn/js/common/products/announcement/announcementList.js';
        
        const response = await axios.get(url, {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            timeout: 15000
        });
        
        // 解析JSONP格式
        const jsonStr = response.data.replace(/^var\s+\w+\s*=\s*/, '').replace(/;$/, '');
        const data = JSON.parse(jsonStr);
        
        const announcements = [];
        
        for (const item of data.result || []) {
            // 只取最近7天的公告
            const pubDate = new Date(item.publishDate);
            const daysAgo = (Date.now() - pubDate) / (1000 * 60 * 60 * 24);
            if (daysAgo > 7) continue;
            
            // AI分类（关键词匹配）
            const category = classifyAnnouncement(item.title);
            
            // 提取基金代码（从标题中匹配）
            const codeMatch = item.title.match(/(\d{6})/);
            const fundCode = codeMatch ? codeMatch[1] : null;
            
            announcements.push({
                fund_code: fundCode,
                title: item.title,
                category: category,
                summary: generateSummary(item.title, category),
                publish_date: item.publishDate.split(' ')[0],
                source_url: `http://www.sse.com.cn${item.url}`,
                confidence: 0.85
            });
        }
        
        // 保存到数据库
        await saveAnnouncements(announcements);
        
        const duration = Date.now() - startTime;
        await logUpdate('announcement', 'sse-crawler', 'success', announcements.length, duration);
        await updateSourceStatus('announcement', 'sse-crawler', 'active');
        
        console.log(`✅ 上交所公告: ${announcements.length} 条`);
        return announcements;
        
    } catch (error) {
        const duration = Date.now() - startTime;
        console.error('❌ 上交所公告爬取失败:', error.message);
        await logUpdate('announcement', 'sse-crawler', 'error', 0, duration, error.message);
        await updateSourceStatus('announcement', 'sse-crawler', 'error', error.message);
        return [];
    }
}

/**
 * 深交所公告爬虫（简化版）
 */
async function crawlSZSE() {
    // 深交所爬虫逻辑类似，暂时省略
    console.log('⏭️  深交所公告爬取（待实现）');
    return [];
}

/**
 * AI分类（关键词匹配版）
 */
function classifyAnnouncement(title) {
    for (const [category, keywords] of Object.entries(CATEGORY_KEYWORDS)) {
        for (const keyword of keywords) {
            if (title.includes(keyword)) {
                return category;
            }
        }
    }
    return 'other';
}

/**
 * 生成摘要（简化版）
 */
function generateSummary(title, category) {
    const summaries = {
        operation: '本基金的运营情况更新，请关注相关经营指标变化。',
        dividend: '本基金拟进行收益分配，请关注权益登记日和除息日安排。',
        inquiry: '本基金收到交易所问询函，请关注后续回复内容。',
        financial: '本基金发布定期财务报告，请关注营收、利润等核心指标。',
        other: '本基金发布重要公告，请关注具体内容。'
    };
    return summaries[category] || summaries.other;
}

/**
 * 保存公告到数据库
 */
async function saveAnnouncements(announcements) {
    for (const item of announcements) {
        const contentHash = crypto.createHash('md5')
            .update(`${item.fund_code}:${item.publish_date}:${item.title}`)
            .digest('hex');
        await new Promise((resolve, reject) => {
            db.run(
                `INSERT INTO business.announcements 
                 (fund_code, title, category, summary, publish_date, source_url, confidence, content_hash)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                 ON CONFLICT (content_hash) DO NOTHING`,
                [item.fund_code, item.title, item.category, item.summary, 
                 item.publish_date, item.source_url, item.confidence, contentHash],
                (err) => {
                    if (err) reject(err);
                    else resolve();
                }
            );
        });
    }
}

/**
 * 主入口
 */
async function crawlAnnouncements() {
    console.log('🚀 开始爬取公告数据...', new Date().toLocaleString());
    
    const sseResults = await crawlSSE();
    const szseResults = await crawlSZSE();
    
    const total = sseResults.length + szseResults.length;
    console.log(`✅ 公告爬取完成: 共 ${total} 条`);
    
    return [...sseResults, ...szseResults];
}

// 如果直接运行
if (require.main === module) {
    crawlAnnouncements().then(() => {
        console.log('完成');
        process.exit(0);
    }).catch(err => {
        console.error(err);
        process.exit(1);
    });
}

module.exports = { crawlAnnouncements };
