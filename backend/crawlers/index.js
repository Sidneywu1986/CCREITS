/**
 * 爬虫调度中心
 * 协调多个爬虫工作，调用中央处理器入库
 */

const CentralProcessor = require('./central-processor');
const SinaCrawler = require('./sina');
const AKShareCrawler = require('./akshare');
const EastMoneyCrawler = require('./eastmoney');
const { spawn } = require('child_process');
const path = require('path');

class CrawlerManager {
    constructor() {
        this.processor = new CentralProcessor();
        this.crawlers = {
            'sina': new SinaCrawler(),
            'akshare': new AKShareCrawler(),
            'eastmoney': new EastMoneyCrawler()
        };
        this.isRunning = false;
    }
    
    /**
     * 运行CNInfo公告爬虫（自动入库）
     */
    async runCNInfoCrawler() {
        console.log('\n[调度器] >>> CNInfo公告同步');
        
        return new Promise((resolve, reject) => {
            const scriptPath = path.join(__dirname, 'cninfo_db_sync.py');
            
            const pythonProcess = spawn('python', [scriptPath, '--all', '--max-count', '30'], {
                cwd: __dirname,
                encoding: 'utf8'
            });
            
            let stdout = '';
            let stderr = '';
            
            pythonProcess.stdout.on('data', (data) => {
                const output = data.toString().trim();
                stdout += output;
                console.log(`[CNInfo] ${output}`);
            });
            
            pythonProcess.stderr.on('data', (data) => {
                stderr += data.toString().trim();
                console.error(`[CNInfo-ERR] ${data.toString().trim()}`);
            });
            
            pythonProcess.on('close', (code) => {
                if (code === 0) {
                    console.log(`[调度器] CNInfo同步完成`);
                    resolve({ success: true, output: stdout });
                } else {
                    console.error(`[调度器] CNInfo同步失败，退出码 ${code}`);
                    resolve({ success: false, error: stderr }); // 失败但不阻断
                }
            });
            
            pythonProcess.on('error', (err) => {
                console.error('[调度器] CNInfo进程启动失败:', err);
                resolve({ success: false, error: err.message }); // 失败但不阻断
            });
        });
    }

    /**
     * 执行全量采集
     */
    async runAll() {
        if (this.isRunning) {
            console.log('[调度器] 已有任务在执行中');
            return;
        }

        this.isRunning = true;
        const startTime = Date.now();
        console.log('========================================');
        console.log('[调度器] 开始全量数据采集');
        console.log('========================================');

        try {
            // 1. 新浪爬虫 - 基础行情（优先）
            console.log('\n[调度器] >>> 阶段1: 新浪基础行情');
            const sinaData = await this.crawlers.sina.fetchData();
            await this.processor.receiveData('sina', sinaData);
            console.log(`[调度器] 新浪数据: ${sinaData.length} 条`);

            // 2. AKShare - REITs核心数据
            console.log('\n[调度器] >>> 阶段2: AKShare REITs数据');
            const akData = await this.crawlers.akshare.fetchData();
            await this.processor.receiveData('akshare', akData);
            console.log(`[调度器] AKShare数据: ${akData.length} 条`);

            // 3. 东方财富 - 主力数据
            console.log('\n[调度器] >>> 阶段3: 东方财富深度数据');
            const emData = await this.crawlers.eastmoney.fetchData();
            await this.processor.receiveData('eastmoney', emData);
            console.log(`[调度器] 东财数据: ${emData.length} 条`);

            // 4. CNInfo - 巨潮资讯网公告（自动入库）
            await this.runCNInfoCrawler();

            // 5. 中央处理器融合入库
            console.log('\n[调度器] >>> 阶段5: 数据融合入库');
            const stats = await this.processor.process();

            const duration = ((Date.now() - startTime) / 1000).toFixed(2);
            console.log('\n========================================');
            console.log(`[调度器] 采集完成! 耗时: ${duration}s`);
            console.log(`[调度器] 成功: ${stats.success}, 失败: ${stats.failed}`);
            console.log('========================================');

            return stats;
        } catch (error) {
            console.error('[调度器] 采集失败:', error);
            throw error;
        } finally {
            this.isRunning = false;
        }
    }

    /**
     * 只采集基础行情（快速模式）
     */
    async runQuick() {
        if (this.isRunning) {
            console.log('[调度器] 已有任务在执行中');
            return;
        }

        this.isRunning = true;
        console.log('[调度器] 开始快速采集（仅行情）');

        try {
            const sinaData = await this.crawlers.sina.fetchData();
            await this.processor.receiveData('sina', sinaData);
            const stats = await this.processor.process();
            
            console.log(`[调度器] 快速采集完成: 成功${stats.success}`);
            return stats;
        } catch (error) {
            console.error('[调度器] 快速采集失败:', error);
            throw error;
        } finally {
            this.isRunning = false;
        }
    }

    /**
     * 启动定时任务
     */
    startScheduled() {
        console.log('[调度器] 启动定时任务');
        
        // 交易时间内每5分钟采集一次行情
        setInterval(async () => {
            const hour = new Date().getHours();
            const minute = new Date().getMinutes();
            
            // 交易时间: 9:30-11:30, 13:00-15:00
            const isTrading = (hour === 9 && minute >= 30) || 
                            (hour === 10) || 
                            (hour === 11 && minute <= 30) ||
                            (hour === 13) || 
                            (hour === 14) ||
                            (hour === 15 && minute === 0);
            
            if (isTrading) {
                console.log('[调度器] 触发定时采集');
                await this.runQuick().catch(console.error);
            }
        }, 5 * 60 * 1000); // 5分钟

        // 每小时全量采集一次
        setInterval(async () => {
            console.log('[调度器] 触发全量采集');
            await this.runAll().catch(console.error);
        }, 60 * 60 * 1000); // 1小时
        
        // 每天9:00、15:30爬取CNInfo公告
        setInterval(async () => {
            const hour = new Date().getHours();
            const minute = new Date().getMinutes();
            
            // 开盘前(9:00)和收盘后(15:30)爬取公告
            if ((hour === 9 || hour === 15) && minute === (hour === 9 ? 0 : 30)) {
                console.log('[调度器] 触发CNInfo公告采集');
                await this.runCNInfoCrawler().catch(console.error);
            }
        }, 60 * 1000); // 每分钟检查

        console.log('[调度器] 定时任务已启动');
    }
}

// 导出单例
module.exports = new CrawlerManager();
