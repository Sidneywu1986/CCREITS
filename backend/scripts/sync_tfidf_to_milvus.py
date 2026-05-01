#!/usr/bin/env python3
"""
TF-IDF 向量增量同步到 Milvus
基于本地状态文件记录 last_synced_id，避免查询 Milvus（Milvus Lite 查询极慢）
"""

import os
import sys
import logging
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.db import get_conn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sync_tfidf")

COLLECTION = "reit_wechat_articles_tfidf"
BATCH_SIZE = 500
STATE_FILE = os.path.join(os.path.dirname(__file__), ".sync_tfidf_state.json")


def get_milvus_client():
    from vector.milvus_client import MilvusClient
    mc = MilvusClient(uri="./milvus_reits.db", collection=COLLECTION)
    if not mc.connect():
        raise RuntimeError("Failed to connect Milvus")
    return mc._client


def load_state():
    """加载上次同步状态"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
    return {"last_id": 0}


def save_state(state):
    """保存同步状态"""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)


def get_pg_max_id():
    """获取 PG article_vectors 最大 id"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COALESCE(MAX(id), 0) as m FROM business.article_vectors")
        return dict(cur.fetchone())['m']


def fetch_new_chunks(last_id, limit=500):
    """获取 PG 中 id > last_id 的新向量 chunks"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT id, article_id, chunk_index, chunk_text, vector
               FROM business.article_vectors
               WHERE vector IS NOT NULL AND id > %s
               ORDER BY id
               LIMIT %s""",
            (last_id, limit)
        )
        return [dict(row) for row in cur.fetchall()]


def sync():
    logger.info("=" * 60)
    logger.info("TF-IDF Incremental Sync to Milvus")
    logger.info("=" * 60)

    state = load_state()
    last_id = state.get("last_id", 0)
    pg_max = get_pg_max_id()

    logger.info(f"Last synced id: {last_id}, PG max id: {pg_max}")

    if last_id >= pg_max:
        logger.info("Already up to date, nothing to sync")
        return

    client = get_milvus_client()

    # 循环同步新向量
    total_synced = 0
    batch_num = 0
    t0_all = time.time()

    while True:
        batch_num += 1
        chunks = fetch_new_chunks(last_id, limit=BATCH_SIZE)
        if not chunks:
            logger.info("No new chunks to sync")
            break

        logger.info(f"[Batch {batch_num}] {len(chunks)} new chunks (id > {last_id})")

        rows = []
        for c in chunks:
            rows.append({
                "id": c["id"],
                "article_id": c["article_id"],
                "chunk_index": c["chunk_index"],
                "chunk_text": c["chunk_text"][:4000],
                "embedding": json.loads(c["vector"]),
            })
            last_id = c["id"]

        t0 = time.time()
        client.insert(collection_name=COLLECTION, data=rows)
        elapsed = time.time() - t0

        total_synced += len(chunks)
        logger.info(f"  Inserted in {elapsed:.2f}s | Cumulative: {total_synced}")

        # 每批保存状态（断点续传）
        save_state({"last_id": last_id})

    total_time = time.time() - t0_all
    logger.info("=" * 60)
    logger.info(f"Sync complete: {total_synced} chunks in {total_time:.1f}s")
    save_state({"last_id": last_id})


if __name__ == "__main__":
    sync()
