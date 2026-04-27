/**
 * 公告爬虫 V2
 * 调用Python AKShare爬虫获取REITs公告
 */

const { spawn } = require('child_process');
const path = require('path');
const { db } = require('../database/db');

/**
 * 执行Python爬虫脚本
 */
function runPythonCrawler() {
    return new Promise((resolve, reject) => {
        const scriptPath = path.join(__dirname, 'announcement_akshare.py');
        const pythonProcess = spawn('python', [scriptPath], {
            cwd: path.join(__dirname, '..'),
            encoding: 'utf8'
        });
        
        let output = '';
        let errorOutput = '';
        
        pythonProcess.stdout.on('data', (data) => {
            output += data.toString();
            process.stdout.write(data);
        });
        
        pythonProcess.stderr.on('data', (data) => {
            errorOutput += data.toString();
            process.stderr.write(data);
        });
        
        pythonProcess.on('close', (code) => {
            if (code === 0) {
                resolve(output);
            } else {
                reject(new Error(`Python脚本退出码 ${code}: ${errorOutput}`));
            }
        });
    });
}

/**
 * 从数据库获取最新公告
 */
async function getAnnouncementsFromDB(limit = 100, days = 30) {
    return new Promise((resolve, reject) => {
        let sql = `
            SELECT 
                a.*,
                f.fund_name as fund_name,
                f.sector_name
            FROM business.announcements a
            LEFT JOIN business.funds f ON a.fund_code = f.fund_code
            WHERE 1=1
        `;
        
        const params = [];
        
        if (days > 0) {
            sql += ` AND a.publish_date >= CURRENT_DATE - INTERVAL '${days} days'`;
        }
        
        sql += ` ORDER BY a.publish_date DESC, a.id DESC LIMIT ?`;
        params.push(limit);
        
        db.all(sql, params, (err, rows) => {
            if (err) {
                reject(err);
            } else {
                resolve(rows);
            }
        });
    });
}

/**
 * 爬取公告主函数
 */
async function crawlAnnouncements(options = {}) {
    const { usePython = true, maxAge = 7 } = options;
    
    console.log(`\n🚀 开始爬取REITs公告... ${new Date().toLocaleString()}`);
    const startTime = Date.now();
    
    try {
        // 调用Python爬虫
        if (usePython) {
            await runPythonCrawler();
        }
        
        // 从数据库获取最新公告
        const announcements = await getAnnouncementsFromDB(200, maxAge);
        
        const duration = Date.now() - startTime;
        console.log(`✅ 爬取完成: 共 ${announcements.length} 条公告，耗时: ${duration}ms`);
        
        return announcements;
        
    } catch (error) {
        console.error('❌ 爬取失败:', error.message);
        // 返回数据库中的现有数据
        return getAnnouncementsFromDB(200, maxAge);
    }
}

/**
 * 手动触发爬取（用于API调用）
 */
async function triggerCrawl() {
    return crawlAnnouncements({ usePython: true, maxAge: 365 });
}

module.exports = {
    crawlAnnouncements,
    triggerCrawl
};
