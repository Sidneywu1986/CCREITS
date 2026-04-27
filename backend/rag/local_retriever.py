#!/usr/bin/env python3
"""
纯本地向量检索器（SQLite + numpy）
对接 article_vectors 表，零外部依赖
"""

import os
import json
import sqlite3
import numpy as np
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    article_id: int
    source: str
    title: str
    publish_date: str
    chunk_text: str
    score: float          # cosine similarity
    chunk_index: int


class SklearnEmbedder:
    """轻量 Embedding（TF-IDF + SVD），复用自 vectorize_articles.py"""

    def __init__(self, dim: int = 256):
        self.dim = dim
        self._vectorizer = None
        self._svd = None
        self._fitted = False

    def fit(self, texts: List[str]):
        """Fit on corpus（初始化时调用一次）"""
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.decomposition import TruncatedSVD
        from sklearn.preprocessing import normalize

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
        logger.info(f"Embedding dim: {self.dim}")

    def encode(self, texts: List[str]) -> List[List[float]]:
        if not self._fitted:
            raise RuntimeError("Embedder not fitted. Call fit() first.")
        from sklearn.preprocessing import normalize

        tfidf = self._vectorizer.transform(texts)
        vectors = self._svd.transform(tfidf)
        vectors = normalize(vectors)
        return vectors.tolist()


class LocalVectorRetriever:
    """
    纯本地检索，零外部依赖。
    适合万级向量以内场景。
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.join(
            os.path.dirname(__file__), "..", "database", "reits.db"
        )
        self._embedder: Optional[SklearnEmbedder] = None
        self._vectors: Optional[np.ndarray] = None
        self._meta: List[Dict] = []
        self._article_fund_tags: Dict[int, Set[str]] = {}
        self._fund_article_tags: Dict[str, Set[int]] = {}
        self._initialized = False

    def _ensure_initialized(self):
        if self._initialized:
            return
        logger.info("Initializing LocalVectorRetriever...")

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Check if article_vectors exists
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='article_vectors'")
        if not cur.fetchone():
            conn.close()
            raise RuntimeError("article_vectors table not found. Run vectorize_articles.py first.")

        # Load all vectors and texts for fitting
        cur.execute("""
            SELECT v.article_id, v.chunk_index, v.vector, v.chunk_text,
                   a.source, a.title, a.published
            FROM article_vectors v
            JOIN wechat_articles a ON v.article_id = a.id
            WHERE a.vectorized = 1
        """)

        rows = cur.fetchall()
        if not rows:
            conn.close()
            raise RuntimeError("No vectors found in article_vectors.")

        texts = []
        self._meta = []
        vectors_list = []

        for row in rows:
            vec = json.loads(row[2])
            vectors_list.append(vec)
            texts.append(row[3])  # chunk_text for fitting
            self._meta.append({
                "article_id": row[0],
                "chunk_index": row[1],
                "chunk_text": row[3],
                "source": row[4],
                "title": row[5],
                "publish_date": row[6],
            })

        # Load article_fund_tags mapping
        cur.execute("SELECT article_id, fund_code FROM article_fund_tags")
        for row in cur.fetchall():
            aid = row[0]
            fc = row[1]
            if aid not in self._article_fund_tags:
                self._article_fund_tags[aid] = set()
            self._article_fund_tags[aid].add(fc)
            if fc not in self._fund_article_tags:
                self._fund_article_tags[fc] = set()
            self._fund_article_tags[fc].add(aid)

        conn.close()

        # Fit embedder on all chunk texts
        self._embedder = SklearnEmbedder(dim=256)
        self._embedder.fit(texts)

        # Pre-normalize all vectors for fast cosine similarity
        self._vectors = np.array(vectors_list, dtype=np.float32)
        norms = np.linalg.norm(self._vectors, axis=1, keepdims=True)
        self._vectors = self._vectors / (norms + 1e-8)

        self._initialized = True
        logger.info(f"Retriever ready: {len(self._meta)} vectors, dim={self._embedder.dim}")

    def search(self, query: str, top_k: int = 5, source_filter: Optional[str] = None, fund_code: Optional[str] = None) -> List[SearchResult]:
        """语义搜索，支持基金代码加权"""
        self._ensure_initialized()

        # Encode query
        query_vec = np.array(self._embedder.encode([query])[0], dtype=np.float32)
        query_norm = np.linalg.norm(query_vec)

        # Zero-vector fallback: when query has no overlapping vocab with corpus
        if query_norm < 1e-6:
            return self._fallback_search(top_k=top_k, source_filter=source_filter, fund_code=fund_code)

        query_vec = query_vec / (query_norm + 1e-8)

        # Compute cosine similarity with all vectors
        scores = self._vectors.dot(query_vec).copy()

        # Apply source filter
        indices = list(range(len(self._meta)))
        if source_filter:
            indices = [i for i in indices if self._meta[i]["source"] == source_filter]
            if not indices:
                return []
            scores = scores[indices]
        else:
            scores = scores[indices]

        # Collect results
        results = []

        # If fund_code specified, force-include tagged articles first
        if fund_code:
            tagged_article_ids = self._fund_article_tags.get(fund_code, set())
            tagged_indices = []
            other_indices = []
            for idx in indices:
                meta = self._meta[idx]
                if meta["article_id"] in tagged_article_ids:
                    tagged_indices.append(idx)
                else:
                    other_indices.append(idx)

            # Sort tagged by vector score descending
            tagged_scores = [(float(scores[indices.index(idx)]) if source_filter else float(scores[idx]), idx) for idx in tagged_indices]
            tagged_scores.sort(key=lambda x: x[0], reverse=True)

            # Fill results with tagged articles up to top_k
            for score, idx in tagged_scores[:top_k]:
                meta = self._meta[idx]
                results.append(SearchResult(
                    article_id=meta["article_id"],
                    source=meta["source"],
                    title=meta["title"],
                    publish_date=meta["publish_date"],
                    chunk_text=meta["chunk_text"],
                    score=round(score * 1.5, 4),
                    chunk_index=meta["chunk_index"],
                ))

            # If still need more, fill from others
            if len(results) < top_k:
                other_scores = [(float(scores[indices.index(idx)]) if source_filter else float(scores[idx]), idx) for idx in other_indices]
                other_scores.sort(key=lambda x: x[0], reverse=True)
                need = top_k - len(results)
                for score, idx in other_scores[:need]:
                    meta = self._meta[idx]
                    results.append(SearchResult(
                        article_id=meta["article_id"],
                        source=meta["source"],
                        title=meta["title"],
                        publish_date=meta["publish_date"],
                        chunk_text=meta["chunk_text"],
                        score=round(score * 0.7, 4),
                        chunk_index=meta["chunk_index"],
                    ))
            return results

        # Normal search without fund_code
        candidate_idx = np.argsort(scores)[::-1][:top_k]
        for idx in candidate_idx:
            real_idx = indices[idx] if source_filter else idx
            meta = self._meta[real_idx]
            results.append(SearchResult(
                article_id=meta["article_id"],
                source=meta["source"],
                title=meta["title"],
                publish_date=meta["publish_date"],
                chunk_text=meta["chunk_text"],
                score=round(float(scores[idx]), 4),
                chunk_index=meta["chunk_index"],
            ))
        return results

    def _fallback_search(self, top_k: int = 5, source_filter: Optional[str] = None, fund_code: Optional[str] = None) -> List[SearchResult]:
        """当查询向量为零时的兜底检索：优先返回带基金标签的文章"""
        results = []
        if fund_code:
            tagged_article_ids = self._fund_article_tags.get(fund_code, set())
            # Collect all chunks from tagged articles
            tagged = []
            for i, meta in enumerate(self._meta):
                if source_filter and meta["source"] != source_filter:
                    continue
                if meta["article_id"] in tagged_article_ids:
                    tagged.append((1.0, i))
            # Take diverse articles (one chunk per article to avoid same-article dominance)
            seen_articles = set()
            for score, idx in tagged:
                aid = self._meta[idx]["article_id"]
                if aid not in seen_articles:
                    seen_articles.add(aid)
                    meta = self._meta[idx]
                    results.append(SearchResult(
                        article_id=meta["article_id"],
                        source=meta["source"],
                        title=meta["title"],
                        publish_date=meta["publish_date"],
                        chunk_text=meta["chunk_text"],
                        score=round(score, 4),
                        chunk_index=meta["chunk_index"],
                    ))
                if len(results) >= top_k:
                    return results

        # Fallback: return first few chunks
        for i, meta in enumerate(self._meta):
            if source_filter and meta["source"] != source_filter:
                continue
            results.append(SearchResult(
                article_id=meta["article_id"],
                source=meta["source"],
                title=meta["title"],
                publish_date=meta["publish_date"],
                chunk_text=meta["chunk_text"],
                score=0.5,
                chunk_index=meta["chunk_index"],
            ))
            if len(results) >= top_k:
                break
        return results

    def search_by_article(self, article_id: int) -> List[SearchResult]:
        """获取单篇文章的所有向量块"""
        self._ensure_initialized()

        results = []
        for i, meta in enumerate(self._meta):
            if meta["article_id"] == article_id:
                results.append(SearchResult(
                    article_id=meta["article_id"],
                    source=meta["source"],
                    title=meta["title"],
                    publish_date=meta["publish_date"],
                    chunk_text=meta["chunk_text"],
                    score=1.0,
                    chunk_index=meta["chunk_index"],
                ))
        return results

    def get_article_meta(self, article_id: int) -> Optional[Dict]:
        """取文章元数据"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, source, title, link, published, content_length
            FROM wechat_articles WHERE id = ?
        """, (article_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        return {
            "id": row[0], "source": row[1], "title": row[2],
            "link": row[3], "published": row[4], "content_length": row[5]
        }

    def get_stats(self) -> Dict:
        """获取检索器统计信息"""
        self._ensure_initialized()
        unique_articles = len(set(m["article_id"] for m in self._meta))
        return {
            "total_vectors": len(self._meta),
            "unique_articles": unique_articles,
            "embedding_dim": self._embedder.dim if self._embedder else 0,
        }


# 全局单例（延迟初始化）
_retriever: Optional[LocalVectorRetriever] = None


def get_retriever() -> LocalVectorRetriever:
    global _retriever
    if _retriever is None:
        _retriever = LocalVectorRetriever()
    return _retriever
