#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI投研 API
分层LLM: 投研用openai (gpt_4o)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
import logging

router = APIRouter(prefix="/api/ai", tags=["AI投研"])

logger = logging.getLogger(__name__)


class ResearchRequest(BaseModel):
    """AI投研请求模型"""
    session_id: Optional[int] = None
    message: str
    fund_codes: List[str] = []
    analysis_type: str = "general"
    agent_name: Optional[str] = "投研小助手"


class ResearchResponse(BaseModel):
    """AI投研响应模型"""
    session_id: int
    result_id: int
    role: str
    content: str
    agent_name: str
    analysis: Dict


async def _fulltext_search_fallback(query: str, top_k: int = 5) -> List[dict]:
    """PostgreSQL fulltext fallback when Milvus is unavailable"""
    from ai_db.models import Article
    results = await Article.filter(
        title__icontains=query
    ).limit(top_k).all()
    return [{"type": "article", "id": r.id, "title": r.title[:100], "content": (r.content or "")[:200]} for r in results]


@router.post("/research", response_model=ResearchResponse)
async def research(req: ResearchRequest):
    """
    AI投研接口
    1. 获取或创建session
    2. 保存用户消息
    3. 获取agent配置
    4. 检索相关基金和公告 (Milvus或全文fallback)
    5. 调用LLM (openai gpt_4o)
    6. 保存AI响应
    7. 返回响应
    """
    try:
        from tortoise import Tortoise
        from ai_db.models import ResearchSession, ResearchMessage, AiChatAgent
        from vector.milvus_client import get_milvus_client
        from vector.embedding_service import get_embedding_service
        from core.config import settings

        # 初始化数据库连接
        if not Tortoise._db_handler:
            await Tortoise.init(
                db_url=settings.AI_DB_CONFIG["connections"]["default"]["credentials"].get(
                    "database", "sqlite://:memory:"
                ) if settings.AI_DB_CONFIG["connections"]["default"]["engine"] == "tortoise.backends.sqlite"
                else f"postgres://{settings.AI_DB_CONFIG['connections']['default']['credentials']['user']}:{settings.AI_DB_CONFIG['connections']['default']['credentials']['password']}@{settings.AI_DB_CONFIG['connections']['default']['credentials']['host']}:{settings.AI_DB_CONFIG['connections']['default']['credentials']['port']}/{settings.AI_DB_CONFIG['connections']['default']['credentials']['database']}",
                modules={'ai_db': ['ai_db.models']}
            )

        # 1. Get or create session
        if req.session_id:
            session = await ResearchSession.filter(id=req.session_id).first()
            if not session:
                session = await ResearchSession.create()
        else:
            session = await ResearchSession.create()

        # 2. Save user message
        user_msg = await ResearchMessage.create(
            session=session,
            role="user",
            content=req.message
        )

        # 3. Get agent config
        agent = await AiChatAgent.filter(agent_name=req.agent_name, is_active=True).first()
        if not agent:
            agent = await AiChatAgent.filter(is_active=True).first()
        if not agent:
            raise HTTPException(status_code=404, detail="无可用AI智能体")

        # 4. Retrieve research contexts (Milvus or fulltext fallback)
        research_contexts = []
        try:
            milvus = get_milvus_client()
            if milvus.is_healthy():
                embedding_svc = get_embedding_service()
                query_vector = embedding_svc.embed_text(req.message)
                results = milvus.search("research_contents", query_vector, top_k=5)
                for hits in results:
                    for hit in hits:
                        research_contexts.append({
                            "id": hit["id"],
                            "content": hit["content"],
                            "distance": hit["distance"]
                        })
            else:
                logger.warning("Milvus not healthy, using fulltext fallback")
                research_contexts = await _fulltext_search_fallback(req.message)
        except (RuntimeError, ValueError, KeyError) as e:
            logger.warning(f"Vector search failed, using fallback: {e}")
            research_contexts = await _fulltext_search_fallback(req.message)

        # 5. Call LLM (openai gpt_4o for research)
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(
                api_key=settings.LLM_CONFIG["gpt_4o"]["api_key"],
                base_url=settings.LLM_CONFIG["gpt_4o"]["base_url"]
            )

            # 构建系统提示
            system_prompt = agent.system_prompt or "你是一个专业的REITs投研助手。"

            # 构建上下文
            context = ""
            if research_contexts:
                context = "\n\n投研参考:\n" + "\n".join([c["content"] for c in research_contexts[:3]])

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": req.message + context}
            ]

            response = await client.chat.completions.create(
                model=settings.LLM_CONFIG["gpt_4o"]["model"],
                messages=messages,
                temperature=agent.temperature,
                max_tokens=agent.max_tokens
            )

            ai_content = response.choices[0].message.content
        except (RuntimeError, ValueError, ConnectionError) as e:
            logger.error(f"LLM call failed: {e}")
            ai_content = "抱歉，AI服务暂时不可用，请稍后重试"

        # 6. Save AI response
        ai_msg = await ResearchMessage.create(
            session=session,
            role="assistant",
            content=ai_content
        )

        # 7. Return response
        return ResearchResponse(
            session_id=session.id,
            result_id=ai_msg.id,
            role="assistant",
            content=ai_content,
            agent_name=agent.agent_name,
            analysis={"type": "research", "contexts_count": len(research_contexts)}
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("research error")
        raise HTTPException(status_code=500, detail="服务暂时不可用，请稍后重试")
