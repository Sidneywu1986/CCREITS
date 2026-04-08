/**
 * CNInfo爬虫包装器
 * 调用Python爬虫脚本获取巨潮资讯网公告
 */

const { spawn } = require('child_process');
const path = require('path');

/**
 * 爬取单只REIT公告
 * @param {string} code - REIT代码
 * @param {number} maxCount - 最大数量
 * @returns {Promise<Object>}
 */
function crawlSingleREIT(code, maxCount = 30) {
    return new Promise((resolve, reject) => {
        const scriptPath = path.join(__dirname, 'cninfo_crawler.py');
        const outputDir = path.join(__dirname, '..', '..', 'data', 'announcements');
        
        const args = [
            scriptPath,
            '--keyword', code,
            '--max-count', maxCount.toString(),
            '--output', outputDir
        ];
        
        console.log(`🚀 启动爬虫: python ${args.join(' ')}`);
        
        const pythonProcess = spawn('python', args, {
            cwd: __dirname,
            encoding: 'utf8'
        });
        
        let stdout = '';
        let stderr = '';
        
        pythonProcess.stdout.on('data', (data) => {
            stdout += data.toString();
            console.log(`[爬虫输出] ${data.toString().trim()}`);
        });
        
        pythonProcess.stderr.on('data', (data) => {
            stderr += data.toString();
            console.error(`[爬虫错误] ${data.toString().trim()}`);
        });
        
        pythonProcess.on('close', (code) => {
            if (code === 0) {
                resolve({
                    success: true,
                    code: code,
                    output: stdout,
                    message: `成功爬取 ${code} 公告`
                });
            } else {
                reject(new Error(`爬虫退出码 ${code}: ${stderr}`));
            }
        });
        
        pythonProcess.on('error', (err) => {
            reject(err);
        });
    });
}

/**
 * 批量爬取全部REIT公告
 * @param {Object} options - 选项
 * @returns {Promise<Object>}
 */
function crawlAllREITs(options = {}) {
    return new Promise((resolve, reject) => {
        const { maxWorkers = 3, maxCount = 30 } = options;
        const scriptPath = path.join(__dirname, 'batch_crawl_all_reits.py');
        const outputDir = path.join(__dirname, '..', '..', 'data', 'announcements');
        
        const args = [
            scriptPath,
            '--workers', maxWorkers.toString(),
            '--max-count', maxCount.toString(),
            '--output', outputDir
        ];
        
        console.log(`🚀 启动批量爬虫: python ${args.join(' ')}`);
        
        const pythonProcess = spawn('python', args, {
            cwd: __dirname,
            encoding: 'utf8'
        });
        
        let stdout = '';
        let stderr = '';
        
        pythonProcess.stdout.on('data', (data) => {
            stdout += data.toString();
            console.log(`[批量爬虫] ${data.toString().trim()}`);
        });
        
        pythonProcess.stderr.on('data', (data) => {
            stderr += data.toString();
            console.error(`[批量爬虫错误] ${data.toString().trim()}`);
        });
        
        pythonProcess.on('close', (code) => {
            if (code === 0) {
                resolve({
                    success: true,
                    output: stdout,
                    message: '批量爬取完成'
                });
            } else {
                reject(new Error(`批量爬虫退出码 ${code}: ${stderr}`));
            }
        });
        
        pythonProcess.on('error', (err) => {
            reject(err);
        });
    });
}

module.exports = {
    crawlSingleREIT,
    crawlAllREITs
};
