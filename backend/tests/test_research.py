"""
Tests for Research API
"""
import pytest
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.research import router, ResearchRequest, ResearchResponse


def test_research_request_model():
    """Test ResearchRequest default values"""
    req = ResearchRequest(message="研究REITs")
    assert req.message == "研究REITs"
    assert req.agent_name == "投研小助手"  # default


def test_research_request_with_session():
    """Test ResearchRequest with session and custom agent"""
    req = ResearchRequest(session_id=1, message="测试", agent_name="小陈")
    assert req.session_id == 1
    assert req.agent_name == "小陈"


def test_research_request_no_session():
    """Test ResearchRequest without session_id"""
    req = ResearchRequest(message="你好")
    assert req.session_id is None
    assert req.message == "你好"


def test_research_response_model():
    """Test ResearchResponse structure"""
    resp = ResearchResponse(
        session_id=1,
        result_id=100,
        message_id=100,
        role="assistant",
        content="这是投研回复",
        agent_name="投研小助手",
        analysis={"type": "summary", "data": {}}
    )
    assert resp.session_id == 1
    assert resp.result_id == 100
    assert resp.analysis["type"] == "summary"
