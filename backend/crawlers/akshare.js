/**
 * AKShare爬虫
 * 职责：获取REITs净值、派息率、财务数据等
 */

const axios = require('axios');
const { db } = require('../database/db');

const SOURCE_NAME = 'akshare';
const AK_API_BASE = 'http://127.0.0.1:5000'; // AKShare服务地址

class AKShareCrawler {
    constructor() {
        this.hasAKService = false;
    }

    async checkService() {
        try {
            await axios.get(`${AK_API_BASE}/health`, { timeout: 5000 });
            this.hasAKService = true;
            return true;
        } catch (error) {
            console.log(`[${SOURCE_NAME}] AKShare服务不可用: ${error.message}`);
            return false;
        }
    }

    async fetchData() {
        if (!await this.checkService()) {
            return [];
        }

        const codes = await this.getFundCodes();
        console.log(`[${SOURCE_NAME}] 获取 ${codes.length} 只REITs数据`);

        const results = [];
        
        for (const code of codes) {
            try {
                const data = await this.fetchFundData(code);
                if (data) {
                    results.push(data);
                }
                // 延时避免请求过快
                await new Promise(r => setTimeout(r, 200));
            } catch (error) {
                console.error(`[${SOURCE_NAME}] ${code} 获取失败:`, error.message);
            }
        }

        return results;
    }

    async getFundCodes() {
        return new Promise((resolve, reject) => {
            db.all(
                "SELECT fund_code FROM business.funds WHERE status = 'listed' OR status IS NULL",
                [],
                (err, rows) => {
                    if (err) reject(err);
                    else resolve(rows.map(r => r.fund_code));
                }
            );
        });
    }

    async fetchFundData(code) {
        // 获取REITs实时行情（含净值等）
        const response = await axios.get(
            `${AK_API_BASE}/reit_realtime`,
            { params: { symbol: code }, timeout: 10000 }
        );

        if (!response.data) return null;

        const d = response.data;
        
        return {
            fund_code: code,
            name: d.名称 || null,
            price: this.parseNumber(d.最新价),
            change_percent: this.parseNumber(d.涨跌幅),
            volume: this.parseNumber(d.成交量),
            // REITs特有数据
            nav: this.parseNumber(d.净值),  // 单位净值
            premium: this.parseNumber(d.溢价率), // 溢折价率
            yield: this.parseNumber(d.派息率) * 100, // 转换为万分之几存储
            market_cap: this.parseNumber(d.总市值) / 100000000, // 转换为亿
            // 财务指标
            debt_ratio: this.parseNumber(d.资产负债率),
            // 元数据
            _source: SOURCE_NAME,
            _fetch_time: new Date().toISOString()
        };
    }

    parseNumber(value) {
        if (value === undefined || value === null || value === '-') return null;
        const num = parseFloat(value);
        return isNaN(num) ? null : num;
    }

    /**
     * 获取历史数据（用于补充缺失数据）
     */
    async fetchHistory(code, days = 30) {
        if (!this.hasAKService) return [];
        
        try {
            const response = await axios.get(
                `${AK_API_BASE}/reit_hist`,
                { 
                    params: { symbol: code, period: 'daily', days },
                    timeout: 15000 
                }
            );
            return response.data || [];
        } catch (error) {
            console.error(`[${SOURCE_NAME}] ${code} 历史数据获取失败:`, error.message);
            return [];
        }
    }

    /**
     * 获取REITs分红数据
     */
    async fetchDividend(code) {
        if (!this.hasAKService) return [];
        
        try {
            const response = await axios.get(
                `${AK_API_BASE}/reit_dividend`,
                { params: { symbol: code }, timeout: 10000 }
            );
            return response.data || [];
        } catch (error) {
            console.error(`[${SOURCE_NAME}] ${code} 分红数据获取失败:`, error.message);
            return [];
        }
    }
}

module.exports = AKShareCrawler;
