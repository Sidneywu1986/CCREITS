"""
Tests for ChatAnnouncement API
"""
import pytest
import sys
sys.path.insert(0, 'D:\\tools\\消费看板5（前端）\\backend')

from api.chat_announcement import router, ChatAnnouncementRequest, ChatAnnouncementResponse


def test_chat_announcement_request_model():
    """Test ChatAnnouncementRequest default values"""
    req = ChatAnnouncementRequest(message="查询公告")
    assert req.message == "查询公告"
    assert req.agent_name == "小智"  # default


def test_chat_announcement_request_with_session():
    """Test ChatAnnouncementRequest with session and custom agent"""
    req = ChatAnnouncementRequest(session_id=1, message="测试", agent_name="小陈")
    assert req.session_id == 1
    assert req.agent_name == "小陈"


def test_chat_announcement_request_no_session():
    """Test ChatAnnouncementRequest without session_id"""
    req = ChatAnnouncementRequest(message="你好")
    assert req.session_id is None
    assert req.message == "你好"


def test_chat_announcement_response_model():
    """Test ChatAnnouncementResponse structure"""
    resp = ChatAnnouncementResponse(
        session_id=1,
        message_id=100,
        role="assistant",
        content="这是AI回复",
        agent_name="小智",
        sources=[{"id": 1, "content": "公告内容"}]
    )
    assert resp.session_id == 1
    assert resp.message_id == 100
    assert resp.role == "assistant"
    assert resp.content == "这是AI回复"
    assert resp.agent_name == "小智"
    assert len(resp.sources) == 1
