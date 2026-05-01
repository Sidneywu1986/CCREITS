#!/usr/bin/env python3
"""
Agent 适配层 —— 连接 SupervisorStateMachine 和 ws_chat 系统
提供：AgentWrapper、AgentMessage、broadcast_adapter
"""

import os
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime

from agents.persona_router import get_persona_router
from api.search import search_articles_for_rag
from core.config import settings
from openai import AsyncOpenAI

logger = logging.getLogger("agent_adapter")

# ============================================
# 模块级变量：流式输出目标 + RoomManager 引用
# ============================================
_current_stream_session_id: Optional[str] = None
_room_manager_ref = None


def set_stream_target(session_id: Optional[str]):
    global _current_stream_session_id
    _current_stream_session_id = session_id


def get_stream_target() -> Optional[str]:
    return _current_stream_session_id


def set_room_manager(room_manager):
    global _room_manager_ref
    _room_manager_ref = room_manager


# ============================================
# AgentMessage —— Supervisor 期望的 generate 返回值
# ============================================
@dataclass
class AgentMessage:
    content: str
    citations: List = field(default_factory=list)
    reply_to: Optional[str] = None
    agent_name: str = ""


# ============================================
# RoomSession —— 房间级共享会话（替代 per-WebSocket ChatSession）
# ============================================
class RoomSession:
    def __init__(self):
        self.persona_router = get_persona_router()
        self.messages: List[dict] = []

    def add_message(self, role: str, content: str, persona: str = ""):
        self.messages.append({"role": role, "content": content, "persona": persona})
        if len(self.messages) > 100:
            self.messages = self.messages[-80:]

    def get_context(self, limit: int = 4) -> str:
        recent = self.messages[-limit:]
        lines = []
        for m in recent:
            role_label = "用户" if m["role"] == "user" else m.get("persona", "AI")
            lines.append(f"{role_label}: {m['content'][:200]}")
        return "\n".join(lines)


# 全局单例
_room_session: Optional[RoomSession] = None


def get_room_session() -> RoomSession:
    global _room_session
    if _room_session is None:
        _room_session = RoomSession()
    return _room_session


# ============================================
# AgentWrapper —— 包装 LLM 调用为 Supervisor 期望接口
# ============================================
class AgentWrapper:
    """将 LLM 调用包装为 Supervisor 期望的 .generate(context) 接口"""

    def __init__(self, persona_id: str):
        self.persona_id = persona_id
        self.session = get_room_session()

    def _build_prompt(self, query: str, emotion_tag: str = "neutral", beat_type: str = "") -> tuple:
        """构建 LLM prompt，返回 (messages, temperature, rag_results, persona_name)"""
        # RAG 检索
        rag_results = []
        try:
            rag_results = search_articles_for_rag(query, top_k=5)
        except (RuntimeError, ValueError, KeyError) as e:
            logger.warning(f"RAG failed: {e}")

        rag_context = ""
        if rag_results:
            lines = [f"[内部研究-{i+1}] {r.chunk_text[:350]}" for i, r in enumerate(rag_results[:5])]
            rag_context = "\n\n参考信息（内部研究资料）：\n" + "\n\n".join(lines)

        # 人设 Prompt
        prompt_pkg = self.session.persona_router.build_prompt(
            self.persona_id, query, rag_context, emotion_tag=emotion_tag
        )

        # 历史
        history = self.session.get_context(limit=4)

        # 节拍指令
        beat_instruction = ""
        if beat_type:
            from agents.session_director import SessionDirector
            sd = SessionDirector([])
            beat_instruction = sd.get_beat_instruction(beat_type)

        # 保密指令
        secrecy = (
            "\n\n【重要】回答时请注意："
            "1. 不要提及任何文章的具体标题（包括书名号《》内的内容）。"
            "2. 不要提及任何公众号名称或作者名称。"
            "3. 可以用'我们此前的深度研究'、'内部研究团队的分析'等模糊表述替代具体出处。"
        )

        system_prompt = prompt_pkg["system_prompt"] + secrecy
        if beat_instruction:
            system_prompt += f"\n\n【本轮任务】{beat_instruction}"
        if history:
            system_prompt += f"\n\n【对话历史】\n{history}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]

        return messages, prompt_pkg["temperature"], rag_results, prompt_pkg.get("persona_name", "AI助手")

    async def generate(self, context: dict) -> AgentMessage:
        """Supervisor 期望的接口：生成回复"""
        topic = context.get("topic", "")
        emotion = context.get("emotion", "neutral")
        beat_instruction = context.get("beat_instruction", "")
        duet_instruction = context.get("duet_instruction", "")
        instruction = context.get("instruction", "")

        # 合并特殊指令到 query
        query = topic
        special = duet_instruction or instruction
        if special:
            query = f"{special}\n\n{query}"

        # 获取流式目标 session
        stream_target = get_stream_target()

        # 构建 prompt
        messages, temperature, rag_results, persona_name = self._build_prompt(query, emotion, beat_instruction)

        # 调用 LLM
        try:
            base_url = settings.LLM_CONFIG["deepseek_pro"]["base_url"]
            if not base_url.endswith("/v1"):
                base_url = base_url.rstrip("/") + "/v1"
            api_key = os.getenv("DEEPSEEK_API_KEY", settings.LLM_CONFIG["deepseek_pro"]["api_key"])

            if not api_key:
                return AgentMessage(
                    content="【系统提示】AI 回复功能需要配置 DeepSeek API Key。请联系管理员设置 DEEPSEEK_API_KEY 环境变量后重启服务。",
                    citations=[],
                )

            client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=30)
            full_content = ""

            if stream_target and _room_manager_ref:
                # ========== 流式模式：给提问者实时输出 ==========
                response = await client.chat.completions.create(
                    model=settings.LLM_CONFIG["deepseek_pro"]["model"],
                    messages=messages,
                    temperature=temperature,
                    max_tokens=1024,
                    stream=True,
                )

                # 发送 message_start
                await _room_manager_ref.send_to(stream_target, {
                    "type": "message_start",
                    "persona": persona_name,
                    "persona_id": self.persona_id,
                })

                # 流式输出
                async for chunk in response:
                    delta = chunk.choices[0].delta.content or ""
                    if delta:
                        full_content += delta
                        await _room_manager_ref.send_to(stream_target, {
                            "type": "message_chunk",
                            "chunk": delta,
                        })

                # 发送 message_end
                await _room_manager_ref.send_to(stream_target, {
                    "type": "message_end",
                    "content": full_content,
                    "persona": persona_name,
                    "persona_id": self.persona_id,
                    "sources": [{"type": "internal_research", "description": "基于内部研究资料", "count": len(rag_results)}],
                    "confidence": "medium",
                })
            else:
                # ========== 非流式模式 ==========
                response = await client.chat.completions.create(
                    model=settings.LLM_CONFIG["deepseek_pro"]["model"],
                    messages=messages,
                    temperature=temperature,
                    max_tokens=1024,
                    stream=False,
                )
                full_content = response.choices[0].message.content

            # 保存到房间历史
            self.session.add_message("assistant", full_content, persona_name)

            return AgentMessage(
                content=full_content,
                citations=[{"type": "internal_research", "description": "基于内部研究资料", "count": len(rag_results)}],
            )

        except (RuntimeError, ValueError, ConnectionError) as e:
            logger.error(f"AgentWrapper.generate failed for {self.persona_id}: {e}")
            return AgentMessage(
                content="抱歉，AI服务暂时不可用，请稍后重试",
                citations=[],
            )


# ============================================
# Broadcast Adapter —— 翻译 Supervisor 消息格式 → 前端兼容格式
# ============================================
async def broadcast_adapter(message: dict):
    """适配 Supervisor 的单参数广播 → RoomManager 的三参数广播"""
    if _room_manager_ref is None:
        logger.error("RoomManager not set, cannot broadcast")
        return

    msg_type = message.get("type", "")
    payload = message.get("payload", {})
    exclude = get_stream_target()
    translated = None

    if msg_type == "AI_DIALOGUE":
        agent_id = payload.get("agent", "")
        registry = get_persona_router().registry
        persona_cfg = registry.get(agent_id)
        persona_name = persona_cfg.name_cn if persona_cfg else agent_id
        translated = {
            "type": "ai_message",
            "persona_id": agent_id,
            "persona": persona_name,
            "content": payload.get("content", ""),
            "sources": payload.get("citations", []),
            "confidence": "medium",
            "timestamp": datetime.now().isoformat(),
        }
        # 第一条 AI 消息广播后，清除流式目标（提问者已通过流式看到内容）
        set_stream_target(None)

    elif msg_type == "GUEST_FLASH":
        agent_id = payload.get("agent", "")
        registry = get_persona_router().registry
        persona_cfg = registry.get(agent_id)
        persona_name = persona_cfg.name_cn if persona_cfg else agent_id
        translated = {
            "type": "guest_message",
            "persona_id": agent_id,
            "persona": persona_name,
            "content": payload.get("content", ""),
            "guest_type": "guest_compliance" if agent_id == "police" else "guest_gossip",
            "sources": payload.get("citations", []),
            "timestamp": datetime.now().isoformat(),
        }

    elif msg_type == "SYSTEM_NOTICE":
        translated = {
            "type": "system",
            "content": payload.get("notice", ""),
            "timestamp": datetime.now().isoformat(),
        }

    elif msg_type == "DEBATE_RESULT":
        translated = message  # 前端已兼容

    elif msg_type == "QUICK_DEBATE":
        translated = message  # 前端已兼容

    elif msg_type == "MODE_CHANGE":
        translated = message

    else:
        translated = message

    if translated:
        await _room_manager_ref.broadcast("reits-lobby", translated, exclude_session=exclude)
        _room_manager_ref.add_history("reits-lobby", translated)

        # 同步更新侧边栏状态
        await _sync_sidebar_state(msg_type, payload, translated)


async def _sync_sidebar_state(msg_type: str, payload: dict, translated: dict):
    """广播 AI 消息后，同步更新侧边栏状态（话题进度、立场、情绪）"""
    if _room_manager_ref is None:
        return

    state = _room_manager_ref.get_room_state("reits-lobby")

    # 更新话题轮次
    if msg_type in ("AI_DIALOGUE", "GUEST_FLASH"):
        current_round = state.get("current_round", 1) + 1
        _room_manager_ref.update_room_state("reits-lobby", "current_round", current_round)
        agent_id = payload.get("agent", "")
        registry = get_persona_router().registry
        persona_cfg = registry.get(agent_id)
        persona_name = persona_cfg.name_cn if persona_cfg else agent_id
        _room_manager_ref.update_room_state("reits-lobby", "topic_desc", f"{persona_name} 正在分析...")

        await _room_manager_ref.broadcast("reits-lobby", {
            "type": "topic_update",
            "current_round": current_round,
            "max_rounds": state.get("max_rounds", 6),
            "current_topic": state.get("current_topic", "REITs市场热点"),
            "topic_desc": state.get("topic_desc", ""),
            "topic_queue": state.get("topic_queue", []),
        })

    # 更新立场（简单规则：根据内容关键词判断）
    if msg_type == "AI_DIALOGUE" and payload.get("agent") in ("lao_k", "su_su", "lao_li", "xiao_chen", "wang_bo"):
        content = payload.get("content", "").lower()
        agent_id = payload.get("agent", "")
        name_map = {"lao_k": "老K", "su_su": "苏苏", "lao_li": "老李", "xiao_chen": "小陈", "wang_bo": "王博"}
        name = name_map.get(agent_id, agent_id)
        stances = state.get("stances", {})

        if name in stances:
            if any(w in content for w in ["看空", "看跌", "风险", "泡沫", "虚高", "跌"]):
                stances[name]["stance"] = "bearish"
            elif any(w in content for w in ["看多", "看涨", "机会", "底部", "价值", "涨"]):
                stances[name]["stance"] = "bullish"
            elif any(w in content for w in ["谨慎", "观望", "不确定"]):
                stances[name]["stance"] = "cautious"
            else:
                stances[name]["stance"] = "neutral"

            _room_manager_ref.update_room_state("reits-lobby", "stances", stances)
            await _room_manager_ref.broadcast("reits-lobby", {
                "type": "stance_sync",
                "stances": stances,
            })
