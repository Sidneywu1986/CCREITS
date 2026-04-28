/**
 * 爬虫定时调度器 - 主系统
 * 自动运行各类爬虫任务，支持自动重试和数据完整性检查
 */

const cron = require('node-cron');
const SinaCrawler = require('./sina');
const EastMoneyCrawler = require('./eastmoney');
const FundDetailCrawler = require('./fund-detail');
const AnnouncementCrawler = require('./announcement_v2');
const DataIntegrityChecker = require('./data-integrity-checker');
const AlertManager = require('./alert-manager');
const YieldCrawler = require('./yield_crawler');

const config = {
    // 自动重试配置
    retry: {
        maxAttempts: 3,
        delay: 5000, // 5秒
        backoff: 2, // 指数退避
    },
    // 数据完整性检查配置
    integrity: {
        enable: true,
        checkInterval: 3600000, // 每小时
        alertThreshold: 0.1, // 10%数据缺失告警
    }
};

console.log('⏰ 爬虫定时调度器已启动\n');

/**
 * 带自动重试的运行函数
 */
async function runWithRetry(taskName, taskFn, customConfig = {}) {
    const retryConfig = { ...config.retry, ...customConfig };

    for (let attempt = 1; attempt <= retryConfig.maxAttempts; attempt++) {
        const startTime = Date.now();

        try {
            console.log(`\n[${new Date().toLocaleString()}] ⏰ 启动${taskName}爬虫 (尝试 ${attempt}/${retryConfig.maxAttempts})...`);
            await taskFn();

            const duration = ((Date.now() - startTime) / 1000).toFixed(2);
            console.log(`✅ ${taskName}更新完成 (耗时 ${duration}s)`);

            // 成功则跳出重试循环
            break;
        } catch (error) {
            const duration = ((Date.now() - startTime) / 1000).toFixed(2);
            console.error(`❌ ${taskName}失败 (尝试 ${attempt}/${retryConfig.maxAttempts}, 耗时 ${duration}s):`, error.message);

            // 发送告警
            AlertManager.sendFormattedAlert('CRAWLER_FAILED', {
                crawler: taskName,
                attempt,
                error: error.message,
                duration,
            }, attempt === retryConfig.maxAttempts ? 'high' : 'medium');

            // 如果是最后一次尝试，仍然失败
            if (attempt === retryConfig.maxAttempts) {
                console.error(`❌ ${taskName}达到最大重试次数，放弃任务`);
                break;
            }

            // 计算退避时间并等待
            const delay = retryConfig.delay * Math.pow(retryConfig.backoff, attempt - 1);
            console.log(`⏳ ${taskName}等待 ${delay}ms 后重试...`);
            await new Promise(resolve => setTimeout(resolve, delay));
        }
    }
}

// 1. 实时行情 - 每5分钟（交易日 9:00-15:00）
cron.schedule('*/5 9-15 * * 1-5', async () => {
    await runWithRetry(
        '实时行情',
        async () => {
            const crawler = new SinaCrawler();
            await crawler.fetchData();
        }
    );
}, {
    timezone: 'Asia/Shanghai'
});

// 2. 东财深度数据 - 每30分钟
cron.schedule('*/30 9-15 * * 1-5', async () => {
    await runWithRetry(
        '东财深度数据',
        async () => {
            const crawler = new EastMoneyCrawler();
            await crawler.fetchData();
        }
    );
}, {
    timezone: 'Asia/Shanghai'
});

// 3. 基金详情（净值、份额等）- 每日凌晨2点
cron.schedule('0 2 * * *', async () => {
    await runWithRetry(
        '基金详情',
        async () => {
            const crawler = new FundDetailCrawler();
            await crawler.fetchData();
        }
    );
}, {
    timezone: 'Asia/Shanghai'
});

// 4. 公告更新 - 每小时
cron.schedule('0 * * * *', async () => {
    await runWithRetry(
        '公告更新',
        async () => {
            await AnnouncementCrawler.crawlAnnouncements({ usePython: true, maxAge: 7 });
        }
    );
});

// 5. 数据完整性检查 - 每小时
cron.schedule('0 * * * *', async () => {
    if (config.integrity.enable) {
        try {
            const checker = new DataIntegrityChecker();
            await checker.runAllChecks();
        } catch (error) {
            console.error('❌ 数据完整性检查失败:', error.message);
            AlertManager.sendFormattedAlert('INTEGRITY_CHECK_FAILED', {
                error: error.message,
            });
        }
    }
});

// 6. 收盘后更新日线数据 - 交易日 15:05
cron.schedule('5 15 * * 1-5', async () => {
    await runWithRetry(
        '收盘日线更新',
        async () => {
            const crawler = new SinaCrawler();
            const results = await crawler.fetchData();
            await crawler.saveToDatabase(results);
            console.log(`📊 收盘数据获取完成: ${results.length} 只基金`);
        }
    );
}, {
    timezone: 'Asia/Shanghai'
});

// 7. 派息率更新 - 交易日 15:10
cron.schedule('10 15 * * 1-5', async () => {
    await runWithRetry(
        '派息率',
        async () => {
            const crawler = new YieldCrawler();
            await crawler.fetchData();
        }
    );
}, {
    timezone: 'Asia/Shanghai'
});

// 8. 告警历史清理 - 每天凌晨3点
cron.schedule('0 3 * * *', async () => {
    try {
        AlertManager.cleanup(7); // 保留7天
    } catch (error) {
        console.error('❌ 告警清理失败:', error.message);
    }
});

console.log('📋 已配置定时任务:');
console.log('  • 实时行情: 每5分钟 (交易日 9:00-15:00)');
console.log('  • 东财深度: 每30分钟 (交易日 9:00-15:00)');
console.log('  • 基金详情: 每日凌晨 2:00');
console.log('  • 收盘日线: 交易日 15:05');
console.log('  • 派息率: 交易日 15:10');
console.log('  • 公告更新: 每小时');
console.log('  • 数据完整性检查: 每小时');
console.log('  • 告警历史清理: 每日凌晨 3:00');

// Python爬虫备份任务
console.log('\n📋 Python备份爬虫:');
console.log('  • 当Node.js爬虫失败时自动触发');
console.log('  • 每日全量备份运行');

console.log('\n💡 提示: 保持此进程运行即可自动执行\n');

// 心跳检测和监控
const heartbeat = setInterval(() => {
    const stats = AlertManager.getStats();
    const now = new Date().toLocaleString();

    console.log(`💓 ${now} - 系统运行正常`);
    console.log(`📊 告警统计: 总计 ${stats.total} 条 (24小时内 ${stats.last24Hours} 条)`);

    // 检查告警频率
    if (stats.last24Hours > 10) {
        AlertManager.sendAlert({
            type: 'HIGH_ALERT_RATE',
            severity: 'medium',
            message: `24小时内告警数量较多: ${stats.last24Hours} 条`,
            details: stats,
        });
    }
}, 60000); // 每分钟心跳一次

// 优雅的进程终止
process.on('SIGINT', () => {
    console.log('\n🛑 收到终止信号，正在停止调度器...');
    clearInterval(heartbeat);
    process.exit(0);
});

process.on('SIGTERM', () => {
    console.log('\n🛑 收到终止信号，正在停止调度器...');
    clearInterval(heartbeat);
    process.exit(0);
});
