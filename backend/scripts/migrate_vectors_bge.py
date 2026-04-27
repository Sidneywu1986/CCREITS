#!/usr/bin/env python3
"""
向量库迁移：TF-IDF+SVD(256d) → BGE-M3(1024d)
全量重建 Milvus collection，保留旧 collection 作为 fallback
"""

import os
import sys
import logging
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.db import get_conn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("migrate_bge")

BATCH_SIZE = 32  # BGE-M3 batch size
CHUNK_SIZE = 512
OVERLAP = 64

# Milvus 新 collection 名称
NEW_COLLECTION = "reit_wechat_articles_bge"
OLD_COLLECTION = "reit_wechat_articles"


def fetch_all_articles():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, source, title, link, published, content 
            FROM business.wechat_articles 
            WHERE content IS NOT NULL AND LENGTH(content) > 50 
            ORDER BY id
            """
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def split_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list:
    """复用现有切分逻辑"""
    from scripts.vectorize_articles import split_text as _split

    return _split(text, chunk_size=chunk_size, overlap=overlap)


def create_new_collection(client, dim: int = 1024):
    from pymilvus import DataType

    if NEW_COLLECTION in client.list_collections():
        logger.info(f"Collection {NEW_COLLECTION} exists, dropping...")
        client.drop_collection(NEW_COLLECTION)

    schema = client.create_schema(auto_id=False, description="REITs wechat articles BGE-M3 vectors")
    schema.add_field("id", DataType.INT64, is_primary=True)
    schema.add_field("article_id", DataType.INT64)
    schema.add_field("chunk_index", DataType.INT64)
    schema.add_field("chunk_text", DataType.VARCHAR, max_length=4000)
    schema.add_field("source", DataType.VARCHAR, max_length=200)
    schema.add_field("title", DataType.VARCHAR, max_length=500)
    schema.add_field("publish_date", DataType.VARCHAR, max_length=20)
    schema.add_field("embedding", DataType.FLOAT_VECTOR, dim=dim)

    client.create_collection(collection_name=NEW_COLLECTION, schema=schema)

    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="embedding",
        index_type="IVF_FLAT",
        metric_type="COSINE",
        params={"nlist": 128},
    )
    client.create_index(collection_name=NEW_COLLECTION, index_params=index_params)
    logger.info(f"Created collection {NEW_COLLECTION} with dim={dim}")


def migrate():
    logger.info("=" * 60)
    logger.info("Day 3: Migrate vectors to BGE-M3 (1024d)")
    logger.info("=" * 60)

    # 1. 连接 Milvus
    from vector.milvus_client import MilvusClient

    mc = MilvusClient(uri="./milvus_reits.db", collection=OLD_COLLECTION)
    if not mc.connect():
        logger.error("Failed to connect Milvus")
        return

    client = mc._client
    create_new_collection(client, dim=1024)

    # 2. 加载 embedder
    from rag.bge_embedder import get_embedder

    embedder = get_embedder()

    # 3. 读取所有文章
    articles = fetch_all_articles()
    logger.info(f"Total articles: {len(articles)}")

    # 4. 分批处理
    total_chunks = 0
    t0_all = time.time()

    for i in range(0, len(articles), BATCH_SIZE):
        batch = articles[i : i + BATCH_SIZE]

        # 切分 + 收集
        all_chunks = []
        all_meta = []
        for art in batch:
            chunks = split_text(art["content"])
            for idx, chunk in enumerate(chunks):
                all_chunks.append(chunk)
                all_meta.append(
                    {
                        "article_id": art["id"],
                        "chunk_index": idx,
                        "chunk_text": chunk[:4000],
                        "source": art.get("source", "")[:200],
                        "title": art.get("title", "")[:500],
                        "publish_date": art.get("published", "")[:20] if art.get("published") else "",
                    }
                )

        if not all_chunks:
            continue

        # 编码
        t0 = time.time()
        vectors = embedder.encode(all_chunks, batch_size=8)
        elapsed = time.time() - t0
        logger.info(f"Batch {i}/{len(articles)}: {len(all_chunks)} chunks in {elapsed:.1f}s")

        # 构造 Milvus 数据
        ids = list(range(total_chunks, total_chunks + len(all_chunks)))
        total_chunks += len(all_chunks)

        data = {
            "id": ids,
            "article_id": [m["article_id"] for m in all_meta],
            "chunk_index": [m["chunk_index"] for m in all_meta],
            "chunk_text": [m["chunk_text"] for m in all_meta],
            "source": [m["source"] for m in all_meta],
            "title": [m["title"] for m in all_meta],
            "publish_date": [m["publish_date"] for m in all_meta],
            "embedding": vectors.tolist(),
        }

        client.insert(collection_name=NEW_COLLECTION, data=data)

    total_time = time.time() - t0_all
    logger.info(f"Migration complete: {total_chunks} chunks in {total_time:.1f}s")

    # 5. 验证
    stats = client.get_collection_stats(NEW_COLLECTION)
    logger.info(f"New collection stats: {stats}")

    # 6. 测试搜索
    qvec = embedder.encode_query("数据中心REITs前景")
    results = client.search(
        collection_name=NEW_COLLECTION,
        data=[qvec.tolist()],
        limit=5,
        output_fields=["title", "source", "chunk_text"],
    )
    for r in results[0]:
        logger.info(f"  [{r['entity']['source']}] dist={r['distance']:.3f} | {r['entity']['title'][:40]}")


if __name__ == "__main__":
    migrate()
