#!/usr/bin/env python3
"""
文章语义搜索 - 内部RAG模块
原则：向量检索用于AI内部推理，不对外暴露全文搜索接口
"""

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging

from rag.local_retriever import get_retriever, SearchResult
from vector.milvus_client import get_milvus_client
import psycopg2

from core.db import get_conn

router = APIRouter(prefix="/api/v1/search", tags=["search"])
logger = logging.getLogger(__name__)


class SearchResponse(BaseModel):
    query: str
    results: List[dict]
    total: int
    search_time_ms: float


# ---------- 内部接口（仅供 chat_reits.py RAG 调用）----------


def _get_fund_name(fund_code: str) -> Optional[str]:
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT fund_name FROM business.funds WHERE fund_code = %s", (fund_code,))
            row = cur.fetchone()
            return row['fund_name'] if row else None
    except Exception:
        return None


def _get_fund_articles_pg(fund_code: str) -> set:
    """从 PostgreSQL 查询该基金关联的文章 ID"""
    try:
        from core.db import get_conn
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT article_id FROM business.article_fund_tags WHERE fund_code = %s", (fund_code,))
            rows = cur.fetchall()
            return {r[0] for r in rows}
    except Exception:
        return set()


def _search_milvus(query: str, top_k: int = 5, fund_code: Optional[str] = None) -> List[SearchResult]:
    """使用 Milvus 做向量检索（BGE-M3 编码）"""
    milvus = get_milvus_client()
    if not milvus.connect():
        return []

    # 获取查询向量：使用 BGE-M3 编码
    from rag.bge_embedder import get_embedder
    import numpy as np
    embedder = get_embedder()
    query_vec = embedder.encode_query(query)
    query_vec = query_vec / (np.linalg.norm(query_vec) + 1e-8)

    results = milvus.search(vector=query_vec.tolist(), top_k=top_k * 3)
    if not results:
        return []

    # fund_code 重排序
    tagged_ids = set()
    if fund_code:
        tagged_ids = _get_fund_articles_pg(fund_code)

    reranked = []
    for r in results:
        score = r.get("distance", 0)
        aid = r.get("article_id")
        if fund_code:
            if aid in tagged_ids:
                score *= 1.5
            else:
                score *= 0.7
        reranked.append((score, r))

    reranked.sort(key=lambda x: x[0], reverse=True)

    search_results = []
    for score, r in reranked[:top_k]:
        search_results.append(SearchResult(
            article_id=r.get("article_id", 0),
            source=r.get("source", ""),
            title=r.get("title", ""),
            publish_date=str(r.get("publish_date", "")),
            chunk_text=r.get("chunk_text", ""),
            score=round(score, 4),
            chunk_index=0,
        ))
    return search_results


def search_articles_for_rag(query: str, top_k: int = 5, fund_code: Optional[str] = None) -> List[SearchResult]:
    """
    供 chat_reits.py 直接调用的函数，不走 HTTP。
    返回 SearchResult 列表，供注入 Prompt。
    fund_code: 若指定，优先返回包含该基金标签的文章，并将基金名称融入查询增强语义匹配。
    """
    # 1. 优先尝试 Milvus
    try:
        enhanced_query = query
        if fund_code:
            fund_name = _get_fund_name(fund_code)
            if fund_name:
                enhanced_query = f"{query} {fund_name}"
        milvus_results = _search_milvus(enhanced_query, top_k=top_k, fund_code=fund_code)
        if milvus_results:
            return milvus_results
    except Exception as e:
        logger.warning(f"Milvus search failed: {e}")

    # 2. Fallback to SQLite local retriever
    try:
        retriever = get_retriever()
        enhanced_query = query
        if fund_code:
            fund_name = _get_fund_name(fund_code)
            if fund_name:
                enhanced_query = f"{query} {fund_name}"
        return retriever.search(enhanced_query, top_k=top_k, fund_code=fund_code)
    except Exception as e:
        logger.warning(f"RAG search failed: {e}")
        return []


# ---------- 对外接口（严格脱敏，仅统计和确认服务状态）----------

@router.get("/stats")
async def get_search_stats():
    """
    获取检索器统计信息（仅数字，不暴露内容）。
    示例: GET /api/v1/search/stats
    """
    try:
        retriever = get_retriever()
        stats = retriever.get_stats()
        return {
            "total_vectors": stats["total_vectors"],
            "unique_articles": stats["unique_articles"],
            "embedding_dim": stats["embedding_dim"],
            "status": "ready",
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ⚠️ 以下接口已移除，保护独家内容资产：
# - GET /api/v1/search/articles?q=...    ❌ 移除：防止全文外泄
# - GET /api/v1/search/articles/{id}     ❌ 移除：防止原文暴露
# - GET /api/v1/search/suggestions       ❌ 移除：防止标题泄露
#
# 如需内部管理后台搜索，建议：
# 1. 新建 /admin/search 路由，加管理员鉴权
# 2. 或直接在数据库客户端查询
