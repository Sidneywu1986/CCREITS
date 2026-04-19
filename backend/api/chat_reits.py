#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI聊REITs API
分层LLM: REITs用deepseek
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import logging

router = APIRouter(prefix="/api/ai", tags=["AI聊天REITs"])

logger = logging.getLogger(__name__)


class ChatReitsRequest(BaseModel):
    """AI聊REITs请求模型"""
    session_id: Optional[int] = None
    message: str
    agent_name: Optional[str] = "老李"


class ChatReitsResponse(BaseModel):
    """AI聊REITs响应模型"""
    session_id: int
    message_id: int
    role: str
    content: str
    agent_name: str
    sources: List[dict]


async def _fulltext_search_fallback(query: str, top_k: int = 5) -> List[dict]:
    """PostgreSQL fulltext fallback when Milvus is unavailable"""
    from ai_db.models import SocialHotspot
    results = await SocialHotspot.filter(
        title__icontains=query
    ).limit(top_k).all()
    return [{"type": "hotspot", "id": r.id, "title": r.title[:100]} for r in results]


@router.post("/chat-reits", response_model=ChatReitsResponse)
async def chat_reits(req: ChatReitsRequest):
    """
    AI聊REITs接口
    1. 获取或创建session
    2. 保存用户消息
    3. 获取agent配置
    4. 检索sources (Milvus或全文fallback)
    5. 调用LLM (deepseek)
    6. 保存AI响应
    7. 返回响应
    """
    try:
        from tortoise import Tortoise
        from ai_db.models import AiChatSession, AiChatMessage, AiChatAgent
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
            session = await AiChatSession.filter(id=req.session_id).first()
            if not session:
                session = await AiChatSession.create(session_type="reits")
        else:
            session = await AiChatSession.create(session_type="reits")

        # 2. Save user message
        user_msg = await AiChatMessage.create(
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

        # 4. Retrieve sources (Milvus or fulltext fallback)
        sources = []
        try:
            milvus = get_milvus_client()
            if milvus.is_healthy():
                embedding_svc = get_embedding_service()
                query_vector = embedding_svc.embed_text(req.message)
                results = milvus.search("reits_contents", query_vector, top_k=5)
                for hits in results:
                    for hit in hits:
                        sources.append({
                            "id": hit["id"],
                            "content": hit["content"],
                            "distance": hit["distance"]
                        })
            else:
                logger.warning("Milvus not healthy, using fulltext fallback")
                sources = await _fulltext_search_fallback(req.message)
        except Exception as e:
            logger.warning(f"Vector search failed, using fallback: {e}")
            sources = await _fulltext_search_fallback(req.message)

        # 5. Call LLM (deepseek for REITs)
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(
                api_key=settings.LLM_CONFIG["deepseek"]["api_key"],
                base_url=settings.LLM_CONFIG["deepseek"]["base_url"]
            )

            # 构建系统提示
            system_prompt = agent.system_prompt or "你是一个专业的REITs投资助手。"

            # 构建上下文
            context = ""
            if sources:
                context = "\n\n参考信息:\n" + "\n".join([s["content"] for s in sources[:3]])

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": req.message + context}
            ]

            response = await client.chat.completions.create(
                model=settings.LLM_CONFIG["deepseek"]["model"],
                messages=messages,
                temperature=agent.temperature,
                max_tokens=agent.max_tokens
            )

            ai_content = response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            ai_content = f"抱歉，AI服务暂时不可用: {str(e)}"

        # 6. Save AI response
        ai_msg = await AiChatMessage.create(
            session=session,
            role="assistant",
            content=ai_content,
            model=agent.model
        )

        # 7. Return response
        return ChatReitsResponse(
            session_id=session.id,
            message_id=ai_msg.id,
            role="assistant",
            content=ai_content,
            agent_name=agent.agent_name,
            sources=sources
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"chat_reits error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
