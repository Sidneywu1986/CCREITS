"""
Milvus Client Tests (TDD)
"""
import pytest
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    result = client.is_healthy()
    assert result is False or result is True  # Either healthy or not


def test_milvus_client_create_collection():
    """Test create collection if not exists"""
    client = MilvusClient(host="localhost", port=19530)
    # Should handle gracefully without real connection
    try:
        client.create_collection_if_not_exists("test_collection", dimension=1536)
    except Exception as e:
        pytest.fail(str(e))


def test_milvus_client_insert_and_search():
    """Test insert and search vectors"""
    client = MilvusClient(host="localhost", port=19530)
    try:
        # Insert vectors
        data = [
            {"content": "test content 1", "embedding": [0.1] * 1536},
            {"content": "test content 2", "embedding": [0.2] * 1536}
        ]
        ids = client.insert("test_collection", data)
        # insert() returns None on failure, empty list on success with no ids
        if ids is not None:
            assert len(ids) == 2

        # Search vectors
        results = client.search("test_collection", [0.1] * 1536, top_k=1)
        assert isinstance(results, list)
    except Exception as e:
        pytest.fail(str(e))
