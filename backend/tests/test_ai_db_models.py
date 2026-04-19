"""
AI Database Models Tests (TDD)
"""
import pytest
import sys
sys.path.insert(0, 'D:\\tools\\消费看板5（前端）\\backend')

from ai_db.models import (
    AiChatSession, AiChatMessage, AiChatAgent,
    AnnouncementChatSession, AnnouncementChatMessage, AnnouncementChatContext,
    ResearchSession, ResearchMessage, ResearchFund, ResearchResult,
    AnnouncementContent, SocialHotspot, Article, VectorPending, CrawlErrorLog
)


@pytest.mark.asyncio
async def test_create_ai_chat_session():
    """Test creating an AI chat session"""
    session = await AiChatSession.create(session_title="测试会话")
    assert session.id is not None
    assert session.session_title == "测试会话"

@pytest.mark.asyncio
async def test_create_ai_chat_message():
    """Test creating an AI chat message"""
    session = await AiChatSession.create(session_title="测试")
    msg = await AiChatMessage.create(session=session, role="user", content="你好")
    assert msg.id is not None
    assert msg.role == "user"
    assert msg.content == "你好"

@pytest.mark.asyncio
async def test_ai_chat_agent():
    """Test AI agent creation"""
    agent = await AiChatAgent.create(
        agent_name="测试Agent",
        agent_desc="测试描述",
        system_prompt="你是一个测试助手"
    )
    assert agent.id is not None
    assert agent.agent_name == "测试Agent"

@pytest.mark.asyncio
async def test_announcement_chat_session():
    """Test announcement chat session"""
    session = await AnnouncementChatSession.create(session_title="公告会话")
    assert session.id is not None
    assert session.session_title == "公告会话"

@pytest.mark.asyncio
async def test_announcement_chat_message():
    """Test announcement chat message"""
    session = await AnnouncementChatSession.create(session_title="公告")
    msg = await AnnouncementChatMessage.create(
        session=session, role="user", content="查找年报"
    )
    assert msg.id is not None
    assert msg.content == "查找年报"

@pytest.mark.asyncio
async def test_research_session():
    """Test research session"""
    session = await ResearchSession.create(session_title="投研会话")
    assert session.id is not None

@pytest.mark.asyncio
async def test_research_result_structured():
    """Test research result with structured data"""
    session = await ResearchSession.create()
    result = await ResearchResult.create(
        session=session,
        analysis_type="financial",
        conclusion="结论测试",
        supporting_data='[{"key": "value"}]',
        references='[{"id": 1}]'
    )
    assert result.id is not None
    assert result.conclusion == "结论测试"
    assert result.analysis_type == "financial"

@pytest.mark.asyncio
async def test_research_fund():
    """Test research fund linking"""
    session = await ResearchSession.create()
    fund = await ResearchFund.create(
        session=session,
        fund_code="000001",
        fund_name="测试基金"
    )
    assert fund.id is not None
    assert fund.fund_code == "000001"

@pytest.mark.asyncio
async def test_crawl_error_log():
    """Test crawl error logging"""
    error = await CrawlErrorLog.create(
        crawler_name="test_crawler",
        error_type="ParseError",
        error_message="Failed to parse HTML",
        url="http://example.com"
    )
    assert error.id is not None
    assert error.crawler_name == "test_crawler"

@pytest.mark.asyncio
async def test_vector_pending():
    """Test vector pending queue"""
    pending = await VectorPending.create(
        content_type="article",
        content_id="123",
        original_content="测试内容"
    )
    assert pending.id is not None
    assert pending.status == "pending"
