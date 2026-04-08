#!/usr/bin/env node
/**
 * 全量数据采集脚本
 */

const crawlerManager = require('../crawlers');

async function main() {
    try {
        const stats = await crawlerManager.runAll();
        process.exit(0);
    } catch (error) {
        console.error('采集失败:', error);
        process.exit(1);
    }
}

main();
