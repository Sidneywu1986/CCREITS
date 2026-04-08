/**
 * 爬虫定时调度器
 * 自动运行各类爬虫任务
 */

const cron = require('node-cron');
const SinaCrawler = require('./sina');
const EastMoneyCrawler = require('./eastmoney');
const FundDetailCrawler = require('./fund-detail');
const AnnouncementCrawler = require('./announcement_v2');

console.log('⏰ 爬虫定时调度器已启动\n');

// 1. 实时行情 - 每5分钟（交易日 9:00-15:00）
cron.schedule('*/5 9-15 * * 1-5', async () => {
    console.log(`\n[${new Date().toLocaleString()}] ⏰ 启动实时行情爬虫...`);
    try {
        const crawler = new SinaCrawler();
        await crawler.fetchData();
        console.log('✅ 实时行情更新完成');
    } catch (error) {
        console.error('❌ 实时行情失败:', error.message);
    }
}, {
    timezone: 'Asia/Shanghai'
});

// 2. 东财深度数据 - 每30分钟
cron.schedule('*/30 9-15 * * 1-5', async () => {
    console.log(`\n[${new Date().toLocaleString()}] ⏰ 启动东财深度数据爬虫...`);
    try {
        const crawler = new EastMoneyCrawler();
        await crawler.fetchData();
        console.log('✅ 东财深度数据更新完成');
    } catch (error) {
        console.error('❌ 东财深度数据失败:', error.message);
    }
}, {
    timezone: 'Asia/Shanghai'
});

// 3. 基金详情（净值、份额等）- 每日凌晨2点
cron.schedule('0 2 * * *', async () => {
    console.log(`\n[${new Date().toLocaleString()}] ⏰ 启动基金详情爬虫...`);
    try {
        const crawler = new FundDetailCrawler();
        await crawler.fetchData();
        console.log('✅ 基金详情更新完成');
    } catch (error) {
        console.error('❌ 基金详情失败:', error.message);
    }
}, {
    timezone: 'Asia/Shanghai'
});

// 4. 公告更新 - 每小时
cron.schedule('0 * * * *', async () => {
    console.log(`\n[${new Date().toLocaleString()}] ⏰ 启动公告爬虫...`);
    try {
        const crawler = new AnnouncementCrawler();
        await crawler.crawlAll();
        console.log('✅ 公告更新完成');
    } catch (error) {
        console.error('❌ 公告更新失败:', error.message);
    }
});

console.log('📋 已配置定时任务:');
console.log('  • 实时行情: 每5分钟 (交易日 9:00-15:00)');
console.log('  • 东财深度: 每30分钟 (交易日 9:00-15:00)');
console.log('  • 基金详情: 每日凌晨 2:00');
console.log('  • 公告更新: 每小时');
console.log('\n💡 提示: 保持此进程运行即可自动执行\n');

// 防止进程退出
setInterval(() => {
    // 心跳检测
}, 60000);
