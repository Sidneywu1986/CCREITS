#!/usr/bin/env python3
"""
增量向量化公众号文章 —— PostgreSQL + sklearn Embedding + PostgreSQL 向量存储版
无需 Milvus/Docker，纯 Python 实现
"""

import os
import sys
import argparse
import logging
import re
import json
from datetime import datetime
from typing import List, Dict, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.db import get_conn

logger = logging.getLogger("vectorize")

# ---------- 配置 ----------
CHUNK_SIZE = 512
OVERLAP = 64
VECTOR_DIM = 256

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


# ---------- 轻量 Embedding (sklearn TF-IDF + SVD) ----------
class SklearnEmbedder:
    """Lightweight embedding using TF-IDF + SVD"""

    def __init__(self, dim: int = VECTOR_DIM):
        self.dim = dim
        self._vectorizer = None
        self._svd = None
        self._fitted = False

    def _ensure_fitted(self, texts: List[str]):
        if self._fitted:
            return
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.decomposition import TruncatedSVD

        logger.info(f"Fitting TF-IDF + SVD on {len(texts)} texts...")
        self._vectorizer = TfidfVectorizer(
            max_features=5000,
            min_df=2,
            max_df=0.95,
            ngram_range=(1, 2)
        )
        tfidf = self._vectorizer.fit_transform(texts)

        actual_dim = min(self.dim, tfidf.shape[1])
        self._svd = TruncatedSVD(n_components=actual_dim)
        self._svd.fit(tfidf)
        self.dim = actual_dim
        self._fitted = True
        logger.info(f"Embedding dim set to {self.dim}")

    def encode(self, texts: List[str]) -> List[List[float]]:
        self._ensure_fitted(texts)
        from sklearn.preprocessing import normalize

        tfidf = self._vectorizer.transform(texts)
        vectors = self._svd.transform(tfidf)
        vectors = normalize(vectors)
        return vectors.tolist()


# ---------- 分块逻辑 ----------
def split_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> List[str]:
    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)

        if end < text_len:
            best_pos = end
            for punct in ['\u3002', '\uff01', '\uff1f', '\n', '\uff1b']:
                pos = text.rfind(punct, start, end)
                if pos > start + chunk_size // 3:
                    best_pos = pos + 1
                    break

            if best_pos == end:
                for sep in ['\uff0c', '\u3001', ' ']:
                    pos = text.rfind(sep, start, end)
                    if pos > start + chunk_size // 3:
                        best_pos = pos + 1
                        break

            end = best_pos

        chunk = text[start:end].strip()
        if len(chunk) > 20:
            chunks.append(chunk)

        next_start = end - overlap
        start = next_start if next_start > start else end

    return chunks


# ---------- 数据库操作 ----------
def ensure_vector_tables(dim: int):
    """Create tables for vector storage in PostgreSQL"""
    stmts = [
        """
        CREATE TABLE IF NOT EXISTS business.article_vectors (
            id SERIAL PRIMARY KEY,
            article_id INTEGER NOT NULL REFERENCES business.wechat_articles(id),
            chunk_index INTEGER NOT NULL,
            chunk_text TEXT,
            vector TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(article_id, chunk_index)
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_vec_article ON business.article_vectors(article_id)",
        "CREATE INDEX IF NOT EXISTS idx_vec_created ON business.article_vectors(created_at)",
    ]
    with get_conn() as conn:
        cur = conn.cursor()
        for stmt in stmts:
            cur.execute(stmt)
        conn.commit()


def fetch_pending_articles() -> List[Dict]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, source, title, published, content
            FROM business.wechat_articles
            WHERE vectorized = FALSE AND content IS NOT NULL AND LENGTH(TRIM(content)) > 50
            ORDER BY published DESC
        """)
        return [dict(row) for row in cur.fetchall()]


def mark_vectorized(article_ids: List[int]):
    placeholders = ",".join(["%s"] * len(article_ids))
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            UPDATE business.wechat_articles
            SET vectorized = TRUE, updated_at = CURRENT_TIMESTAMP
            WHERE id IN ({placeholders})
        """, article_ids)
        conn.commit()


def get_not_vectorized_count() -> int:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM business.wechat_articles WHERE vectorized = FALSE AND content IS NOT NULL")
        row = cur.fetchone()
        return row['count'] if row else 0


def insert_vectors(entities: List[Dict]):
    """Insert vectors as JSON text"""
    sql = """
    INSERT INTO business.article_vectors (article_id, chunk_index, chunk_text, vector)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (article_id, chunk_index) DO NOTHING
    """
    rows = []
    for e in entities:
        rows.append((
            e["article_id"],
            e["chunk_index"],
            e["chunk_text"],
            json.dumps(e["vector"])
        ))
    with get_conn() as conn:
        cur = conn.cursor()
        cur.executemany(sql, rows)
        conn.commit()


# ---------- 向量搜索 ----------
def search_similar(query_vector: List[float], top_k: int = 5,
                   source_filter: Optional[str] = None) -> List[Dict]:
    """Search similar vectors using cosine similarity"""
    import numpy as np

    query = np.array(query_vector, dtype=np.float32)
    query_norm = np.linalg.norm(query)
    if query_norm == 0:
        return []
    query = query / query_norm

    where = ""
    params = []
    if source_filter:
        where = "WHERE a.source = %s"
        params.append(source_filter)

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT v.id, v.article_id, v.chunk_text, v.vector,
                   a.source, a.title, a.published
            FROM business.article_vectors v
            JOIN business.wechat_articles a ON v.article_id = a.id
            {where}
        """, params)

        results = []
        for row in cur.fetchall():
            vec = np.array(json.loads(row['vector']), dtype=np.float32)
            vec_norm = np.linalg.norm(vec)
            if vec_norm == 0:
                continue
            vec = vec / vec_norm
            similarity = float(np.dot(query, vec))
            results.append({
                "id": row['id'],
                "article_id": row['article_id'],
                "chunk_text": row['chunk_text'],
                "source": row['source'],
                "title": row['title'],
                "published": row['published'],
                "similarity": similarity,
            })

    # Sort by similarity descending
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:top_k]


# ---------- 主流程 ----------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, default=100, help="Unused, kept for compatibility")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    embedder = SklearnEmbedder(dim=VECTOR_DIM)

    logger.info("Connecting to PostgreSQL...")
    
    total_pending = get_not_vectorized_count()
    logger.info(f"Pending articles: {total_pending}")

    if total_pending == 0:
        logger.info("No pending articles, done")
        return

    # First pass: collect all texts
    logger.info("First pass: collecting all texts...")
    all_texts = []
    articles_data = []

    for art in fetch_pending_articles():
        chunks = split_text(art["content"])
        if chunks:
            all_texts.extend(chunks)
            articles_data.append({"article": art, "chunks": chunks})

    if not all_texts:
        logger.info("No valid chunks found")
        return

    logger.info(f"Total chunks: {len(all_texts)}, from {len(articles_data)} articles")

    # Fit embedder
    logger.info("Fitting embedder...")
    embeddings = embedder.encode(all_texts)
    actual_dim = len(embeddings[0])
    logger.info(f"Actual vector dim: {actual_dim}")

    if args.dry_run:
        logger.info(f"[DRY-RUN] Would process {len(articles_data)} articles, {len(all_texts)} chunks")
        return

    # Ensure vector tables exist
    ensure_vector_tables(actual_dim)

    # Build entities
    entities = []
    vectorized_ids = set()
    idx = 0
    for item in articles_data:
        art = item["article"]
        chunks = item["chunks"]
        for i, chunk in enumerate(chunks):
            entities.append({
                "article_id": art["id"],
                "chunk_index": i,
                "chunk_text": chunk[:1500],
                "vector": embeddings[idx],
            })
            idx += 1
            vectorized_ids.add(art["id"])

    # Insert vectors
    insert_vectors(entities)

    # Mark as vectorized
    mark_vectorized(list(vectorized_ids))

    logger.info(f"All done! Processed {len(vectorized_ids)} articles, {len(entities)} chunks, dim={actual_dim}")

    # Quick verification: test search
    logger.info("Running verification search...")
    test_query = embedder.encode(["REITs 投资分析"])[0]
    results = search_similar(test_query, top_k=3)
    for r in results:
        logger.info(f"  [{r['source'][:20]}] sim={r['similarity']:.3f} | {r['title'][:40]}")


if __name__ == "__main__":
    main()
