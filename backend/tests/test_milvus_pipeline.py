#!/usr/bin/env python3
"""
Test Milvus + BGE-M3 pipeline end-to-end.
Uses mock vectors when BGE-M3 model is not yet downloaded.
"""
import os
import sys
import tempfile
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vector.milvus_client import MilvusClient


def test_milvus_crud():
    """Test basic Milvus insert/search/delete with random vectors."""
    db_path = os.path.join(tempfile.gettempdir(), "test_milvus_pipeline.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    client = MilvusClient(uri=db_path, collection="test_pipeline")
    assert client.connect(), "Failed to connect Milvus"

    # Create collection
    client.ensure_collection(dim=1024)

    # Insert mock data
    mock_vectors = [
        {
            "article_id": 1,
            "source": "wechat",
            "title": "数据中心REITs前景分析",
            "publish_date": "2024-01-01",
            "chunk_index": 0,
            "chunk_text": "数据中心REITs在2024年表现强劲...",
            "embedding": np.random.randn(1024).astype(np.float32).tolist(),
        },
        {
            "article_id": 2,
            "source": "wechat",
            "title": "高速公路REITs分红方案",
            "publish_date": "2024-02-01",
            "chunk_index": 0,
            "chunk_text": "高速公路REITs宣布提高分红比例...",
            "embedding": np.random.randn(1024).astype(np.float32).tolist(),
        },
    ]

    ok = client.insert(mock_vectors)
    assert ok, "Insert failed"
    print("✅ Insert OK")

    # Search
    query_vec = np.random.randn(1024).astype(np.float32).tolist()
    results = client.search(vector=query_vec, top_k=2)
    assert len(results) == 2, f"Expected 2 results, got {len(results)}"
    print(f"✅ Search OK: got {len(results)} results")

    # Delete
    ok = client.delete_by_article_ids([1])
    assert ok, "Delete failed"
    print("✅ Delete OK")

    # Verify delete
    results_after = client.search(vector=query_vec, top_k=2)
    # Should still return results but article_id=1 should be gone
    remaining_ids = {r["article_id"] for r in results_after}
    assert 1 not in remaining_ids, "Delete did not work"
    print("✅ Delete verification OK")

    client.disconnect()
    if os.path.exists(db_path):
        os.remove(db_path)
    print("\n🎉 All Milvus CRUD tests passed!")


def test_search_api_import():
    """Test that search API can be imported without errors."""
    from api.search import search_articles_for_rag, _search_milvus
    print("✅ search API imports OK")


def test_bge_embedder_import():
    """Test that BGE embedder can be imported."""
    from rag.bge_embedder import BGEEmbedder, get_embedder
    print("✅ BGE embedder imports OK")


if __name__ == "__main__":
    test_milvus_crud()
    test_search_api_import()
    test_bge_embedder_import()
