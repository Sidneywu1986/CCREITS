#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI聊公告 API
分层LLM: 公告用openai (gpt_4o_mini)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import logging

router = APIRouter(prefix="/api/ai", tags=["AI聊天公告"])

logger = logging.getLogger(__name__)


class ChatAnnouncementRequest(BaseModel):
    """AI聊公告请求模型"""
    session_id: Optional[int] = None
    message: str
    announcement_ids: List[int] = []
    agent_name: Optional[str] = "小智"


class ChatAnnouncementResponse(BaseModel):
    """AI聊公告响应模型"""
    session_id: int
    message_id: int
    role: str
    content: str
    agent_name: str
    sources: List[dict]


async def _fulltext_search_fallback(query: str, announcement_ids: List[int], top_k: int = 5) -> List[dict]:
    """PostgreSQL fulltext fallback when Milvus is unavailable"""
    from ai_db.models import AnnouncementContent
    filters = []
    if announcement_ids:
        filters.append(announcement_id__in=announcement_ids)
    if query:
        filters.append(content_text__icontains=query)
    results = await AnnouncementContent.filter(*filters).limit(top_k).all() if filters else []
    return [{"type": "announcement", "id": r.id, "content": (r.content_text or "")[:200]} for r in results]


@router.post("/chat-announcement", response_model=ChatAnnouncementResponse)
async def chat_announcement(req: ChatAnnouncementRequest):
    """
    AI聊公告接口
    1. 获取或创建session
    2. 保存用户消息
    3. 获取agent配置
    4. 检索上下文 (Milvus或全文fallback)
    5. 调用LLM (openai)
    6. 保存AI响应
    7. 返回响应
    """
    try:
        from tortoise import Tortoise
        from ai_db.models import AnnouncementChatSession, AnnouncementChatMessage, AiChatAgent
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
            session = await AnnouncementChatSession.filter(id=req.session_id).first()
            if not session:
                session = await AnnouncementChatSession.create()
        else:
            session = await AnnouncementChatSession.create()

        # 2. Save user message
        user_msg = await AnnouncementChatMessage.create(
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

        # 4. Retrieve contexts (Milvus or fulltext fallback)
        contexts = []
        try:
            milvus = get_milvus_client()
            if milvus.is_healthy():
                embedding_svc = get_embedding_service()
                query_vector = embedding_svc.embed_text(req.message)
                results = milvus.search("announcement_contents", query_vector, top_k=5)
                for hits in results:
                    for hit in hits:
                        contexts.append({
                            "id": hit["id"],
                            "content": hit["content"],
                            "distance": hit["distance"]
                        })
            else:
                logger.warning("Milvus not healthy, using fulltext fallback")
                contexts = await _fulltext_search_fallback(req.message, req.announcement_ids)
        except (RuntimeError, ValueError, KeyError) as e:
            logger.warning(f"Vector search failed, using fallback: {e}")
            contexts = await _fulltext_search_fallback(req.message, req.announcement_ids)

        # 5. Call LLM (openai for announcements)
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(
                api_key=settings.LLM_CONFIG["gpt_4o_mini"]["api_key"],
                base_url=settings.LLM_CONFIG["gpt_4o_mini"]["base_url"]
            )

            # 构建系统提示
            system_prompt = agent.system_prompt or "你是一个专业的REITs公告分析助手。"

            # 构建上下文
            context = ""
            if contexts:
                context = "\n\n参考公告:\n" + "\n".join([c["content"] for c in contexts[:3]])

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": req.message + context}
            ]

            response = await client.chat.completions.create(
                model=settings.LLM_CONFIG["gpt_4o_mini"]["model"],
                messages=messages,
                temperature=agent.temperature,
                max_tokens=agent.max_tokens
            )

            ai_content = response.choices[0].message.content
        except (RuntimeError, ValueError, ConnectionError) as e:
            logger.error(f"LLM call failed: {e}")
            ai_content = "抱歉，AI服务暂时不可用，请稍后重试"

        # 6. Save AI response
        ai_msg = await AnnouncementChatMessage.create(
            session=session,
            role="assistant",
            content=ai_content
        )

        # 7. Return response
        return ChatAnnouncementResponse(
            session_id=session.id,
            message_id=ai_msg.id,
            role="assistant",
            content=ai_content,
            agent_name=agent.agent_name,
            sources=contexts
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("chat_announcement error")
        raise HTTPException(status_code=500, detail="服务暂时不可用，请稍后重试")
