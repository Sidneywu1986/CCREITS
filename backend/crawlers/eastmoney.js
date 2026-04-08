/**
 * 东方财富爬虫
 * 职责：获取主力资金流向、龙虎榜、机构持仓等深度数据
 */

const axios = require('axios');
const { db } = require('../database/db');

const SOURCE_NAME = 'eastmoney';

class EastMoneyCrawler {
    constructor() {
        this.baseHeaders = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://quote.eastmoney.com/'
        };
    }

    async fetchData() {
        const codes = await this.getFundCodes();
        console.log(`[${SOURCE_NAME}] 获取 ${codes.length} 只基金深度数据`);

        const results = [];
        
        for (const code of codes) {
            try {
                const mainForce = await this.fetchMainForce(code);
                const turnover = await this.fetchTurnover(code);
                
                results.push({
                    fund_code: code,
                    main_inflow: mainForce?.inflow || null,      // 主力净流入
                    main_outflow: mainForce?.outflow || null,    // 主力净流出
                    main_net: mainForce?.net || null,            // 主力净额
                    turnover: turnover || null,                   // 换手率
                    _source: SOURCE_NAME,
                    _fetch_time: new Date().toISOString()
                });
                
                await new Promise(r => setTimeout(r, 300));
            } catch (error) {
                console.error(`[${SOURCE_NAME}] ${code} 获取失败:`, error.message);
            }
        }

        return results;
    }

    async getFundCodes() {
        return new Promise((resolve, reject) => {
            db.all(
                "SELECT code FROM funds WHERE status = 'listed' OR status IS NULL",
                [],
                (err, rows) => {
                    if (err) reject(err);
                    else resolve(rows.map(r => r.code));
                }
            );
        });
    }

    /**
     * 获取主力资金流向
     */
    async fetchMainForce(code) {
        const prefix = code.startsWith('5') ? '1' : '0'; // 1=上海, 0=深圳
        const fullCode = `${prefix}.${code}`;
        
        const url = `https://push2.eastmoney.com/api/qt/stock/fflow/kline/get`;
        
        try {
            const response = await axios.get(url, {
                params: {
                    lmt: 1,
                    klt: 101, // 日K
                    fields1: 'f1,f2,f3,f7',
                    fields2: 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65',
                    secid: fullCode
                },
                headers: this.baseHeaders,
                timeout: 10000
            });

            const klines = response.data?.data?.klines;
            if (!klines || klines.length === 0) return null;

            // 格式: 日期,主力净流入,小单净流入,中单净流入,大单净流入,特大单净流入
            const parts = klines[0].split(',');
            
            return {
                inflow: parseFloat(parts[1]) || 0,  // 主力净流入
                outflow: 0, // 东方财富只给净流入
                net: parseFloat(parts[1]) || 0
            };
        } catch (error) {
            return null;
        }
    }

    /**
     * 获取换手率
     */
    async fetchTurnover(code) {
        const prefix = code.startsWith('5') ? '1' : '0';
        const fullCode = `${prefix}.${code}`;
        
        const url = `https://push2.eastmoney.com/api/qt/stock/get`;
        
        try {
            const response = await axios.get(url, {
                params: {
                    secid: fullCode,
                    fields: 'f43,f44,f45,f46,f47,f48,f57,f58,f60,f170'
                },
                headers: this.baseHeaders,
                timeout: 10000
            });

            const data = response.data?.data;
            if (!data) return null;

            // f51 = 换手率
            return data.f51 || null;
        } catch (error) {
            return null;
        }
    }

    /**
     * 获取龙虎榜数据
     */
    async fetchDragonTiger(code, date) {
        const url = `https://datacenter-web.eastmoney.com/api/data/v1/get`;
        
        try {
            const response = await axios.get(url, {
                params: {
                    sortColumns: 'TRADE_DATE',
                    sortTypes: '-1',
                    pageSize: 50,
                    pageNumber: 1,
                    reportName: 'RPT_DMSK_TS',
                    columns: 'ALL',
                    filter: `(SECURITY_CODE="${code}")`
                },
                headers: this.baseHeaders,
                timeout: 10000
            });

            return response.data?.result?.data || [];
        } catch (error) {
            console.error(`[${SOURCE_NAME}] ${code} 龙虎榜获取失败:`, error.message);
            return [];
        }
    }

    /**
     * 获取机构持仓
     */
    async fetchInstitutionHold(code) {
        const url = `https://datacenter-web.eastmoney.com/api/data/v1/get`;
        
        try {
            const response = await axios.get(url, {
                params: {
                    sortColumns: 'REPORT_DATE',
                    sortTypes: '-1',
                    pageSize: 10,
                    pageNumber: 1,
                    reportName: 'RPT_DMSK_ORG_HOLD',
                    columns: 'ALL',
                    filter: `(SECURITY_CODE="${code}")`
                },
                headers: this.baseHeaders,
                timeout: 10000
            });

            return response.data?.result?.data || [];
        } catch (error) {
            console.error(`[${SOURCE_NAME}] ${code} 机构持仓获取失败:`, error.message);
            return [];
        }
    }
}

module.exports = EastMoneyCrawler;
