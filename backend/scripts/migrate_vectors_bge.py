#!/usr/bin/env python3
"""
向量入库：BGE-M3(1024d) → Milvus
支持分批处理、断点续传、每批验证
"""

import os
import sys
import logging
import time

# Allow MPS to use more memory (MacBook Pro 16GB RAM)
os.environ["PYTORCH_MPS_HIGH_WATERMARK_RATIO"] = "0.0"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.db import get_conn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("migrate_bge")

CHUNK_SIZE = 1024
OVERLAP = 128
NEW_COLLECTION = "reit_wechat_articles_bge"
OLD_COLLECTION = "reit_wechat_articles"


def get_milvus_client():
    from vector.milvus_client import MilvusClient
    mc = MilvusClient(uri="./milvus_reits.db", collection=OLD_COLLECTION)
    if not mc.connect():
        raise RuntimeError("Failed to connect Milvus")
    return mc._client


def ensure_collection(client, dim: int = 1024):
    from pymilvus import DataType
    if NEW_COLLECTION in client.list_collections():
        logger.info(f"Collection {NEW_COLLECTION} already exists")
        return

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


def get_existing_article_ids_from_milvus(client):
    """从Milvus获取已处理的article_id（不依赖PG vectorized字段）"""
    try:
        # Milvus query limit max 16384, use pagination if needed
        all_ids = set()
        offset = 0
        batch = 16000
        while True:
            results = client.query(
                collection_name=NEW_COLLECTION,
                filter="",
                output_fields=["article_id"],
                limit=batch,
                offset=offset,
            )
            if not results:
                break
            for r in results:
                all_ids.add(r["article_id"])
            if len(results) < batch:
                break
            offset += batch
        logger.info(f"Existing in Milvus BGE: {len(all_ids)} articles")
        return all_ids
    except (RuntimeError, ConnectionError, ValueError) as e:
        logger.warning(f"Query Milvus existing failed: {e}")
        return set()


def mark_vectorized(article_ids):
    """标记文章为已向量化（可选，保留用于兼容）"""
    # BGE迁移不再依赖PG的vectorized字段，状态直接从Milvus查询
    pass


def fetch_articles_batch(existing_ids, limit=20):
    """取未处理的文章，过滤超长内容（>100KB 视为脏数据）"""
    with get_conn() as conn:
        cur = conn.cursor()
        if existing_ids:
            placeholders = ",".join(["%s"] * len(existing_ids))
            cur.execute(
                f"""SELECT id, source, title, link, published, content
                    FROM business.wechat_articles
                    WHERE content IS NOT NULL AND LENGTH(content) > 50
                      AND LENGTH(content) < 100000
                      AND id NOT IN ({placeholders})
                    ORDER BY id
                    LIMIT %s""",
                tuple(existing_ids) + (limit,)
            )
        else:
            cur.execute(
                """SELECT id, source, title, link, published, content
                   FROM business.wechat_articles
                   WHERE content IS NOT NULL AND LENGTH(content) > 50
                     AND LENGTH(content) < 100000
                   ORDER BY id
                   LIMIT %s""",
                (limit,)
            )
        return [dict(row) for row in cur.fetchall()]


def split_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list:
    from scripts.vectorize_articles import split_text as _split
    return _split(text, chunk_size=chunk_size, overlap=overlap)


def encode_batch(embedder, articles):
    """纯编码，不碰Milvus连接"""
    all_chunks = []
    all_meta = []

    for art in articles:
        chunks = split_text(art["content"])
        logger.info(f"    Article {art['id']}: {len(chunks)} chunks")
        for idx, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_meta.append({
                "article_id": art["id"],
                "chunk_index": idx,
                "chunk_text": chunk[:4000],
                "source": art.get("source", "")[:200],
                "title": art.get("title", "")[:500],
                "publish_date": str(art.get("published", ""))[:20] if art.get("published") else "",
            })

    if not all_chunks:
        return [], []

    logger.info(f"  Total chunks to encode: {len(all_chunks)}")
    t0 = time.time()
    vectors = embedder.encode(all_chunks, batch_size=16)
    encode_time = time.time() - t0
    logger.info(f"  Encoded {len(all_chunks)} chunks in {encode_time:.1f}s")
    return vectors, all_meta


def write_to_milvus(client, vectors, meta_list, global_chunk_id_start):
    """写入Milvus（行格式，兼容 pymilvus 2.6+）"""
    rows = []
    vec_list = vectors.tolist() if hasattr(vectors, 'tolist') else vectors
    for i, m in enumerate(meta_list):
        rows.append({
            "id": global_chunk_id_start + i,
            "article_id": m["article_id"],
            "chunk_index": m["chunk_index"],
            "chunk_text": m["chunk_text"],
            "source": m["source"],
            "title": m["title"],
            "publish_date": m["publish_date"],
            "embedding": vec_list[i],
        })

    client.insert(collection_name=NEW_COLLECTION, data=rows)
    return global_chunk_id_start + len(meta_list)


def verify_batch(client, article_ids):
    """验证这批article_id是否在Milvus中"""
    try:
        for aid in article_ids:
            resp = client.query(
                collection_name=NEW_COLLECTION,
                filter=f"article_id == {aid}",
                output_fields=["article_id"],
                limit=1
            )
            if not resp:
                logger.error(f"  VERIFY FAIL: article_id={aid} not found!")
                return False
        logger.info(f"  VERIFY OK: all {len(article_ids)} articles confirmed")
        return True
    except (RuntimeError, ConnectionError, ValueError) as e:
        logger.error(f"  VERIFY ERROR: {e}")
        return False


def test_search(client, embedder):
    try:
        qvec = embedder.encode_query("数据中心REITs前景")
        results = client.search(
            collection_name=NEW_COLLECTION,
            data=[qvec.tolist()],
            limit=5,
            output_fields=["title", "source", "chunk_text"],
        )
        logger.info("Search test:")
        for r in results[0]:
            logger.info(
                f"  [{r['entity']['source']}] dist={r['distance']:.3f} | "
                f"{r['entity']['title'][:40]}"
            )
    except (RuntimeError, ConnectionError, ValueError) as e:
        logger.warning(f"Search test failed: {e}")


def migrate(batch_size: int = 50):
    logger.info("=" * 60)
    logger.info("BGE-M3 Vector Migration (MPS GPU accelerated)")
    logger.info("=" * 60)

    # 1. 加载 embedder（最耗时，先加载）
    from rag.bge_embedder import get_embedder
    import torch
    embedder = get_embedder()
    logger.info(f"BGE-M3 loaded on {embedder.device}")
    
    # Clear MPS cache after model load to free VRAM for encoding
    if embedder.device == "mps" and hasattr(torch.mps, 'empty_cache'):
        torch.mps.empty_cache()
        logger.info("MPS cache cleared after model load")

    # 2. 连接Milvus并查已处理
    client = get_milvus_client()
    ensure_collection(client)
    existing_ids = get_existing_article_ids_from_milvus(client)

    # 3. 循环分批处理
    global_chunk_id = 0
    total_articles = 0
    total_chunks = 0
    batch_num = 0
    t0_all = time.time()

    while True:
        batch_num += 1
        articles = fetch_articles_batch(existing_ids, limit=batch_size)
        if not articles:
            logger.info("No more articles to process")
            break

        logger.info(
            f"[Batch {batch_num}] {len(articles)} articles "
            f"(ids: {articles[0]['id']}~{articles[-1]['id']})"
        )

        # 3a. 编码（长时间操作，不保持Milvus连接）
        vectors, meta_list = encode_batch(embedder, articles)
        if not meta_list:
            logger.warning("  No chunks generated, skipping")
            for a in articles:
                existing_ids.add(a["id"])
            continue

        # 3b. 连接Milvus并写入（短操作）
        client = get_milvus_client()
        ensure_collection(client)
        global_chunk_id = write_to_milvus(client, vectors, meta_list, global_chunk_id)

        total_articles += len(articles)
        total_chunks += len(meta_list)

        # 3c. 验证
        ok = verify_batch(client, [a["id"] for a in articles])

        # 3d. 标记为已处理（添加到内存集合）
        for a in articles:
            existing_ids.add(a["id"])

        logger.info(
            f"  Cumulative: {total_articles} articles, {total_chunks} chunks, "
            f"{(time.time()-t0_all)/60:.1f}min, "
            f"speed={total_articles/((time.time()-t0_all)/60):.1f} articles/min"
        )

    total_time = time.time() - t0_all
    logger.info("=" * 60)
    logger.info(
        f"Done: {total_articles} articles, {total_chunks} chunks "
        f"in {total_time/60:.1f}min"
    )

    # 最终验证
    client = get_milvus_client()
    try:
        stats = client.get_collection_stats(NEW_COLLECTION)
        logger.info(f"Collection stats: {stats}")
    except (RuntimeError, ConnectionError, ValueError) as e:
        logger.warning(f"Stats failed: {e}")
    test_search(client, embedder)


if __name__ == "__main__":
    migrate(batch_size=10)
