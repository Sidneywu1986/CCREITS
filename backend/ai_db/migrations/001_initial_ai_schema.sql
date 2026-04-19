-- AI Database Schema Migration
-- PostgreSQL DDL Script
-- 15 tables with indexes and full-text search support

-- ============================================
-- AI Chat Tables
-- ============================================

-- AI聊天会话表
CREATE TABLE IF NOT EXISTS ai_chat_sessions (
    id SERIAL PRIMARY KEY,
    session_title VARCHAR(255),
    session_type VARCHAR(50) DEFAULT 'general',
    user_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ai_chat_sessions_user_id ON ai_chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_chat_sessions_created_at ON ai_chat_sessions(created_at);

-- AI聊天消息表
CREATE TABLE IF NOT EXISTS ai_chat_messages (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    model VARCHAR(50),
    tokens INTEGER,
    fulltext_vector tsvector,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES ai_chat_sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ai_chat_messages_session_id ON ai_chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_ai_chat_messages_created_at ON ai_chat_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_ai_chat_messages_fulltext ON ai_chat_messages USING GIN(fulltext_vector);

-- AI智能体配置表
CREATE TABLE IF NOT EXISTS ai_chat_agents (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(100) NOT NULL UNIQUE,
    agent_desc TEXT,
    system_prompt TEXT NOT NULL,
    model VARCHAR(50) DEFAULT 'deepseek',
    temperature FLOAT DEFAULT 0.7,
    max_tokens INTEGER DEFAULT 2000,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- Announcement Chat Tables
-- ============================================

-- 公告聊天会话表
CREATE TABLE IF NOT EXISTS announcement_chat_sessions (
    id SERIAL PRIMARY KEY,
    session_title VARCHAR(255),
    user_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ann_chat_sessions_user_id ON announcement_chat_sessions(user_id);

-- 公告聊天消息表
CREATE TABLE IF NOT EXISTS announcement_chat_messages (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    fulltext_vector tsvector,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES announcement_chat_sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ann_chat_messages_session_id ON announcement_chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_ann_chat_messages_fulltext ON announcement_chat_messages USING GIN(fulltext_vector);

-- 公告聊天上下文关联表
CREATE TABLE IF NOT EXISTS announcement_chat_contexts (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL,
    announcement_id INTEGER NOT NULL,
    relevance_score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES announcement_chat_sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ann_chat_contexts_session_id ON announcement_chat_contexts(session_id);
CREATE INDEX IF NOT EXISTS idx_ann_chat_contexts_announcement_id ON announcement_chat_contexts(announcement_id);

-- ============================================
-- Research Tables
-- ============================================

-- 投研会话表
CREATE TABLE IF NOT EXISTS research_sessions (
    id SERIAL PRIMARY KEY,
    session_title VARCHAR(255),
    user_id INTEGER,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_research_sessions_user_id ON research_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_research_sessions_status ON research_sessions(status);

-- 投研消息表
CREATE TABLE IF NOT EXISTS research_messages (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    fulltext_vector tsvector,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES research_sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_research_messages_session_id ON research_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_research_messages_fulltext ON research_messages USING GIN(fulltext_vector);

-- 投研基金关联表
CREATE TABLE IF NOT EXISTS research_funds (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL,
    fund_code VARCHAR(20) NOT NULL,
    fund_name VARCHAR(100),
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES research_sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_research_funds_session_id ON research_funds(session_id);
CREATE INDEX IF NOT EXISTS idx_research_funds_fund_code ON research_funds(fund_code);

-- 投研结果表（结构化分段存储）
CREATE TABLE IF NOT EXISTS research_results (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL,
    analysis_type VARCHAR(50) NOT NULL,
    conclusion TEXT NOT NULL,
    supporting_data JSONB,
    references JSONB,
    fulltext_vector tsvector,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES research_sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_research_results_session_id ON research_results(session_id);
CREATE INDEX IF NOT EXISTS idx_research_results_analysis_type ON research_results(analysis_type);
CREATE INDEX IF NOT EXISTS idx_research_results_fulltext ON research_results USING GIN(fulltext_vector);

-- ============================================
-- Content Tables
-- ============================================

-- 公告内容表（解析后的公告原文）
CREATE TABLE IF NOT EXISTS announcement_contents (
    id SERIAL PRIMARY KEY,
    announcement_id INTEGER NOT NULL UNIQUE,
    title VARCHAR(500),
    content TEXT,
    summary TEXT,
    fulltext_vector tsvector,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_announcement_contents_announcement_id ON announcement_contents(announcement_id);
CREATE INDEX IF NOT EXISTS idx_announcement_contents_fulltext ON announcement_contents USING GIN(fulltext_vector);

-- 社会热点表
CREATE TABLE IF NOT EXISTS social_hotspots (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    source VARCHAR(100),
    url VARCHAR(500),
    heat_score INTEGER DEFAULT 0,
    keywords JSONB,
    fulltext_vector tsvector,
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_social_hotspots_heat_score ON social_hotspots(heat_score DESC);
CREATE INDEX IF NOT EXISTS idx_social_hotspots_published_at ON social_hotspots(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_social_hotspots_fulltext ON social_hotspots USING GIN(fulltext_vector);

-- 公众号/研报文章表
CREATE TABLE IF NOT EXISTS articles (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    content TEXT,
    author VARCHAR(100),
    source VARCHAR(100),
    article_type VARCHAR(50),
    url VARCHAR(500),
    published_at TIMESTAMP,
    fulltext_vector tsvector,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_articles_title ON articles(title);
CREATE INDEX IF NOT EXISTS idx_articles_article_type ON articles(article_type);
CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_fulltext ON articles USING GIN(fulltext_vector);

-- ============================================
-- Queue and Log Tables
-- ============================================

-- 向量待处理队列表
CREATE TABLE IF NOT EXISTS vector_pending (
    id SERIAL PRIMARY KEY,
    content_type VARCHAR(50) NOT NULL,
    content_id VARCHAR(100) NOT NULL,
    original_content TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_vector_pending_status ON vector_pending(status);
CREATE INDEX IF NOT EXISTS idx_vector_pending_content ON vector_pending(content_type, content_id);

-- 爬虫错误日志表
CREATE TABLE IF NOT EXISTS crawl_error_logs (
    id SERIAL PRIMARY KEY,
    crawler_name VARCHAR(100) NOT NULL,
    error_type VARCHAR(50),
    error_message TEXT,
    url VARCHAR(500),
    stack_trace TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_crawl_error_logs_crawler_name ON crawl_error_logs(crawler_name);
CREATE INDEX IF NOT EXISTS idx_crawl_error_logs_error_type ON crawl_error_logs(error_type);
CREATE INDEX IF NOT EXISTS idx_crawl_error_logs_created_at ON crawl_error_logs(created_at DESC);

-- ============================================
-- Initialize Default AI Agents
-- ============================================

INSERT INTO ai_chat_agents (agent_name, agent_desc, system_prompt, model, temperature, max_tokens)
VALUES
    ('老李', 'REITs领域资深专家，擅长政策解读和市场分析', '你是一位REITs领域的资深专家，拥有20年从业经验。你擅长解读政策文件、分析市场趋势，为投资者提供专业的REITs投资建议。', 'deepseek', 0.7, 2000),
    ('小陈', '数据分析助手，擅长处理表格和统计数据', '你是一位数据分析专家，擅长处理各种表格数据、统计分析和可视化。你可以帮助用户理解复杂的财务数据，发现数据中的规律和 insights。', 'deepseek', 0.5, 1500),
    ('王博士', '学术研究员，擅长理论分析和深度研究', '你是一位金融学博士，专注于REITs的学术研究。你可以为用户提供深入的理论分析、学术视角的研究报告和文献综述。', 'gpt-4o-mini', 0.6, 3000)
ON CONFLICT (agent_name) DO NOTHING;
