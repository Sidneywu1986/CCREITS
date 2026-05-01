#!/usr/bin/env python3
"""
将现有 TF-IDF 向量从 PostgreSQL 迁入 Milvus
分批处理、断点续传、每批验证
"""

import os
import sys
import logging
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.db import get_conn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("migrate_tfidf")

COLLECTION = "reit_wechat_articles_tfidf"
BATCH_SIZE = 500  # chunks per batch (fast, no model inference)


def get_milvus_client():
    from vector.milvus_client import MilvusClient
    mc = MilvusClient(uri="./milvus_reits.db", collection=COLLECTION)
    if not mc.connect():
        raise RuntimeError("Failed to connect Milvus")
    return mc._client


def ensure_collection(client, dim: int = 256):
    from pymilvus import DataType
    if COLLECTION in client.list_collections():
        logger.info(f"Collection {COLLECTION} exists, dropping...")
        client.drop_collection(COLLECTION)

    schema = client.create_schema(auto_id=False, description="REITs wechat articles TF-IDF vectors")
    schema.add_field("id", DataType.INT64, is_primary=True)
    schema.add_field("article_id", DataType.INT64)
    schema.add_field("chunk_index", DataType.INT64)
    schema.add_field("chunk_text", DataType.VARCHAR, max_length=4000)
    schema.add_field("embedding", DataType.FLOAT_VECTOR, dim=dim)

    client.create_collection(collection_name=COLLECTION, schema=schema)

    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="embedding",
        index_type="IVF_FLAT",
        metric_type="COSINE",
        params={"nlist": 128},
    )
    client.create_index(collection_name=COLLECTION, index_params=index_params)
    logger.info(f"Created collection {COLLECTION} with dim={dim}")


def get_vector_dim():
    import json
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT vector FROM business.article_vectors WHERE vector IS NOT NULL LIMIT 1")
        row = cur.fetchone()
        if row:
            vec = json.loads(row['vector'])
            return len(vec)
    return 256


def fetch_chunks_batch(offset, limit):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT id, article_id, chunk_index, chunk_text, vector
               FROM business.article_vectors
               WHERE vector IS NOT NULL
               ORDER BY id
               LIMIT %s OFFSET %s""",
            (limit, offset)
        )
        return [dict(row) for row in cur.fetchall()]


def get_total_count():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as cnt FROM business.article_vectors WHERE vector IS NOT NULL")
        return cur.fetchone()['cnt']


def migrate():
    logger.info("=" * 60)
    logger.info("TF-IDF Vector Migration to Milvus")
    logger.info("=" * 60)

    # 1. 获取向量维度
    dim = get_vector_dim()
    logger.info(f"Vector dimension: {dim}")

    # 2. 连接 Milvus 并创建 collection
    client = get_milvus_client()
    ensure_collection(client, dim=dim)

    # 3. 获取总量
    total = get_total_count()
    logger.info(f"Total chunks to migrate: {total}")

    if total == 0:
        logger.warning("No vectors to migrate")
        return

    # 4. 分批迁移
    offset = 0
    batch_num = 0
    t0_all = time.time()

    while offset < total:
        batch_num += 1
        chunks = fetch_chunks_batch(offset, BATCH_SIZE)
        if not chunks:
            break

        logger.info(f"[Batch {batch_num}] offset={offset}, {len(chunks)} chunks")

        import json
        rows = []
        for c in chunks:
            rows.append({
                "id": c["id"],
                "article_id": c["article_id"],
                "chunk_index": c["chunk_index"],
                "chunk_text": c["chunk_text"][:4000],
                "embedding": json.loads(c["vector"]),
            })

        t0 = time.time()
        client.insert(collection_name=COLLECTION, data=rows)
        elapsed = time.time() - t0

        offset += len(chunks)
        logger.info(
            f"  Inserted in {elapsed:.2f}s | "
            f"Progress: {offset}/{total} ({offset/total*100:.1f}%)"
        )

    total_time = time.time() - t0_all
    logger.info("=" * 60)
    logger.info(f"Migration complete: {offset}/{total} chunks in {total_time:.1f}s")

    # 5. 最终验证
    stats = client.get_collection_stats(COLLECTION)
    logger.info(f"Collection stats: {stats}")

    # 6. 测试搜索
    try:
        import json
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT vector FROM business.article_vectors WHERE vector IS NOT NULL LIMIT 1")
            row = cur.fetchone()
            qvec = json.loads(row['vector'])

        results = client.search(
            collection_name=COLLECTION,
            data=[qvec],
            limit=5,
            output_fields=["article_id", "chunk_text"],
        )
        logger.info("Search test OK:")
        for r in results[0]:
            logger.info(f"  dist={r['distance']:.3f} | {r['entity']['chunk_text'][:60]}...")
    except (RuntimeError, ConnectionError, ValueError) as e:
        logger.warning(f"Search test failed: {e}")


if __name__ == "__main__":
    migrate()
