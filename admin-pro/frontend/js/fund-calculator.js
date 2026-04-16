/**
 * REITs 基金实时计算工具
 * 计算溢价率、流通市值等可推导指标
 */

const FundCalculator = {
    /**
     * 计算溢价率
     * @param {number} price - 当前市价
     * @param {number} nav - 单位净值
     * @returns {number} 溢价率（%）
     */
    calculatePremium(price, nav) {
        if (!price || !nav || nav <= 0) return null;
        return ((price - nav) / nav * 100).toFixed(2);
    },

    /**
     * 计算流通市值
     * @param {number} price - 当前市价
     * @param {number} shares - 流通份额（万份）
     * @returns {number} 流通市值（亿元）
     */
    calculateMarketCap(price, shares) {
        if (!price || !shares) return null;
        // 流通份额通常是万份，价格通常是元
        // 市值 = 价格 × 份额 / 10000（转为亿元）
        return (price * shares / 10000).toFixed(2);
    },

    /**
     * 计算派息率（年化）
     * @param {number} price - 当前市价
     * @param {Array} dividends - 分红历史数组 [{date, amount}]
     * @returns {number} 派息率（%）
     */
    calculateYield(price, dividends) {
        if (!price || !dividends || dividends.length === 0) return null;
        
        // 计算过去12个月的分红总额
        const oneYearAgo = new Date();
        oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1);
        
        const annualDividend = dividends
            .filter(d => new Date(d.date) >= oneYearAgo)
            .reduce((sum, d) => sum + d.amount, 0);
        
        if (annualDividend <= 0) return null;
        
        return (annualDividend / price * 100).toFixed(2);
    },

    /**
     * 增强基金数据（添加计算字段）
     * @param {Object} fund - 基金基础数据
     * @returns {Object} 增强后的数据
     */
    enrichFundData(fund) {
        if (!fund) return null;
        
        const enriched = { ...fund };
        
        // 计算溢价率
        if (fund.price && fund.nav) {
            enriched.premium = this.calculatePremium(fund.price, fund.nav);
        }
        
        // 计算流通市值
        if (fund.price && fund.circulating_shares) {
            enriched.market_cap = this.calculateMarketCap(fund.price, fund.circulating_shares);
        }
        
        // 计算派息率
        if (fund.price && fund.dividends) {
            enriched.yield = this.calculateYield(fund.price, fund.dividends);
        }
        
        return enriched;
    },

    /**
     * 批量增强基金数据
     * @param {Array} funds - 基金数组
     * @returns {Array} 增强后的数组
     */
    enrichFundsData(funds) {
        if (!Array.isArray(funds)) return [];
        return funds.map(fund => this.enrichFundData(fund));
    }
};

// 导出
window.FundCalculator = FundCalculator;
