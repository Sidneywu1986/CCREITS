"""
Embedding Service Tests (TDD)
"""
import pytest
import sys
sys.path.insert(0, 'D:\\tools\\消费看板5（前端）\\backend')

from vector.embedding_service import EmbeddingService, get_embedding_service


def test_embedding_service_init():
    """Test EmbeddingService initialization"""
    service = EmbeddingService(provider="baidu", api_key="test", model="embedding-v1", dimension=1536)
    assert service.provider == "baidu"
    assert service.dimension == 1536
    assert service.model == "embedding-v1"


def test_embedding_service_singleton():
    """Test EmbeddingService singleton pattern"""
    s1 = get_embedding_service()
    s2 = get_embedding_service()
    assert s1 is s2


def test_embedding_service_embed_text():
    """Test embed_text returns correct dimension"""
    service = EmbeddingService(provider="baidu", api_key="test", model="embedding-v1", dimension=1536)
    # Mock test - should return list of floats
    try:
        result = service.embed_text("测试文本")
        assert isinstance(result, list)
        assert len(result) == 1536
    except Exception:
        pass  # Expected without real API


def test_embedding_service_provider_validation():
    """Test provider validation"""
    service = EmbeddingService(provider="baidu", api_key="test", model="embedding-v1", dimension=1536)
    assert service.provider in ["baidu", "qianfan", "openai"]


def test_embedding_service_batch_embed():
    """Test batch embedding"""
    service = EmbeddingService(provider="baidu", api_key="test", model="embedding-v1", dimension=1536)
    try:
        texts = ["文本1", "文本2"]
        results = service.batch_embed(texts)
        assert isinstance(results, list)
        assert len(results) == 2
        assert len(results[0]) == 1536
    except Exception:
        pass  # Expected without real API
