#!/usr/bin/env node
/**
 * 基金详情数据爬取脚本
 * 采集：净值、流通份额、机构持仓、债务率等
 */

const FundDetailCrawler = require('../crawlers/fund-detail');

console.log('🚀 启动基金详情爬虫...');
console.log('📊 采集字段：净值、流通份额、机构持仓、债务率、分红记录');
console.log('');

const crawler = new FundDetailCrawler();

crawler.fetchData()
    .then(results => {
        console.log('');
        console.log(`✅ 爬取完成！成功获取 ${results.length} 只基金详情数据`);
        process.exit(0);
    })
    .catch(error => {
        console.error('❌ 爬取失败:', error);
        process.exit(1);
    });
