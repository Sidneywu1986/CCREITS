"""
将 SQLite article_vectors 数据增量导入 Milvus
"""
import os
import sys
import json
import sqlite3
from tqdm import tqdm

sys.path.insert(0, os.path.dirname(__file__))

from core.config import settings
from vector.milvus_client import get_milvus_client

SQLITE_DB = 'database/reits.db'
COLLECTION = 'reit_wechat_articles'
BATCH_SIZE = 500


def _get_existing_milvus_ids() -> set:
    """获取 Milvus 中已有的 article_id + chunk_index 组合"""
    try:
        from pymilvus import MilvusClient
        mc = MilvusClient('http://localhost:19530')
        if 'reit_wechat_articles' not in mc.list_collections():
            return set()
        stats = mc.get_collection_stats('reit_wechat_articles')
        if stats.get('row_count', 0) == 0:
            return set()
        results = mc.query(
            collection_name='reit_wechat_articles',
            filter='article_id >= 0',
            output_fields=['article_id', 'chunk_index'],
            limit=100000
        )
        return {(r['article_id'], r['chunk_index']) for r in results}
    except Exception as e:
        print(f"[Milvus] Failed to query existing IDs: {e}")
        return set()


def main():
    # 1. Connect to Milvus
    print("Connecting to Milvus...")
    milvus = get_milvus_client()
    if not milvus.connect():
        print("Failed to connect to Milvus")
        return

    # 2. Ensure collection
    print(f"Ensuring collection: {COLLECTION}")
    milvus.ensure_collection(dim=256)

    # 3. Get existing IDs for incremental import
    existing = _get_existing_milvus_ids()
    print(f"Existing vectors in Milvus: {len(existing)}")

    # 4. Load data from SQLite
    print("Loading vectors from SQLite...")
    conn = sqlite3.connect(SQLITE_DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT v.article_id, v.chunk_index, v.chunk_text, v.vector,
               a.source, a.title, a.published
        FROM article_vectors v
        JOIN wechat_articles a ON v.article_id = a.id
    """)

    batch = []
    total = 0
    skipped = 0
    for row in tqdm(cur.fetchall(), desc="Importing"):
        article_id, chunk_index, chunk_text, vector_json, source, title, published = row
        if (article_id, chunk_index) in existing:
            skipped += 1
            continue
        vec = json.loads(vector_json)
        batch.append({
            "article_id": article_id,
            "chunk_index": chunk_index,
            "chunk_text": chunk_text[:4000] if chunk_text else "",
            "source": source or "",
            "title": title or "",
            "publish_date": str(published) if published else "",
            "embedding": vec,
        })

        if len(batch) >= BATCH_SIZE:
            milvus.insert(batch)
            total += len(batch)
            batch = []

    if batch:
        milvus.insert(batch)
        total += len(batch)

    conn.close()
    print(f"Imported: {total} new vectors, Skipped: {skipped} existing")

    if total > 0:
        print("Flushing...")
        from pymilvus import MilvusClient as PyMC
        pmc = PyMC('http://localhost:19530')
        pmc.flush('reit_wechat_articles')
        print("Creating index...")
        from pymilvus.milvus_client.index import IndexParams
        idx = IndexParams()
        idx.add_index(field_name='embedding', metric_type='COSINE', index_type='IVF_FLAT', params={'nlist':128})
        pmc.create_index('reit_wechat_articles', index_params=idx)
        print("Loading collection...")
        pmc.load_collection('reit_wechat_articles')
    print("Done!")


if __name__ == '__main__':
    main()
