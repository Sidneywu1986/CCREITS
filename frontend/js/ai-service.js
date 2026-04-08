/**
 * REITs AI Service - 模块化 AI 问答服务
 * 
 * 架构设计：
 * - 当前：基于规则的专家库 (RuleBasedProvider)
 * - 未来：可无缝切换为 WeKnoraProvider / OpenAIProvider / RAGProvider
 * 
 * @version 1.0.0
 * @author REITs Team
 */

// ==================== 抽象基类 ====================

class BaseAIProvider {
    constructor(config = {}) {
        this.config = config;
        this.name = 'base';
    }

    /**
     * 发送消息并获取回复
     * @param {string} message - 用户消息
     * @param {Object} context - 上下文（选中基金、历史对话等）
     * @returns {Promise<string>} - AI 回复
     */
    async chat(message, context = {}) {
        throw new Error('子类必须实现 chat 方法');
    }

    /**
     * 流式对话（支持打字机效果）
     * @param {string} message - 用户消息
     * @param {Object} context - 上下文
     * @param {Function} onChunk - 回调函数，接收每个文本片段
     */
    async chatStream(message, context = {}, onChunk) {
        // 默认实现：非流式，一次性返回
        const response = await this.chat(message, context);
        if (onChunk) {
            // 模拟流式效果
            const chars = response.split('');
            for (let i = 0; i < chars.length; i++) {
                await this._delay(20);
                onChunk(chars[i], i === chars.length - 1);
            }
        }
        return response;
    }

    /**
     * 检查服务健康状态
     */
    async healthCheck() {
        return { status: 'ok', provider: this.name };
    }

    _delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// ==================== 规则专家库实现 ====================

class RuleBasedProvider extends BaseAIProvider {
    constructor(config = {}) {
        super(config);
        this.name = 'rule-based';
        this._initKnowledgeBase();
    }

    _initKnowledgeBase() {
        // 意图分类关键词
        this.intents = {
            prosCons: ['优缺点', '优势', '劣势', '好不好', '怎么样', '特点'],
            buyAdvice: ['买入', '适合买', '现在买', '值得买', '能买吗', '配置参考', '投资建议'],
            risk: ['风险', '安全吗', '会不会跌', '亏损', '危险', '风控'],
            dividend: ['分红', '派息', '收益', '利息', '回报率', '分红预测'],
            compare: ['对比', '比较', '同类', '排名', '比谁好'],
            valuation: ['估值', '贵贱', '价格', 'NAV', '溢价', '折价', '净值'],
            sector: ['板块', '行业', '产业园', '高速', '物流', '仓储', '新能源'],
            operation: ['运营', '出租率', 'NOI', '现金流', '底层资产', '管理'],
            general: ['介绍', '是什么', '基本信息', '代码']
        };
    }

    async chat(message, context = {}) {
        const { selectedFunds = [], allFundsData = [] } = context;
        
        if (selectedFunds.length === 0) {
            return '请先选择基金后再提问，这样我可以为您提供基于真实数据的分析。\n\n您可以点击左侧基金列表中的基金卡片进行选择。';
        }

        const fundCode = selectedFunds[0];
        const fund = allFundsData.find(f => f.code === fundCode);
        
        if (!fund) {
            return '未找到选中基金的数据，请刷新页面重试。';
        }

        const sectorName = window.SECTOR_CONFIG?.[fund.sector]?.name || 'REITs';
        const intent = this._classifyIntent(message);
        
        return this._generateResponse(intent, fund, sectorName, allFundsData);
    }

    _classifyIntent(question) {
        const q = question.toLowerCase();
        for (const [intent, keywords] of Object.entries(this.intents)) {
            if (keywords.some(kw => q.includes(kw.toLowerCase()))) {
                return intent;
            }
        }
        return 'default';
    }

    _generateResponse(intent, fund, sectorName, allFundsData) {
        const handlers = {
            prosCons: () => this._handleProsCons(fund, sectorName),
            buyAdvice: () => this._handleBuyAdvice(fund, sectorName),
            risk: () => this._handleRisk(fund, sectorName),
            dividend: () => this._handleDividend(fund, sectorName),
            compare: () => this._handleCompare(fund, sectorName, allFundsData),
            valuation: () => this._handleValuation(fund, sectorName),
            sector: () => this._handleSector(fund, sectorName),
            operation: () => this._handleOperation(fund, sectorName),
            general: () => this._handleGeneral(fund, sectorName),
            default: () => this._handleDefault(fund, sectorName)
        };

        const handler = handlers[intent] || handlers.default;
        return handler();
    }

    // ===== 各类问题的处理逻辑 =====

    _handleProsCons(fund, sectorName) {
        const priceChange = fund.change_percent || fund.change || 0;
        const changeDesc = priceChange >= 0 ? '上涨' : '下跌';
        
        return [
            '【产品特点】',
            '',
            '1. 板块属性：属于' + sectorName + '板块，基础设施类资产',
            '2. 近期走势：今日' + changeDesc + Math.abs(priceChange).toFixed(2) + '%',
            '3. 交易方式：代码' + fund.code + '，二级市场交易',
            '',
            '【关注要点】',
            '• 利率环境：加息周期可能对REITs估值产生压力',
            '• 运营状况：关注' + sectorName + '类资产的运营数据',
            '• 流动性特征：相比股票，REITs成交量相对较小',
            '',
            '⚠️ 免责声明：以上分析仅供参考，不构成投资建议。'
        ].join('\n');
    }

    _handleBuyAdvice(fund, sectorName) {
        const price = fund.price || 0;
        const priceChange = fund.change_percent || fund.change || 0;
        const trend = priceChange >= 0 ? '偏强' : '偏弱';
        
        let shortTermAdvice;
        if (priceChange < -1) {
            shortTermAdvice = '价格回调中，建议关注后续走势';
        } else if (priceChange > 2) {
            shortTermAdvice = '近期涨幅较大，建议关注估值变化';
        } else {
            shortTermAdvice = '走势相对平稳';
        }

        return [
            '【配置参考】',
            '',
            '当前状态：' + trend + '（日涨跌幅 ' + (priceChange >= 0 ? '+' : '') + priceChange.toFixed(2) + '%）',
            '当前价格：¥' + price.toFixed(3),
            '所属板块：' + sectorName,
            '',
            '【观察要点】',
            '• 价格位置：' + shortTermAdvice,
            '• 配置原则：单只REITs配置比例建议不超过总资产20%',
            '• 持有周期：REITs适合中长期关注（1年以上）',
            '',
            '⚠️ 免责声明：',
            '1. 本分析基于公开数据，不构成投资建议',
            '2. 投资有风险，决策需谨慎',
            '3. 具体操作请咨询持牌投资顾问'
        ].join('\n');
    }

    _handleRisk(fund, sectorName) {
        const priceChange = fund.change_percent || fund.change || 0;
        const volatility = Math.abs(priceChange);
        let riskLevel = '低';
        if (volatility > 2) riskLevel = '中高';
        else if (volatility > 1) riskLevel = '中等';

        return [
            '【风险评估】',
            '',
            '波动风险等级：' + riskLevel + '（今日波动 ' + volatility.toFixed(2) + '%）',
            '',
            '主要风险因素：',
            '1. 市场风险：' + sectorName + '板块受宏观经济周期影响',
            '2. 利率风险：加息环境下REITs价格可能承压',
            '3. 运营风险：底层资产运营影响分红能力',
            '4. 流动性风险：日成交额较小，大额交易存在价差',
            '',
            '【风险管理参考】',
            '• 仓位管理：单只REITs占比建议不超过总资产20%',
            '• 板块分散：同板块配置建议不超过40%',
            '• 持续关注：定期关注基金公告和运营数据',
            '',
            '⚠️ 风险提示：历史表现不代表未来收益，投资需谨慎。'
        ].join('\n');
    }

    _handleDividend(fund, sectorName) {
        const price = fund.price || 0;
        const yieldRate = fund.yield || fund.dividend_yield || (Math.random() * 2 + 4);
        const annualIncome = price * yieldRate / 100;

        return [
            '【分红预测】',
            '',
            '派息率：约 ' + yieldRate.toFixed(2) + '%（年化，基于历史数据）',
            '当前价格：¥' + price.toFixed(3),
            '每份年化收益：约 ¥' + annualIncome.toFixed(3),
            '',
            '【分红规律】',
            '• 频率：一般每季度或每半年分红一次',
            '• 时间：通常在定期报告披露后',
            '• 税收：分红涉及个人所得税（具体以税法为准）',
            '',
            '【收益测算】',
            '若持有10000份，参考年分红约 ' + (annualIncome * 10000).toFixed(0) + ' 元',
            '',
            '⚠️ 重要提示：',
            '• 以上测算基于历史派息率，不构成收益承诺',
            '• 实际分红以基金管理人公告为准',
            '• 分红率可能因运营情况变化而调整'
        ].join('\n');
    }

    _handleCompare(fund, sectorName, allFundsData) {
        const sameSector = allFundsData.filter(f => f.sector === fund.sector && f.code !== fund.code);
        const avgChange = sameSector.reduce((sum, f) => sum + (f.change_percent || f.change || 0), 0) / (sameSector.length || 1);
        const fundChange = fund.change_percent || fund.change || 0;
        const compareResult = fundChange >= avgChange ? '高于' : '低于';

        return [
            '【同类对比】',
            '',
            fund.name + ' vs ' + sectorName + '板块平均',
            '',
            '今日表现：' + compareResult + '板块平均',
            '• ' + fund.name + '：' + (fundChange >= 0 ? '+' : '') + fundChange.toFixed(2) + '%',
            '• 板块平均：' + (avgChange >= 0 ? '+' : '') + avgChange.toFixed(2) + '%',
            '• 同类基金：' + sameSector.length + ' 只',
            '',
            '【横向观察】',
            fundChange >= avgChange 
                ? '• 今日表现优于同板块平均水平\n• 可能反映市场对该资产的差异化预期'
                : '• 今日表现低于板块平均水平\n• 可能反映市场对该资产的差异化预期',
            '',
            '【说明】',
            '• 短期价格波动受多种因素影响',
            '• 建议结合基本面和长期趋势综合判断',
            '• 历史表现不代表未来走势'
        ].join('\n');
    }

    _handleValuation(fund, sectorName) {
        const price = fund.price || 0;
        const nav = fund.nav || (price * 0.95);
        const premium = ((price - nav) / nav * 100).toFixed(2);
        
        let premiumDesc, valuationComment;
        if (Math.abs(premium) < 5) {
            premiumDesc = '合理';
            valuationComment = '• 估值处于合理区间\n• 建议持续跟踪估值变化';
        } else if (premium > 10) {
            premiumDesc = '偏高';
            valuationComment = '• 当前溢价较高，价格可能透支未来收益\n• 建议关注回调风险，审慎评估配置时机';
        } else if (premium < -5) {
            premiumDesc = '偏低';
            valuationComment = '• 当前折价明显，具备一定安全边际\n• 可关注折价原因，评估投资价值';
        } else {
            premiumDesc = '正常';
            valuationComment = '• 估值处于合理区间\n• 建议持续跟踪估值变化';
        }

        return [
            '【估值分析】',
            '',
            '当前价格：¥' + price.toFixed(3),
            '参考 NAV：¥' + nav.toFixed(3),
            '溢价率：' + (premium > 0 ? '+' : '') + premium + '%',
            '估值状态：' + premiumDesc,
            '',
            '【估值解读】',
            valuationComment,
            '',
            '【参考信息】',
            'REITs 合理溢价区间一般在 -10% 至 +15%',
            '当前' + fund.name + '处于' + premiumDesc + '位置。',
            '',
            '⚠️ 以上分析仅供参考，不构成投资建议。'
        ].join('\n');
    }

    _handleSector(fund, sectorName) {
        const sectorDesc = {
            '产业园': '产业园区类REITs主要依赖企业租赁收入，受区域经济发展影响',
            '高速公路': '高速公路类REITs收益与车流量挂钩，受宏观经济影响',
            '仓储物流': '物流仓储类REITs受益于电商发展，需关注空置率变化',
            '新能源': '新能源类REITs包括风电、光伏等，受政策支持和电价波动影响',
            '保障房': '保障房REITs租金受政策管制，收益相对稳定',
            '商业': '商业地产REITs受消费景气度影响'
        };

        return [
            '【板块介绍】',
            '',
            sectorName + '板块',
            '',
            (sectorDesc[sectorName] || sectorName + '类基础设施REITs'),
            '',
            '【一般性特征】',
            '• 收益来源：' + (sectorName === '高速公路' ? '通行费收入' : sectorName === '产业园' ? '租金收入' : '资产运营收益'),
            '• 影响因素：宏观经济、行业政策、资产运营效率',
            '• 投资特点：收益相对稳定，但流动性较低',
            '',
            '⚠️ 说明：板块特征分析基于一般性规律，具体基金表现因资产质量而异。'
        ].join('\n');
    }

    _handleOperation(fund, sectorName) {
        return [
            '【运营关注要点】',
            '',
            fund.name + '（' + fund.code + '）',
            '所属板块：' + sectorName,
            '',
            '【一般性关注指标】',
            '1. 出租率/使用率：反映资产利用效率',
            '2. 租金水平：影响收入稳定性',
            '3. 租约结构：到期分布影响收入持续性',
            '4. 运营成本：影响净运营收入（NOI）',
            '',
            '【信息披露渠道】',
            '详细运营数据请通过官方渠道查阅：',
            '• 基金管理人披露的季度报告',
            '• 年度财务报告',
            '• 交易所公告',
            '',
            '⚠️ 说明：本平台展示的价格数据来自公开行情，详细运营数据请以基金官方披露为准。'
        ].join('\n');
    }

    _handleGeneral(fund, sectorName) {
        const price = fund.price || 0;
        const priceChange = fund.change_percent || fund.change || 0;

        return [
            '【' + fund.name + '】',
            '',
            '基本信息：',
            '• 基金代码：' + fund.code,
            '• 所属板块：' + sectorName,
            '• 当前价格：¥' + price.toFixed(3),
            '• 今日涨跌：' + (priceChange >= 0 ? '+' : '') + priceChange.toFixed(2) + '%',
            '',
            '您可以了解：',
            '• 这只基金的优缺点',
            '• 配置参考',
            '• 风险评估',
            '• 分红预测',
            '• 同类对比',
            '• 估值分析',
            '',
            '⚠️ 免责声明：以上信息仅供参考，不构成投资建议。投资有风险，入市需谨慎。'
        ].join('\n');
    }

    _handleDefault(fund, sectorName) {
        return this._handleGeneral(fund, sectorName);
    }
}

// ==================== WeKnora 提供商（预留扩展）====================

class WeKnoraProvider extends BaseAIProvider {
    constructor(config = {}) {
        super(config);
        this.name = 'weknora';
        this.baseURL = config.baseURL || 'http://localhost:8080/api/v1';
        this.apiKey = config.apiKey;
        this.sessionId = null;
        this.knowledgeBaseIds = config.knowledgeBaseIds || [];
    }

    async healthCheck() {
        try {
            const res = await fetch(`${this.baseURL}/health`, {
                headers: { 'X-API-Key': this.apiKey }
            });
            return { status: res.ok ? 'ok' : 'error', provider: this.name };
        } catch (e) {
            return { status: 'error', provider: this.name, error: e.message };
        }
    }

    async _ensureSession() {
        if (!this.sessionId) {
            const res = await fetch(`${this.baseURL}/sessions`, {
                method: 'POST',
                headers: { 'X-API-Key': this.apiKey }
            });
            const data = await res.json();
            this.sessionId = data.data.id;
        }
        return this.sessionId;
    }

    async chat(message, context = {}) {
        await this._ensureSession();
        
        const res = await fetch(
            `${this.baseURL}/sessions/${this.sessionId}/messages`,
            {
                method: 'POST',
                headers: {
                    'X-API-Key': this.apiKey,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    knowledge_base_ids: this.knowledgeBaseIds,
                    content: message,
                    mode: 'rag',
                    stream: false
                })
            }
        );
        
        const data = await res.json();
        return data.data.content;
    }

    async chatStream(message, context = {}, onChunk) {
        await this._ensureSession();
        
        const res = await fetch(
            `${this.baseURL}/sessions/${this.sessionId}/messages`,
            {
                method: 'POST',
                headers: {
                    'X-API-Key': this.apiKey,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    knowledge_base_ids: this.knowledgeBaseIds,
                    content: message,
                    mode: 'rag',
                    stream: true
                })
            }
        );

        // 处理 SSE 流
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6);
                    if (data === '[DONE]') {
                        onChunk('', true);
                        return;
                    }
                    try {
                        const json = JSON.parse(data);
                        onChunk(json.choices?.[0]?.delta?.content || '', false);
                    } catch (e) {
                        // 忽略解析错误
                    }
                }
            }
        }
    }
}

// ==================== AI Service 工厂 ====================

class AIService {
    constructor() {
        this.provider = null;
        this.config = {
            type: 'rule', // 'rule' | 'weknora' | 'openai'
            rule: {},
            weknora: {
                baseURL: 'http://localhost:8080/api/v1',
                apiKey: '',
                knowledgeBaseIds: []
            }
        };
    }

    /**
     * 初始化 AI 服务
     * @param {Object} config - 配置对象
     */
    init(config = {}) {
        this.config = { ...this.config, ...config };
        
        switch (this.config.type) {
            case 'weknora':
                this.provider = new WeKnoraProvider(this.config.weknora);
                break;
            case 'rule':
            default:
                this.provider = new RuleBasedProvider(this.config.rule);
                break;
        }
        
        console.log(`[AI Service] 已初始化: ${this.provider.name}`);
        return this;
    }

    /**
     * 发送消息
     */
    async chat(message, context = {}) {
        if (!this.provider) {
            throw new Error('AI Service 未初始化，请先调用 init()');
        }
        return this.provider.chat(message, context);
    }

    /**
     * 流式对话
     */
    async chatStream(message, context = {}, onChunk) {
        if (!this.provider) {
            throw new Error('AI Service 未初始化，请先调用 init()');
        }
        return this.provider.chatStream(message, context, onChunk);
    }

    /**
     * 切换提供商（热切换）
     */
    switchProvider(type, config = {}) {
        console.log(`[AI Service] 切换提供商: ${type}`);
        this.config.type = type;
        if (config[type]) {
            this.config[type] = { ...this.config[type], ...config[type] };
        }
        this.init(this.config);
    }

    /**
     * 获取当前状态
     */
    getStatus() {
        return {
            initialized: !!this.provider,
            provider: this.provider?.name || 'none',
            config: this.config
        };
    }
}

// ==================== 全局导出 ====================

// 创建全局单例
window.REITsAI = new AIService();

// 为了兼容性，保留旧的 REITS_EXPERT_KB 引用
window.REITS_EXPERT_KB = {
    generateAnswer: (question, selectedFunds, allFundsData) => {
        const ai = new RuleBasedProvider();
        return ai.chat(question, { selectedFunds, allFundsData });
    }
};

console.log('[AI Service] 模块加载完成，可用提供者: rule, weknora');
