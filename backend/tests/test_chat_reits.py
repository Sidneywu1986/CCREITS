"""
Tests for ChatReits API
"""
import pytest
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.chat_reits import router, ChatReitsRequest, ChatReitsResponse


def test_chat_reits_request_model():
    """Test ChatReitsRequest default values"""
    req = ChatReitsRequest(message="测试消息")
    assert req.message == "测试消息"
    assert req.agent_name == "老李"  # default


def test_chat_reits_request_with_session():
    """Test ChatReitsRequest with session and custom agent"""
    req = ChatReitsRequest(session_id=1, message="测试", agent_name="小陈")
    assert req.session_id == 1
    assert req.agent_name == "小陈"


def test_chat_reits_request_no_session():
    """Test ChatReitsRequest without session_id"""
    req = ChatReitsRequest(message="你好")
    assert req.session_id is None
    assert req.message == "你好"


def test_chat_reits_response_model():
    """Test ChatReitsResponse structure"""
    resp = ChatReitsResponse(
        session_id=1,
        message_id=100,
        role="assistant",
        content="这是AI回复",
        agent_name="老李",
        sources=[{"id": 1, "content": "来源1"}]
    )
    assert resp.session_id == 1
    assert resp.message_id == 100
    assert resp.role == "assistant"
    assert resp.content == "这是AI回复"
    assert resp.agent_name == "老李"
    assert len(resp.sources) == 1
