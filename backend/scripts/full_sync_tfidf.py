#!/usr/bin/env python3
"""TF-IDF 全量同步到 Milvus — 一次性完成，避免多次连接"""
import os
import sys
import json
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.db import get_conn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("full_sync")

COLLECTION = "reit_wechat_articles_tfidf"

def main():
    logger.info("Loading all vectors from PG...")
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, article_id, chunk_index, chunk_text, vector
            FROM business.article_vectors
            WHERE vector IS NOT NULL
            ORDER BY id
        """)
        rows = [dict(row) for row in cur.fetchall()]
    logger.info(f"Loaded {len(rows)} vectors from PG")

    if not rows:
        logger.info("No vectors to sync")
        return

    logger.info("Connecting to Milvus...")
    from vector.milvus_client import MilvusClient
    mc = MilvusClient(uri="./milvus_reits.db", collection=COLLECTION)
    if not mc.connect():
        raise RuntimeError("Failed to connect Milvus")
    client = mc._client

    logger.info("Preparing data...")
    data = []
    for r in rows:
        data.append({
            "id": r["id"],
            "article_id": r["article_id"],
            "chunk_index": r["chunk_index"],
            "chunk_text": r["chunk_text"][:4000],
            "embedding": json.loads(r["vector"]),
        })

    logger.info(f"Inserting {len(data)} rows into Milvus...")
    client.insert(collection_name=COLLECTION, data=data)
    logger.info(f"Done! Inserted {len(data)} chunks")

if __name__ == "__main__":
    main()
