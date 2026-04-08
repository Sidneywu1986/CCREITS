#!/usr/bin/env node
/**
 * CNInfo公告自动爬取定时任务
 * 每天定时爬取所有REIT的最新公告
 */

const { spawn } = require('child_process');
const path = require('path');

const CRAWLER_DIR = path.join(__dirname, '..', 'crawlers');

/**
 * 执行Python同步脚本
 */
function runSync() {
    return new Promise((resolve, reject) => {
        const scriptPath = path.join(CRAWLER_DIR, 'cninfo_db_sync.py');
        
        console.log(`[${new Date().toISOString()}] 启动CNInfo公告同步...`);
        
        const pythonProcess = spawn('python', [scriptPath, '--all', '--max-count', '30'], {
            cwd: CRAWLER_DIR,
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
            const output = data.toString().trim();
            stderr += output;
            console.error(`[CNInfo-ERR] ${output}`);
        });
        
        pythonProcess.on('close', (code) => {
            if (code === 0) {
                console.log(`[${new Date().toISOString()}] CNInfo同步完成`);
                resolve({ success: true, output: stdout });
            } else {
                reject(new Error(`同步失败，退出码 ${code}: ${stderr}`));
            }
        });
        
        pythonProcess.on('error', (err) => {
            reject(err);
        });
    });
}

/**
 * 运行单次同步
 */
async function runOnce() {
    try {
        const result = await runSync();
        console.log('✅ 自动同步完成');
        return result;
    } catch (error) {
        console.error('❌ 自动同步失败:', error.message);
        throw error;
    }
}

/**
 * 启动定时任务
 * 每天9:00、12:00、15:00、18:00运行
 */
function startScheduler() {
    console.log('========================================');
    console.log('[Scheduler] CNInfo自动同步已启动');
    console.log('[Scheduler] 定时: 每天 9:00, 12:00, 15:00, 18:00');
    console.log('========================================');
    
    // 每分钟检查一次是否需要运行
    setInterval(async () => {
        const now = new Date();
        const hour = now.getHours();
        const minute = now.getMinutes();
        
        // 在指定时间运行（整点）
        if (minute === 0 && [9, 12, 15, 18].includes(hour)) {
            console.log(`\n[${now.toISOString()}] 触发定时同步...`);
            try {
                await runOnce();
            } catch (error) {
                console.error('定时同步失败:', error);
            }
        }
    }, 60 * 1000); // 每分钟检查一次
    
    // 启动时先运行一次
    console.log('[Scheduler] 启动时立即运行一次...');
    runOnce().catch(console.error);
}

// 命令行参数处理
const args = process.argv.slice(2);

if (args.includes('--once')) {
    // 单次运行
    runOnce().then(() => process.exit(0)).catch(() => process.exit(1));
} else if (args.includes('--schedule')) {
    // 定时模式
    startScheduler();
} else {
    // 默认单次运行
    runOnce().then(() => process.exit(0)).catch(() => process.exit(1));
}

module.exports = { runOnce, startScheduler };
