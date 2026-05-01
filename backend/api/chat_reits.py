#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI聊REITs API
分层LLM: REITs用deepseek
RAG检索脱敏：向量全文用于AI内部推理，前端仅展示模糊溯源
"""
from fastapi import APIRouter, HTTPException, Depends
from core.auth.dependencies import optional_user
from core.auth.jwt import TokenPayload
from pydantic import BaseModel
from typing import Optional, List
import logging
import re

from api.search import search_articles_for_rag
from engine.sentiment import get_sentiment_engine
from agents.persona_router import get_persona_router
from agents.debate_manager import DebateManager

router = APIRouter(prefix="/api/ai", tags=["AI聊天REITs"])

logger = logging.getLogger(__name__)


class ChatReitsRequest(BaseModel):
    """AI聊REITs请求模型"""
    session_id: Optional[int] = None
    message: str
    agent_name: Optional[str] = "老K"
    persona: Optional[str] = None  # 显式指定人设：lao_k / su_su / lao_li / xiao_chen / wang_bo / standard
    fund_context: Optional[str] = None  # 当前关注的基金上下文（如"180101 博时蛇口产园REIT"）


class ChatReitsResponse(BaseModel):
    """AI聊REITs响应模型"""
    session_id: int
    message_id: int
    role: str
    content: str
    agent_name: str
    sources: List[dict]


async def _ensure_db():
    """Ensure Tortoise DB is initialized"""
    from tortoise import Tortoise
    if not Tortoise.is_inited():
        from core.config import settings
        c = settings.AI_DB_CONFIG["connections"]["default"]["credentials"]
        db_url = f"postgres://{c['user']}:{c['password']}@{c['host']}:{c['port']}/{c['database']}"
        await Tortoise.init(
            db_url=db_url,
            modules={'ai_db': ['ai_db.models']}
        )


async def _fulltext_search_fallback(query: str, top_k: int = 5) -> List[dict]:
    """PostgreSQL fulltext fallback when vector search is unavailable"""
    try:
        from ai_db.models import SocialHotspot
        results = await SocialHotspot.filter(
            title__icontains=query
        ).limit(top_k).all()
        return [{"type": "hotspot", "id": r.id, "title": r.title[:100]} for r in results]
    except (RuntimeError, ValueError, TypeError):
        return []


def _sanitize_citations(answer: str) -> str:
    """
    前端展示前脱敏：去除具体文章标题、公众号名称、日期+作者组合
    '咱们公众号那篇《消费REITs护城河》' → '我们此前的深度研究'
    'REITs新视线2024年7月分析' → '内部研究团队'
    """
    # 去书名号标题
    answer = re.sub(r'《[^》]+》', '相关研究', answer)
    # 去公众号名（常见中文公众号名模式）
    answer = re.sub(r'(?:公众号|微信号|专栏)[""\s]*[^\s，。]{2,20}[""\s]*', '内部研究', answer)
    # 去日期+来源组合
    answer = re.sub(r'\d{4}年\d{1,2}月[^\s，。]{2,15}(?:分析|报告|研报|点评)', '此前分析', answer)
    # 去具体引用标记如 [1] [2]
    answer = re.sub(r'\[\d+\]\s*【[^】]+】', '', answer)
    return answer


def _build_internal_context(rag_results) -> str:
    """
    构建内部RAG上下文（完整chunk，仅AI可见）
    保留来源标记以便AI理解信息层次，但不对用户暴露
    """
    if not rag_results:
        return ""
    lines = []
    for i, r in enumerate(rag_results[:5]):
        lines.append(f"[内部研究-{i+1}] {r.chunk_text[:400]}")
    return "\n\n参考信息（内部研究资料）：\n" + "\n\n".join(lines)


def _build_public_sources(rag_results, confidence: str) -> List[dict]:
    """
    构建前端可见的脱敏溯源信息
    用户只看见：置信度级别、资料类型、参考份数
    """
    count = len(rag_results) if rag_results else 0
    if count == 0:
        return []
    return [{
        "type": "internal_research",
        "confidence": confidence,
        "description": "基于内部研究资料",
        "count": count,
        # 绝不暴露以下字段给前端：
        # title: ❌
        # source: ❌
        # link: ❌
        # chunk_text: ❌
    }]


@router.post("/chat-reits", response_model=ChatReitsResponse)
async def chat_reits(req: ChatReitsRequest, user: Optional[TokenPayload] = Depends(optional_user)):
    """
    AI聊REITs接口
    核心原则：向量全文用于AI内部推理，前端仅展示脱敏回答+模糊溯源
    """
    try:
        from tortoise import Tortoise
        from ai_db.models import AiChatSession, AiChatMessage, AiChatAgent
        from core.config import settings

        # 初始化数据库连接
        if not Tortoise.is_inited():
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
        await AiChatMessage.create(
            session=session,
            role="user",
            content=req.message
        )

        # 3. 情感计算（获取当日市场情绪）
        try:
            market_emotion = get_sentiment_engine().get_market_emotion()
            emotion_tag = market_emotion.get("overall", "neutral")
            logger.info(f"Market emotion: {emotion_tag} ({market_emotion.get('score', 0)})")
        except (AttributeError, KeyError, ValueError) as e:
            logger.warning(f"Sentiment analysis failed: {e}")
            emotion_tag = "neutral"

        # 4. 人设路由（根据关键词或用户显式指定选择人格）
        persona_router = get_persona_router()
        persona_cfg = persona_router.route(req.message, mentioned=req.persona)
        logger.info(f"Persona selected: {persona_cfg.name} ({persona_cfg.name_cn})")

        # ===== 新增：判断是否走辩论模式 =====
        if DebateManager.should_debate(req.message) and not req.persona:
            # 辩论模式：返回系统提示，真正的辩论结果由WebSocket广播
            debate_hint = "🎙️ 已触发投研辩论会，老K、苏苏、老李、小陈、王博士正在独立撰写投资备忘录..."
            await AiChatMessage.create(
                session=session,
                role="assistant",
                content=debate_hint,
                agent_name=" debate"
            )
            return ChatReitsResponse(
                session_id=session.id,
                message_id=0,
                role="assistant",
                content=debate_hint,
                agent_name=" debate",
                sources=[],
            )

        # 兼容：同时尝试从数据库加载 agent 配置（温度等参数）
        agent = await AiChatAgent.filter(agent_name=req.agent_name, is_active=True).first()
        if not agent:
            agent = await AiChatAgent.filter(is_active=True).first()

        # 5. Retrieve sources (local vector search + fallback)
        rag_results = []
        try:
            rag_results = search_articles_for_rag(req.message, top_k=5)
        except (RuntimeError, ValueError, KeyError) as e:
            logger.warning(f"Vector search failed: {e}")

        # 6. Call LLM with persona + emotion + internal RAG context
        try:
            from openai import AsyncOpenAI
            base_url = settings.LLM_CONFIG["deepseek_pro"]["base_url"]
            if not base_url.endswith("/v1"):
                base_url = base_url.rstrip("/") + "/v1"
            import os
            api_key = os.getenv("DEEPSEEK_API_KEY", settings.LLM_CONFIG["deepseek_pro"]["api_key"])
            if not api_key:
                return JSONResponse({
                    "success": False,
                    "message": "AI 回复功能需要配置 DeepSeek API Key。请联系管理员设置 DEEPSEEK_API_KEY 环境变量后重启服务。"
                }, status_code=503)
            client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=30)

            # 内部RAG上下文（完整chunk，仅AI可见）
            internal_context = _build_internal_context(rag_results)

            # 通过人设路由器组装完整 Prompt（含情感注入、人格约束）
            prompt_pkg = persona_router.build_prompt(
                persona_cfg.name,
                req.message,
                internal_context,
                emotion_tag=emotion_tag,
            )

            # 基金上下文注入（投研页面问答用）
            fund_ctx_instruction = ""
            if req.fund_context:
                fund_ctx_instruction = (
                    f"\n\n【当前关注基金】用户正在分析以下 REITs：{req.fund_context}\n"
                    "请围绕这些基金回答用户问题，结合其基本面数据进行针对性分析。"
                )

            # 附加保密指令（双重保险）
            secrecy_instruction = (
                "\n\n【重要】回答时请注意："
                "1. 不要提及任何文章的具体标题（包括书名号《》内的内容）。"
                "2. 不要提及任何公众号名称或作者名称。"
                "3. 可以用'我们此前的深度研究'、'内部研究团队的分析'等模糊表述替代具体出处。"
                "4. 直接给出观点和结论，让用户感受到专业性，但不暴露信息来源。"
            )

            messages = [
                {"role": "system", "content": prompt_pkg["system_prompt"] + fund_ctx_instruction + secrecy_instruction},
                {"role": "user", "content": req.message}
            ]

            # 温度：优先使用人设配置，其次数据库配置，最后默认
            temperature = prompt_pkg["temperature"]
            if agent and agent.temperature is not None:
                temperature = agent.temperature

            response = await client.chat.completions.create(
                model=settings.LLM_CONFIG["deepseek_pro"]["model"],
                messages=messages,
                temperature=temperature,
                max_tokens=agent.max_tokens if agent else 2000
            )

            raw_answer = response.choices[0].message.content

            # 二次脱敏：后处理AI回答，确保没有漏网之鱼
            ai_content = _sanitize_citations(raw_answer)

            # 置信度判断（基于向量相似度）
            avg_score = sum(r.score for r in rag_results) / len(rag_results) if rag_results else 0
            confidence = "high" if avg_score > 0.75 else "medium" if avg_score > 0.6 else "low"

            # 使用的人设名称
            agent_display_name = persona_cfg.name_cn

        except (RuntimeError, ValueError, ConnectionError) as e:
            logger.error(f"LLM call failed: {e}")
            ai_content = "抱歉，AI服务暂时不可用，请稍后重试"
            confidence = "low"
            rag_results = []
            agent_display_name = req.agent_name or "AI助手"

        # 6. Save AI response
        ai_msg = await AiChatMessage.create(
            session=session,
            role="assistant",
            content=ai_content,
            model=getattr(agent, 'model', None) if agent else None
        )

        # 7. Build public sources (脱敏)
        public_sources = _build_public_sources(rag_results, confidence)

        # 8. Return response
        return ChatReitsResponse(
            session_id=session.id,
            message_id=ai_msg.id,
            role="assistant",
            content=ai_content,
            agent_name=agent_display_name,
            sources=public_sources
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("chat_reits error")
        raise HTTPException(status_code=500, detail="服务暂时不可用，请稍后重试")


@router.get("/agents")
async def get_agents():
    """Get all active AI agents"""
    try:
        await _ensure_db()
        from ai_db.models import AiChatAgent
        agents = await AiChatAgent.filter(is_active=True).all()
        return {
            "agents": [
                {
                    "id": a.id,
                    "agent_name": a.agent_name,
                    "agent_desc": a.agent_desc,
                    "system_prompt": a.system_prompt,
                    "model": a.model,
                    "temperature": a.temperature,
                    "max_tokens": a.max_tokens,
                }
                for a in agents
            ]
        }
    except Exception:
        logger.exception("get_agents error")
        raise HTTPException(status_code=500, detail="获取智能体列表失败，请稍后重试")


@router.get("/hotspots")
async def get_hotspots(limit: int = 20):
    """Get latest REITs hotspots from wechat_articles (fallback to SocialHotspot)"""
    try:
        from core.db import get_conn

        # PostgreSQL: query from business.wechat_articles
        conn = get_conn()
        cursor = conn.cursor()

        # Query REITs-related articles from wechat_articles
        # 先取足够多的文章，然后在 Python 中做标签多样性排序
        # 确保每种情感标签都有代表，避免全是"利好"
        cursor.execute("""
            SELECT id, title, link, published, sentiment_score, emotion_tag, event_tags
            FROM business.wechat_articles
            WHERE title ILIKE '%REIT%'
            ORDER BY published DESC
            LIMIT %s
        """, (limit * 3,))
        rows = cursor.fetchall()
        conn.close()

        if rows:
            from collections import defaultdict

            # 1. 先打标
            tagged = []
            for row in rows:
                sentiment = row[4] or 0
                heat = int((sentiment + 1) * 50)
                if sentiment >= 0.7:
                    tag = "利好"
                elif sentiment >= 0.3:
                    tag = "偏暖"
                elif sentiment <= -0.3:
                    tag = "利空"
                else:
                    tag = "中性"
                tagged.append({
                    "id": row[0],
                    "source": tag,
                    "title": row[1],
                    "content": str(heat),
                    "url": row[2],
                    "author": None,
                    "publish_time": row[3],
                    "sentiment_score": sentiment,
                    "entity_tags": row[6],
                    "created_at": row[3],
                })

            # 2. 按标签分组，确保多样性
            by_tag = defaultdict(list)
            for h in tagged:
                by_tag[h["source"]].append(h)

            # 3. 轮询取文：每种标签轮流取 1 条，直到凑够 limit
            # 这样前 N 条会有红/橙/绿/灰多种颜色
            tags_order = ["利空", "偏暖", "中性", "利好"]
            result = []
            idx = {t: 0 for t in tags_order}
            while len(result) < limit:
                added = False
                for t in tags_order:
                    if idx[t] < len(by_tag[t]):
                        result.append(by_tag[t][idx[t]])
                        idx[t] += 1
                        added = True
                        if len(result) >= limit:
                            break
                if not added:
                    break

            # 4. 如果轮询后还不够，用剩余文章补足（按时间）
            used_ids = {h["id"] for h in result}
            remain = [h for h in tagged if h["id"] not in used_ids]
            remain.sort(key=lambda x: x["publish_time"] or "", reverse=True)
            result.extend(remain[:limit - len(result)])

            return {"hotspots": result}

        # Fallback to SocialHotspot if no REITs articles found
        await _ensure_db()
        from ai_db.models import SocialHotspot
        items = await SocialHotspot.all().order_by("-created_at").limit(limit)
        return {
            "hotspots": [
                {
                    "id": h.id,
                    "source": h.source,
                    "title": h.title,
                    "content": h.content,
                    "url": h.url,
                    "author": h.author,
                    "publish_time": str(h.publish_time) if h.publish_time else None,
                    "sentiment_score": h.sentiment_score,
                    "entity_tags": h.entity_tags,
                    "created_at": str(h.created_at) if h.created_at else None,
                }
                for h in items
            ]
        }
    except Exception:
        logger.exception("get_hotspots error")
        raise HTTPException(status_code=500, detail="获取热点失败，请稍后重试")
