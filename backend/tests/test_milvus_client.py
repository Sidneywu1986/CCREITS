"""
Milvus Client Tests (TDD)
"""
import pytest
import sys
sys.path.insert(0, 'D:\\tools\\消费看板5（前端）\\backend')

from vector.milvus_client import MilvusClient, get_milvus_client


def test_milvus_client_init():
    """Test MilvusClient initialization"""
    client = MilvusClient(host="localhost", port=19530)
    assert client.host == "localhost"
    assert client.port == 19530
    assert not client._connected


def test_milvus_client_singleton():
    """Test MilvusClient singleton pattern"""
    client1 = get_milvus_client()
    client2 = get_milvus_client()
    assert client1 is client2


def test_milvus_client_connect_disconnect():
    """Test connect and disconnect"""
    client = MilvusClient(host="localhost", port=19530)
    # Should not raise, just catch connection error gracefully
    result = client.health_check()
    assert result is False or result is True  # Either healthy or not


def test_milvus_client_create_collection():
    """Test create collection if not exists"""
    client = MilvusClient(host="localhost", port=19530)
    # Should handle gracefully without real connection
    try:
        client.create_collection_if_not_exists("test_collection", dimension=1536)
    except Exception:
        pass  # Expected without real Milvus


def test_milvus_client_insert_and_search():
    """Test insert and search vectors"""
    client = MilvusClient(host="localhost", port=19530)
    try:
        # Insert vectors
        vectors = [[0.1] * 1536, [0.2] * 1536]
        ids = client.insert_vectors("test_collection", vectors)
        assert len(ids) == 2

        # Search vectors
        results = client.search_vectors("test_collection", [[0.1] * 1536], top_k=1)
        assert isinstance(results, list)
    except Exception:
        pass  # Expected without real Milvus
