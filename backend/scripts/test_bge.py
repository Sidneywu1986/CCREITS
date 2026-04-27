#!/usr/bin/env python3
"""
BGE-M3 编码测试 — Day 1
从 SQLite 取 10 篇文章，测试编码速度和向量质量
"""

import os
import sys
import time
import logging
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_bge")

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "reits.db")


def fetch_sample_articles(limit: int = 10) -> list:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        "SELECT id, title, content FROM wechat_articles WHERE content IS NOT NULL AND length(content) > 100 ORDER BY id LIMIT ?",
        (limit,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def main():
    logger.info("=" * 60)
    logger.info("Day 1: BGE-M3 embedder test")
    logger.info("=" * 60)

    articles = fetch_sample_articles(limit=10)
    logger.info(f"Fetched {len(articles)} articles from SQLite")

    # 构造 chunks（复用现有切分逻辑）
    from scripts.vectorize_articles import split_text

    all_chunks = []
    chunk_meta = []
    for art in articles:
        chunks = split_text(art["content"], chunk_size=512, overlap=64)
        for idx, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            chunk_meta.append({"article_id": art["id"], "title": art["title"], "chunk_index": idx})

    logger.info(f"Total chunks: {len(all_chunks)} from {len(articles)} articles")

    # 加载 embedder
    from rag.bge_embedder import get_embedder

    t0 = time.time()
    embedder = get_embedder()
    load_time = time.time() - t0
    logger.info(f"Embedder loaded in {load_time:.1f}s")

    # 编码 chunks
    t0 = time.time()
    vectors = embedder.encode(all_chunks, batch_size=4, show_progress=True)
    encode_time = time.time() - t0
    logger.info(f"Encoded {len(all_chunks)} chunks in {encode_time:.1f}s")
    logger.info(f"Vector shape: {vectors.shape}, dtype: {vectors.dtype}")

    # 验证
    import numpy as np

    norms = np.linalg.norm(vectors, axis=1)
    logger.info(f"Norm stats: min={norms.min():.4f} max={norms.max():.4f} mean={norms.mean():.4f}")

    # 语义相似度测试
    queries = [
        "数据中心REITs前景",
        "产业园出租率",
        "高速公路分红",
    ]
    for q in queries:
        qvec = embedder.encode_query(q)
        sims = np.dot(vectors, qvec)
        top3 = np.argsort(sims)[-3:][::-1]
        top3_sims = [f"{sims[i]:.3f}" for i in top3]
        logger.info(f"Query '{q}': top3 sims={top3_sims}")
        for i in top3:
            meta = chunk_meta[i]
            logger.info(f"  -> [{meta['article_id']}-{meta['chunk_index']}] {meta['title'][:30]}...")

    logger.info("Day 1 test complete!")


if __name__ == "__main__":
    main()
