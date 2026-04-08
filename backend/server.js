/**
 * REITs数据平台后端服务
 * 阶段一：快速可用（Node.js + SQLite）
 */

require('dotenv').config();
const express = require('express');
const cors = require('cors');
const cron = require('node-cron');
const path = require('path');

const { db, initDatabase } = require('./database/db');
const { crawlAnnouncements } = require('./crawlers/announcement_v2');
const crawlerManager = require('./crawlers');

// 导入路由
const fundsRouter = require('./routes/funds');
const announcementsRouter = require('./routes/announcements');
const systemRouter = require('./routes/system');
const akshareRouter = require('./routes/akshare');
const aiChatRouter = require('./routes/ai-chat');
const marketRouter = require('./routes/market');
const { initWebSocket } = require('./routes/ai-chat');
const MarketIndexCrawler = require('./crawlers/market-index');

const app = express();
const PORT = process.env.PORT || 3000;

// 数据源配置
const USE_AKSHARE = process.env.USE_AKSHARE === 'true' || false;
const USE_SINA = process.env.USE_SINA !== 'false';  // 默认启用

// 中间件
app.use(cors()); // 允许跨域
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// 禁用所有安全策略，允许本地开发
app.use((req, res, next) => {
    // 重写res.send和res.json来移除安全头部
    const originalSend = res.send;
    const originalJson = res.json;
    const originalSendFile = res.sendFile;
    
    res.send = function(...args) {
        res.removeHeader('Content-Security-Policy');
        res.removeHeader('X-Content-Security-Policy');
        res.removeHeader('X-WebKit-CSP');
        res.removeHeader('X-Frame-Options');
        return originalSend.apply(this, args);
    };
    
    res.json = function(...args) {
        res.removeHeader('Content-Security-Policy');
        res.removeHeader('X-Content-Security-Policy');
        res.removeHeader('X-WebKit-CSP');
        res.removeHeader('X-Frame-Options');
        return originalJson.apply(this, args);
    };
    
    next();
});

// 请求日志
app.use((req, res, next) => {
    console.log(`${new Date().toISOString()} - ${req.method} ${req.url}`);
    next();
});

// API路由
app.use('/api/funds', fundsRouter);
app.use('/api/announcements', announcementsRouter);
app.use('/api/system', systemRouter);
app.use('/api/akshare', akshareRouter);
app.use('/api/ai-chat', aiChatRouter.router);
app.use('/api/market', marketRouter);

// 静态文件服务（前端文件）
const FRONTEND_PATH = path.resolve(__dirname, '../frontend');
console.log('前端路径:', FRONTEND_PATH);

// 配置静态文件服务，禁用默认缓存
app.use(express.static(FRONTEND_PATH, {
    etag: false,
    lastModified: false,
    setHeaders: (res, path) => {
        // 移除所有CSP相关的安全头部
        res.removeHeader('Content-Security-Policy');
        res.removeHeader('X-Content-Security-Policy');
        res.removeHeader('X-WebKit-CSP');
        res.removeHeader('X-Frame-Options');
        // 设置缓存控制
        res.setHeader('Cache-Control', 'no-cache');
    }
}));

// 显式路由到各个HTML文件
app.get('/market.html', (req, res) => {
    res.sendFile(path.join(FRONTEND_PATH, 'market.html'), {
        headers: { 'Cache-Control': 'no-cache' }
    });
});
app.get('/ai-chat.html', (req, res) => {
    res.sendFile(path.join(FRONTEND_PATH, 'ai-chat.html'), {
        headers: { 'Cache-Control': 'no-cache' }
    });
});
app.get('/announcements.html', (req, res) => {
    res.sendFile(path.join(FRONTEND_PATH, 'announcements.html'), {
        headers: { 'Cache-Control': 'no-cache' }
    });
});
app.get('/fund-detail.html', (req, res) => {
    res.sendFile(path.join(FRONTEND_PATH, 'fund-detail.html'), {
        headers: { 'Cache-Control': 'no-cache' }
    });
});
app.get('/compare.html', (req, res) => {
    res.sendFile(path.join(FRONTEND_PATH, 'compare.html'), {
        headers: { 'Cache-Control': 'no-cache' }
    });
});
app.get('/portfolio.html', (req, res) => {
    res.sendFile(path.join(FRONTEND_PATH, 'portfolio.html'), {
        headers: { 'Cache-Control': 'no-cache' }
    });
});
app.get('/tools.html', (req, res) => {
    res.sendFile(path.join(FRONTEND_PATH, 'tools.html'), {
        headers: { 'Cache-Control': 'no-cache' }
    });
});
app.get('/dividend-calendar.html', (req, res) => {
    res.sendFile(path.join(FRONTEND_PATH, 'dividend-calendar.html'), {
        headers: { 'Cache-Control': 'no-cache' }
    });
});
app.get('/fund-archive.html', (req, res) => {
    res.sendFile(path.join(FRONTEND_PATH, 'fund-archive.html'), {
        headers: { 'Cache-Control': 'no-cache' }
    });
});

// 根路径重定向到首页
app.get('/', (req, res) => {
    res.sendFile(path.join(FRONTEND_PATH, 'index.html'), {
        headers: {
            'Cache-Control': 'no-cache'
        }
    });
});

// 健康检查
app.get('/api/health', (req, res) => {
    res.json({
        status: 'ok',
        timestamp: new Date().toISOString(),
        uptime: process.uptime()
    });
});

// 404处理
app.use((req, res) => {
    res.status(404).json({
        success: false,
        error: 'API不存在'
    });
});

// 错误处理
app.use((err, req, res, next) => {
    console.error('服务器错误:', err);
    res.status(500).json({
        success: false,
        error: '服务器内部错误'
    });
});

// ==================== 定时任务 ====================

// 行情数据：每5分钟更新一次（交易时间）
cron.schedule('*/5 9-15 * * 1-5', async () => {
    console.log('⏰ 定时任务：快速更新行情');
    try {
        await crawlerManager.runQuick();
    } catch (error) {
        console.error('定时任务失败:', error);
    }
});

// 全量数据：每小时更新一次
cron.schedule('0 * * * *', async () => {
    console.log('⏰ 定时任务：全量数据采集');
    try {
        await crawlerManager.runAll();
    } catch (error) {
        console.error('定时任务失败:', error);
    }
});

// 公告数据：每小时更新一次
cron.schedule('30 * * * *', async () => {
    console.log('⏰ 定时任务：更新公告数据');
    try {
        await crawlAnnouncements();
    } catch (error) {
        console.error('公告更新失败:', error);
    }
});

// 大盘指数：每5分钟更新一次（交易时间）
cron.schedule('*/5 9-15 * * 1-5', async () => {
    console.log('⏰ 定时任务：更新大盘指数');
    try {
        const crawler = new MarketIndexCrawler();
        const data = await crawler.fetchData();
        await crawler.saveToDatabase(data);
        console.log(`✅ 大盘指数更新完成: ${data.length} 条`);
    } catch (error) {
        console.error('大盘指数更新失败:', error);
    }
});

// ==================== 启动服务 ====================

async function startServer() {
    try {
        // 初始化数据库
        await initDatabase();
        
        // 启动服务 - 绑定到所有网络接口
        const server = app.listen(PORT, '0.0.0.0', () => {
            const dataSources = [];
            if (USE_AKSHARE) dataSources.push('AKShare');
            if (USE_SINA) dataSources.push('新浪财经');
            
            console.log(`
🚀 REITs数据平台后端服务已启动

📍 服务地址: http://localhost:${PORT}
📊 数据源: 新浪财经 + AKShare + 东方财富
📋 API文档:
   GET  /api/health              健康检查
   GET  /api/funds               基金列表
   GET  /api/funds/:code         基金详情
   GET  /api/funds/:code/kline   K线数据
   GET  /api/announcements       公告列表
   GET  /api/system/status       系统状态
   GET  /api/ai-chat/personas    AI角色列表
   GET  /api/ai-chat/hot-topics  热点话题
   WS   /ws/ai-chat              AI聊天室WebSocket

🤖 AI聊REIT: 
   访问 http://localhost:${PORT}/ai-chat.html 进入AI聊天室

⏰ 定时任务:
   快速行情: 每5分钟（交易日 9:00-15:00）
   全量数据: 每小时
   公告更新: 每小时

💡 手动更新命令:
   node scripts/crawl-all.js        立即执行全量采集
            `);
            
            // 初始化WebSocket
            initWebSocket(server);
        });
        
    } catch (error) {
        console.error('❌ 启动失败:', error);
        process.exit(1);
    }
}

// 优雅关闭
process.on('SIGINT', () => {
    console.log('\n👋 正在关闭服务...');
    db.close();
    process.exit(0);
});

// 启动
startServer();
