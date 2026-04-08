-- AI聊REIT功能 - 数据库Schema扩展

-- 1. 用户行为统计表（埋点数据）
CREATE TABLE IF NOT EXISTS user_analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,                 -- 会话ID
    page_path TEXT,                  -- 页面路径
    event_type TEXT,                 -- 事件类型（page_view/click/search等）
    event_data TEXT,                 -- 事件详情（JSON格式）
    user_agent TEXT,                 -- 浏览器信息
    ip_address TEXT,                 -- IP地址（匿名化）
    referrer TEXT,                   -- 来源页面
    duration_ms INTEGER,             -- 停留时长
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2. AI聊天室表
CREATE TABLE IF NOT EXISTS ai_chat_rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_name TEXT NOT NULL,         -- 房间名称
    topic TEXT,                      -- 当前话题
    status TEXT DEFAULT 'active',    -- 状态（active/paused/closed）
    participant_count INTEGER DEFAULT 0, -- 参与人数
    message_count INTEGER DEFAULT 0, -- 消息数
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 3. AI角色配置表
CREATE TABLE IF NOT EXISTS ai_personas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,              -- AI名称
    avatar TEXT,                     -- 头像URL
    role_type TEXT,                  -- 角色类型（analyst/trader/researcher）
    personality TEXT,                -- 人设描述
    system_prompt TEXT,              -- 系统提示词
    expertise TEXT,                  -- 专业领域（JSON数组）
    temperature REAL DEFAULT 0.7,    -- 创造性程度
    voice_style TEXT,                -- 语言风格
    is_active INTEGER DEFAULT 1,     -- 是否激活
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 4. AI聊天记录表
CREATE TABLE IF NOT EXISTS ai_chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL,        -- 房间ID
    sender_type TEXT NOT NULL,       -- 发送者类型（ai/human/system）
    sender_id TEXT,                  -- 发送者ID（AI名称或用户session）
    sender_name TEXT,                -- 显示名称
    message TEXT NOT NULL,           -- 消息内容
    message_type TEXT DEFAULT 'text', -- 消息类型（text/image/link）
    reply_to INTEGER,                -- 回复哪条消息
    sentiment_score REAL,            -- 情感分析分数
    topics TEXT,                     -- 涉及话题（JSON数组）
    mentioned_funds TEXT,            -- 提到的基金代码
    is_hot_topic INTEGER DEFAULT 0,  -- 是否热点话题
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (room_id) REFERENCES ai_chat_rooms(id)
);

-- 5. 热点话题表
CREATE TABLE IF NOT EXISTS hot_topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,             -- 话题内容
    category TEXT,                   -- 分类（market/policy/fund）
    heat_score REAL,                 -- 热度分数
    related_funds TEXT,              -- 相关基金
    source_urls TEXT,                -- 来源链接（JSON）
    ai_discussed INTEGER DEFAULT 0,  -- AI是否讨论过
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 6. REIT信源配置表
CREATE TABLE IF NOT EXISTS reit_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT NOT NULL,       -- 信源名称
    source_type TEXT,                -- 类型（news/research/gov/forum）
    source_url TEXT,                 -- 地址
    api_endpoint TEXT,               -- API接口
    fetch_interval INTEGER,          -- 抓取间隔（分钟）
    last_fetch_at DATETIME,          -- 最后抓取时间
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_analytics_session ON user_analytics(session_id);
CREATE INDEX IF NOT EXISTS idx_analytics_page ON user_analytics(page_path);
CREATE INDEX IF NOT EXISTS idx_analytics_time ON user_analytics(created_at);
CREATE INDEX IF NOT EXISTS idx_chat_room ON ai_chat_messages(room_id);
CREATE INDEX IF NOT EXISTS idx_chat_time ON ai_chat_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_hot_topics_score ON hot_topics(heat_score DESC);

-- 初始化3个AI角色
INSERT OR IGNORE INTO ai_personas (name, avatar, role_type, personality, system_prompt, expertise, temperature, voice_style) VALUES 
(
    '老李',
    'https://api.dicebear.com/7.x/avataaars/svg?seed=laoli&backgroundColor=b6e3f4',
    'analyst',
    '资深市场分析师，从业20年，说话稳重，喜欢用数据说话，偶尔带点幽默感',
    '你是一位资深的REITs市场分析师，拥有20年资本市场经验。你的分析风格严谨务实，善于用数据支撑观点。你会关注宏观经济、政策变化对REITs市场的影响。回答简洁有力，一般不超过3句话。',
    '["宏观经济", "政策解读", "市场趋势", "风险评估"]',
    0.6,
    '稳重专业，条理清晰，偶尔幽默'
),
(
    '小陈',
    'https://api.dicebear.com/7.x/avataaars/svg?seed=xiaochen&backgroundColor=ffd5dc',
    'trader',
    '年轻活跃的散户投资者，思维活跃，关注短期机会，喜欢提问和质疑',
    '你是一位活跃的个人投资者，投资风格偏激进，喜欢研究短期交易机会。你善于发现市场中的异常波动和投资机会，经常提出犀利的问题。你会用通俗易懂的语言解释复杂的金融概念。',
    '["技术分析", "短线操作", "个股研究", "情绪判断"]',
    0.8,
    '活泼直接，充满好奇，偶尔质疑'
),
(
    '王博士',
    'https://api.dicebear.com/7.x/avataaars/svg?seed=wang&backgroundColor=c0aede',
    'researcher',
    '学术派研究员，深耕REITs领域，善于挖掘底层资产价值，说话严谨',
    '你是一位REITs领域的学术研究员，专注于底层资产分析和长期价值投资研究。你善于从财务报表、资产质量角度分析REITs的内在价值。你的回答详实专业，喜欢引用研究数据和案例。',
    '["资产评估", "财务报表", "底层资产", "长期价值", "行业研究"]',
    0.5,
    '严谨学术，数据详实，深度分析'
);

-- 初始化信源配置
INSERT OR IGNORE INTO reit_sources (source_name, source_type, source_url, fetch_interval) VALUES
('新浪财经-REIT', 'news', 'https://finance.sina.com.cn/reits/', 30),
('东方财富-REIT', 'news', 'https://fund.eastmoney.com/REIT/', 30),
('上交所-REIT', 'gov', 'http://www.sse.com.cn/reits/', 60),
('深交所-REIT', 'gov', 'http://www.szse.cn/reits/', 60),
('中国REITs论坛', 'forum', 'https://www.chinareits.org/', 120),
('投中网-REIT', 'research', 'https://www.chinaventure.com.cn/', 120);

-- 初始化默认聊天室
INSERT OR IGNORE INTO ai_chat_rooms (id, room_name, topic, status) VALUES 
(1, 'REIT投资交流群', '今日REITs市场热点讨论', 'active');
