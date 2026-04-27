#!/usr/bin/env python3
"""
WebSocket 直播间模式 —— 统一内容广播
所有用户在同一房间(reits-lobby)，看到完全相同的AI对话流
支持：流式输出(个人体验)、全员广播、历史同步、导演续场、自动开场、辩论
"""

import os
import re
import json
import logging
import random
import asyncio
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Dict, Optional, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from core.db import get_conn

from api.search import search_articles_for_rag
from engine.sentiment import get_sentiment_engine
from agents.persona_router import get_persona_router
from agents.session_director import SessionDirector, DialogueBeat
from agents.supervisor import GuestDispatcher, GuestTrigger
from agents.debate_manager import DebateManager, get_debate_manager
from agents.show_schedule import get_schedule
from agents.user_quota import get_quota_manager
from agents.butterfly_effect import get_butterfly_trigger
from agents.lunch_whisper import get_lunch_whisper
from agents.morning_news import get_morning_engine

router = APIRouter(tags=["WebSocket聊天"])
logger = logging.getLogger(__name__)

# ============================================
# Room Manager —— 房间广播 + 历史消息
# ============================================

DEFAULT_ROOM = "reits-lobby"
MAX_HISTORY = 50


class RoomManager:
    """房间管理器：管理连接、广播消息、维护历史 + 直播间共享状态"""

    def __init__(self):
        # room_id -> {session_id: WebSocket}
        self.rooms: Dict[str, Dict[str, WebSocket]] = {}
        # room_id -> [messages]
        self.history: Dict[str, List[dict]] = {}
        # session_id -> room_id 映射，方便断线清理
        self.session_rooms: Dict[str, str] = {}
        # 昵称池
        self._nicknames = set()
        # ========== 直播间共享状态 ==========
        self.room_state: Dict[str, dict] = {}

    def _init_room_state(self, room_id: str):
        """初始化直播间状态（话题队列、竞猜、轮次）"""
        if room_id not in self.room_state:
            self.room_state[room_id] = {
                "current_topic": "REITs市场热点",
                "current_round": 1,
                "max_rounds": 6,
                "topic_desc": "等待专家切入话题...",
                "topic_queue": [
                    {"id": 1, "title": "华夏高速车流量", "votes": 0, "active": True},
                    {"id": 2, "title": "盐田港扩募定价", "votes": 0, "active": False},
                    {"id": 3, "title": "京东仓储双11", "votes": 0, "active": False},
                ],
                "quiz": {"up": 0, "down": 0, "total": 0},
                "auto_opened": False,
                "stances": {
                    "老K": {"stance": "bearish", "quote": '"虚高，有水分"'},
                    "苏苏": {"stance": "neutral", "quote": '"春天到了暖和正常"'},
                    "老李": {"stance": "bullish", "quote": '"数据支撑，长期看好"'},
                    "小陈": {"stance": "neutral", "quote": '"短期波动，等等看"'},
                    "王博": {"stance": "cautious", "quote": '"模型显示中性偏谨慎"'},
                },
            }

    def get_room_state(self, room_id: str) -> dict:
        self._init_room_state(room_id)
        return self.room_state[room_id]

    def update_room_state(self, room_id: str, key: str, value):
        self._init_room_state(room_id)
        self.room_state[room_id][key] = value

    def vote_topic(self, room_id: str, topic_id: int) -> bool:
        self._init_room_state(room_id)
        for t in self.room_state[room_id]["topic_queue"]:
            if t["id"] == topic_id:
                t["votes"] += 1
                return True
        return False

    def vote_quiz(self, room_id: str, val: str):
        self._init_room_state(room_id)
        quiz = self.room_state[room_id]["quiz"]
        if val in quiz:
            quiz[val] += 1
            quiz["total"] += 1

    def update_stance(self, room_id: str, agent_name: str, stance: str, quote: str = ""):
        self._init_room_state(room_id)
        if agent_name in self.room_state[room_id]["stances"]:
            self.room_state[room_id]["stances"][agent_name]["stance"] = stance
            if quote:
                self.room_state[room_id]["stances"][agent_name]["quote"] = quote

    def _gen_nickname(self) -> str:
        """生成匿名观众昵称"""
        adjectives = ["热情的", "好奇的", "专注的", "沉稳的", "敏锐的", "乐观的", "谨慎的"]
        nouns = ["投资者", "观察者", "研究员", "分析师", "听众", "网友"]
        for _ in range(100):
            name = f"{random.choice(adjectives)}{random.choice(nouns)}{random.randint(1, 999)}"
            if name not in self._nicknames:
                self._nicknames.add(name)
                return name
        return f"观众{random.randint(1000, 9999)}"

    async def join(self, room_id: str, session_id: str, ws: WebSocket) -> str:
        """加入房间，返回分配的昵称"""
        if room_id not in self.rooms:
            self.rooms[room_id] = {}
            self.history[room_id] = []
        self.rooms[room_id][session_id] = ws
        self.session_rooms[session_id] = room_id
        nickname = self._gen_nickname()
        self._init_room_state(room_id)
        logger.info(f"[{room_id}] {session_id} joined as {nickname}, total={len(self.rooms[room_id])}")
        return nickname

    async def leave(self, session_id: str):
        """离开房间"""
        room_id = self.session_rooms.pop(session_id, None)
        if room_id and room_id in self.rooms:
            self.rooms[room_id].pop(session_id, None)
            if not self.rooms[room_id]:
                del self.rooms[room_id]
                # 保留历史，不删除
        logger.info(f"[{room_id}] {session_id} left")

    async def broadcast(self, room_id: str, message: dict, exclude_session: Optional[str] = None):
        """广播消息给房间内所有人（可选排除某session）"""
        if room_id not in self.rooms:
            return
        payload = json.dumps(message, ensure_ascii=False, default=str)
        dead = []
        targets = []
        for sid, ws in self.rooms[room_id].items():
            if exclude_session and sid == exclude_session:
                continue
            targets.append((sid, ws))
        if not targets:
            return
        tasks = []
        for sid, ws in targets:
            try:
                tasks.append(ws.send_text(payload))
            except Exception:
                dead.append(sid)
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for (sid, ws), result in zip(targets, results):
                if isinstance(result, Exception):
                    dead.append(sid)
        for sid in set(dead):
            self.rooms[room_id].pop(sid, None)
            self.session_rooms.pop(sid, None)

    async def send_to(self, session_id: str, message: dict):
        """单发给某个session（用于个人流式体验）"""
        room_id = self.session_rooms.get(session_id)
        if not room_id or room_id not in self.rooms:
            return
        ws = self.rooms[room_id].get(session_id)
        if not ws:
            return
        try:
            await ws.send_json(message)
        except Exception as e:
            logger.warning(f"Send to {session_id} failed: {e}")

    def add_history(self, room_id: str, message: dict):
        """添加消息到历史"""
        if room_id not in self.history:
            self.history[room_id] = []
        self.history[room_id].append(message)
        if len(self.history[room_id]) > MAX_HISTORY:
            self.history[room_id] = self.history[room_id][-MAX_HISTORY:]

    def get_history(self, room_id: str, limit: int = 20) -> List[dict]:
        """获取最近N条历史"""
        hist = self.history.get(room_id, [])
        return hist[-limit:] if len(hist) > limit else hist.copy()


room_manager = RoomManager()
show_schedule = get_schedule()
quota_manager = get_quota_manager()
butterfly_trigger = get_butterfly_trigger()


# ============================================
# 单会话状态（保留，用于流式输出给提问者）
# ============================================

class ChatSession:
    """WebSocket 聊天会话状态（个人维度）"""

    def __init__(self, session_id: str, websocket: WebSocket, nickname: str):
        self.session_id = session_id
        self.ws = websocket
        self.nickname = nickname
        self.messages: List[dict] = []  # 对话历史（用于LLM上下文）
        self.round_count = 0
        self.current_persona = "lao_k"
        self.director = SessionDirector(["lao_k", "su_su", "lao_li", "xiao_chen", "wang_bo"])
        self.sentiment_engine = get_sentiment_engine()
        self.persona_router = get_persona_router()
        self.guest_dispatcher = GuestDispatcher(self.persona_router)
        # Duet 对戏状态
        self.duet_mode = False
        self.duet_stage = 0   # 0=无 1=质问 2=接招 3=再追 4=收尾
        self.duet_round = 0
        self.duet_max_rounds = 2

    def add_message(self, role: str, content: str, persona: str = ""):
        self.messages.append({"role": role, "content": content, "persona": persona})

    def get_context(self, limit: int = 6) -> str:
        """获取最近N条对话作为上下文"""
        recent = self.messages[-limit:]
        lines = []
        for m in recent:
            name = m.get("persona", m["role"])
            lines.append(f"{name}: {m['content']}")
        return "\n".join(lines)


# ============================================
# 基金代码检测与数据库查询
# ============================================

def _extract_fund_code(query: str) -> Optional[str]:
    """从用户查询中提取6位基金代码"""
    match = re.search(r'(?<!\d)(\d{6})(?!\d)', query)
    return match.group(1) if match else None


def _query_fund_info(fund_code: str) -> dict:
    """从数据库查询基金基本信息和近期价格"""
pg_dsn = "host=localhost dbname=ai_db user=postgres password=postgres"

def get_pg_conn():
    """PostgreSQL connection for ai_db"""
    conn = psycopg2.connect(pg_dsn)
    return conn
    result = {"found": False, "basic": "", "prices": "", "sector": ""}
    try:
        conn = get_conn()
        cur = conn.cursor()

        # 1. 基本信息
        cur.execute("""
            SELECT fund_code, fund_name, sector_name, property_type,
                   scale, market_cap, dividend_yield, debt_ratio, premium_rate
            FROM business.funds WHERE fund_code = %s
        """, (fund_code,))
        row = cur.fetchone()
        if row:
            result["found"] = True
            result["sector"] = row["sector_name"] or row["property_type"] or "未知"
            result["basic"] = (
                f"基金代码：{row['fund_code']} | 名称：{row['fund_name']} | "
                f"类型：{result['sector']} | 规模：{row['scale']}亿 | "
                f"市值：{row['market_cap']}亿 | 分红率：{row['dividend_yield']}% | "
                f"负债率：{row['debt_ratio']}% | 溢价率：{row['premium_rate']}%"
            )

        # 2. 最近5日价格（含开盘/最高/最低/收盘）
        cur.execute("""
            SELECT trade_date, open_price, high_price, low_price, close_price, change_pct, volume
            FROM fund_prices
            WHERE fund_code = %s
            ORDER BY trade_date DESC
            LIMIT 5
        """, (fund_code,))
        rows = cur.fetchall()
        if rows:
            lines = ["最近交易日数据（含开盘价）："]
            for r in rows:
                change = r["change_pct"]
                change_str = f"+{change:.2f}%" if change and change > 0 else f"{change:.2f}%" if change else "N/A"
                lines.append(
                    f"  {r['trade_date']} 开盘{r['open_price']} 最高{r['high_price']} "
                    f"最低{r['low_price']} 收盘{r['close_price']} 涨跌幅{change_str} 成交量{r['volume']}"
                )
            result["prices"] = "\n".join(lines)

        conn.close()
    except Exception as e:
        logger.warning(f"基金数据库查询失败: {e}")
    return result


def _is_market_overview_query(query: str) -> bool:
    """检测用户是否在询问市场概况/总数/分类"""
    q = query.lower()
    # 数量类关键词
    count_keywords = ["多少只", "几只", "总数", "数量", "有多少", "一共", "共多少", "市场有几只"]
    # 概况类关键词
    overview_keywords = ["概况", "整体", "市场情况", "市场现状", "行业现状", "分类", "类型分布", "哪些类型"]
    has_reit = "reit" in q or "REIT" in query
    return has_reit and (any(k in q for k in count_keywords) or any(k in q for k in overview_keywords))


def _query_market_overview() -> str:
    """查询市场整体概况：总数、分类、规模"""
    try:
        conn = get_conn()
        cur = conn.cursor()

        # 1. 总数
        cur.execute("SELECT COUNT(*) as total FROM business.funds")
        total = cur.fetchone()["total"]

        # 2. 分类统计
        cur.execute("""
            SELECT sector_name, COUNT(*) as cnt,
                   ROUND(AVG(COALESCE(scale, 0)), 1) as avg_scale,
                   ROUND(AVG(COALESCE(market_cap, 0)), 1) as avg_cap
            FROM business.funds
            WHERE sector_name IS NOT NULL AND sector_name != ''
            GROUP BY sector_name
            ORDER BY cnt DESC
        """)
        sectors = cur.fetchall()

        # 3. 总规模/总市值
        cur.execute("""
            SELECT ROUND(SUM(COALESCE(scale, 0)), 1) as total_scale,
                   ROUND(SUM(COALESCE(market_cap, 0)), 1) as total_cap
            FROM business.funds
        """)
        totals = cur.fetchone()

        # 4. 最近5只（按fund_code倒序，假设新基金code更大）
        cur.execute("""
            SELECT fund_code, fund_name, sector_name, scale, market_cap
            FROM business.funds
            ORDER BY fund_code DESC
            LIMIT 5
        """)
        recent = cur.fetchall()

        conn.close()

        lines = [
            f"【数据库实时数据 —— REITs市场整体概况】",
            f"",
            f"市场总数：{total}只",
            f"合计规模：{totals['total_scale']}亿元",
            f"合计市值：{totals['total_cap']}亿元",
            f"",
            f"分类分布：",
        ]
        for s in sectors:
            lines.append(f"  {s['sector_name']}：{s['cnt']}只，平均规模{s['avg_scale']}亿")

        lines.extend([
            f"",
            f"最近5只基金：",
        ])
        for r in recent:
            lines.append(f"  {r['fund_code']} {r['fund_name']}（{r['sector_name']}，规模{r['scale']}亿）")

        lines.extend([
            f"",
            f"⚠️ 重要：以上数据来自数据库实时统计，你的回答必须基于这些事实数据，"
            f"不得使用训练数据中的过时数字。当前市场共有【{total}只】REITs基金。"
        ])

        return "\n".join(lines)

    except Exception as e:
        logger.warning(f"市场概况查询失败: {e}")
        return "【数据库查询】市场概况数据暂时不可用，请基于公开信息谨慎回答。"


# ============================================
# AI 回复生成
# ============================================

def _build_llm_context(session: ChatSession, query: str, persona_id: str, emotion_tag: str, beat_type: str = ""):
    """构建 LLM 调用所需的上下文，返回 (messages, temperature, rag_results, persona_name)"""
    # ===== 结构化数据查询：基金代码 或 市场概况 =====
    structured_context = ""

    # 1. 基金代码查询
    fund_code = _extract_fund_code(query)
    if fund_code:
        fund_info = _query_fund_info(fund_code)
        if fund_info["found"]:
            structured_context = (
                f"\n\n【数据库实时数据 —— 基金 {fund_code}】\n"
                f"{fund_info['basic']}\n"
                f"{fund_info['prices']}\n"
                f"\n⚠️ 重要：以上数据来自数据库，你的回答必须基于这些事实数据，"
                f"不得凭空猜测基金类型或属性。该基金属于【{fund_info['sector']}】类别。"
            )
        else:
            structured_context = f"\n\n【数据库查询】未找到基金 {fund_code} 的详细数据，请基于公开信息谨慎回答。"

    # 2. 市场概况查询（总数/分类/规模）
    elif _is_market_overview_query(query):
        structured_context = "\n\n" + _query_market_overview()

    # RAG 检索（文章向量搜索）
    rag_results = []
    try:
        rag_results = search_articles_for_rag(query, top_k=5, fund_code=fund_code)
    except Exception as e:
        logger.warning(f"RAG failed: {e}")

    # 构建 RAG 上下文
    rag_context = ""
    if rag_results:
        lines = []
        for i, r in enumerate(rag_results[:5]):
            lines.append(f"[内部研究-{i+1}] {r.chunk_text[:350]}")
        rag_context = "\n\n参考信息（内部研究资料）：\n" + "\n\n".join(lines)

    # 人设 Prompt 组装
    prompt_pkg = session.persona_router.build_prompt(
        persona_id, query, rag_context + structured_context, emotion_tag=emotion_tag
    )

    # 会话历史上下文
    history_context = session.get_context(limit=4)

    # 导演节拍指令
    beat_instruction = session.director.get_beat_instruction(beat_type) if beat_type else ""

    # 保密指令
    secrecy = (
        "\n\n【重要】回答时请注意："
        "1. 不要提及任何文章的具体标题（包括书名号《》内的内容）。"
        "2. 不要提及任何公众号名称或作者名称。"
        "3. 可以用'我们此前的深度研究'、'内部研究团队的分析'等模糊表述替代具体出处。"
    )

    # 系统提示词
    system_prompt = prompt_pkg["system_prompt"] + secrecy
    if beat_instruction:
        system_prompt += f"\n\n【本轮任务】{beat_instruction}"
    if history_context:
        system_prompt += f"\n\n【对话历史】\n{history_context}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query},
    ]
    return messages, prompt_pkg["temperature"], rag_results, prompt_pkg.get("persona_name", "AI助手")


def _sanitize_answer(raw_answer: str) -> str:
    """脱敏处理"""
    import re
    answer = re.sub(r'《[^》]+》', '相关研究', raw_answer)
    answer = re.sub(r'(?:公众号|微信号|专栏)[""\s]*[^\s，。]{2,20}[""\s]*', '内部研究', answer)
    answer = re.sub(r'\d{4}年\d{1,2}月[^\s，。]{2,15}(?:分析|报告|研报|点评)', '此前分析', answer)
    return answer


def _calc_confidence(rag_results):
    avg_score = sum(r.score for r in rag_results) / len(rag_results) if rag_results else 0
    return "high" if avg_score > 0.75 else "medium" if avg_score > 0.6 else "low"


async def generate_response(
    session: ChatSession,
    query: str,
    persona_id: str,
    emotion_tag: str,
    beat_type: str = "",
) -> dict:
    """
    生成单轮 AI 回答（非流式，用于嘉宾/续场）
    返回: {"content": str, "persona": str, "sources": list, "confidence": str}
    """
    from core.config import settings
    from openai import AsyncOpenAI
    import time

    messages, temperature, rag_results, persona_name = _build_llm_context(session, query, persona_id, emotion_tag, beat_type)

    try:
        base_url = settings.LLM_CONFIG["deepseek_pro"]["base_url"]
        if not base_url.endswith("/v1"):
            base_url = base_url.rstrip("/") + "/v1"
        api_key = os.getenv("DEEPSEEK_API_KEY", settings.LLM_CONFIG["deepseek_pro"]["api_key"])
        if not api_key:
            logger.warning("DEEPSEEK_API_KEY not set, returning config hint")
            return {
                "content": "【系统提示】AI 回复功能需要配置 DeepSeek API Key。请联系管理员设置 DEEPSEEK_API_KEY 环境变量后重启服务。",
                "persona": persona_name,
                "sources": [],
                "confidence": "low",
            }
        client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=30)

        t0 = time.time()
        response = await client.chat.completions.create(
            model=settings.LLM_CONFIG["deepseek_pro"]["model"],
            messages=messages,
            temperature=temperature,
            max_tokens=1024,
            stream=False,
        )
        latency = time.time() - t0
        logger.info(f"[{persona_id}] LLM latency: {latency:.2f}s, tokens: {response.usage.completion_tokens if response.usage else 'N/A'}")

        raw_answer = response.choices[0].message.content
        answer = _sanitize_answer(raw_answer)
        confidence = _calc_confidence(rag_results)

        return {
            "content": answer,
            "persona": persona_name,
            "sources": [{
                "type": "internal_research",
                "confidence": confidence,
                "description": "基于内部研究资料",
                "count": len(rag_results),
            }],
            "confidence": confidence,
        }

    except Exception as e:
        logger.error(f"LLM failed: {e}")
        return {
            "content": f"抱歉，AI服务暂时不可用: {str(e)}",
            "persona": persona_name,
            "sources": [],
            "confidence": "low",
        }


async def generate_response_stream(
    session: ChatSession,
    query: str,
    persona_id: str,
    emotion_tag: str,
    beat_type: str = "",
):
    """
    流式生成 AI 回答（async generator）
    yield {"type": "chunk"/"done"/"error", ...}
    """
    from core.config import settings
    from openai import AsyncOpenAI
    import time

    messages, temperature, rag_results, persona_name = _build_llm_context(session, query, persona_id, emotion_tag, beat_type)

    try:
        base_url = settings.LLM_CONFIG["deepseek_pro"]["base_url"]
        if not base_url.endswith("/v1"):
            base_url = base_url.rstrip("/") + "/v1"
        api_key = os.getenv("DEEPSEEK_API_KEY", settings.LLM_CONFIG["deepseek_pro"]["api_key"])
        if not api_key:
            yield {"type": "error", "content": "API Key 未配置"}
            return
        client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=30)

        t0 = time.time()
        response = await client.chat.completions.create(
            model=settings.LLM_CONFIG["deepseek_pro"]["model"],
            messages=messages,
            temperature=temperature,
            max_tokens=1024,
            stream=True,
        )

        full_content = ""
        async for chunk in response:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                full_content += delta
                yield {"type": "chunk", "chunk": delta}

        latency = time.time() - t0
        logger.info(f"[{persona_id}] stream LLM latency: {latency:.2f}s")

        answer = _sanitize_answer(full_content)
        confidence = _calc_confidence(rag_results)
        yield {
            "type": "done",
            "content": answer,
            "persona": persona_name,
            "sources": [{
                "type": "internal_research",
                "confidence": confidence,
                "description": "基于内部研究资料",
                "count": len(rag_results),
            }],
            "confidence": confidence,
        }

    except Exception as e:
        logger.error(f"Stream LLM failed: {e}")
        yield {"type": "error", "content": f"抱歉，AI服务暂时不可用: {str(e)}", "persona": persona_name}


# ============================================
# 嘉宾闪现 + 补充回答
# ============================================

async def _send_guest_flash(
    session: ChatSession,
    session_id: str,
    query: str,
    trigger: GuestTrigger,
    emotion_tag: str,
    chunk_size: int = 80,
):
    """飞行嘉宾闪现发言：流式给提问者 + 广播给全员"""
    guest_cfg = session.persona_router.get_guest(trigger.guest_id)
    if not guest_cfg:
        return

    # 激活嘉宾
    session.guest_dispatcher.activate_guest(trigger)

    # 广播嘉宾出场提示
    await room_manager.broadcast(DEFAULT_ROOM, {
        "type": "guest_flash",
        "guest_id": trigger.guest_id,
        "guest_name": guest_cfg.name_cn,
        "reason": trigger.reason,
        "timestamp": datetime.now().isoformat(),
    })

    # 生成嘉宾回复
    guest_result = await generate_response(
        session, query, trigger.guest_id, emotion_tag, beat_type="guest_flash"
    )

    # 个人流式给提问者
    gc = guest_result["content"]
    await room_manager.send_to(session_id, {
        "type": "message_start",
        "persona": guest_result["persona"],
        "persona_id": trigger.guest_id,
    })
    for i in range(0, len(gc), chunk_size):
        await room_manager.send_to(session_id, {
            "type": "message_chunk",
            "chunk": gc[i:i + chunk_size],
        })
    await room_manager.send_to(session_id, {
        "type": "message_end",
        "content": gc,
        "persona": guest_result["persona"],
        "persona_id": trigger.guest_id,
        "sources": guest_result.get("sources", []),
        "confidence": guest_result.get("confidence", "low"),
    })

    # 广播完整嘉宾消息给全员（排除提问者，提问者已通过流式看到）
    guest_msg = {
        "type": "guest_message",
        "persona": guest_result["persona"],
        "persona_id": trigger.guest_id,
        "content": gc,
        "guest_type": "guest_compliance" if trigger.guest_id == "police" else "guest_gossip",
        "sources": guest_result.get("sources", []),
        "confidence": guest_result.get("confidence", "low"),
        "timestamp": datetime.now().isoformat(),
    }
    await room_manager.broadcast(DEFAULT_ROOM, guest_msg, exclude_session=session_id)
    room_manager.add_history(DEFAULT_ROOM, guest_msg)
    session.add_message("assistant", gc, guest_result["persona"])


async def _send_follow_up(
    session: ChatSession,
    session_id: str,
    query: str,
    beat: DialogueBeat,
    emotion_tag: str,
    chunk_size: int = 80,
):
    """发送补充/续场回答：流式给提问者 + 广播给全员"""

    # 导演介入提示（广播给全员）
    beat_cn = session.persona_router.registry[beat.speaker].name_cn
    beat_label = {
        "opening": "开场定调",
        "challenge": "不同角度",
        "support": "补充支撑",
        "punchline": "翻包袱",
        "cooldown": "冷静",
    }.get(beat.beat_type, "接话")

    await room_manager.broadcast(DEFAULT_ROOM, {
        "type": "director_beat",
        "speaker": beat.speaker,
        "speaker_cn": beat_cn,
        "beat_type": beat.beat_type,
        "beat_label": beat_label,
        "timestamp": datetime.now().isoformat(),
    })

    # 生成补充回答
    follow_result = await generate_response(
        session, query, beat.speaker, emotion_tag, beat.beat_type
    )

    # 个人流式给提问者
    fc = follow_result["content"]
    await room_manager.send_to(session_id, {
        "type": "message_start",
        "persona": follow_result["persona"],
        "persona_id": beat.speaker,
    })
    for i in range(0, len(fc), chunk_size):
        await room_manager.send_to(session_id, {
            "type": "message_chunk",
            "chunk": fc[i:i + chunk_size],
        })
    await room_manager.send_to(session_id, {
        "type": "message_end",
        "content": fc,
        "persona": follow_result["persona"],
        "persona_id": beat.speaker,
        "sources": follow_result.get("sources", []),
        "confidence": follow_result.get("confidence", "low"),
    })

    # 广播完整补充给全员（排除提问者，提问者已通过流式看到）
    follow_ai_msg = {
        "type": "ai_message",
        "persona": follow_result["persona"],
        "persona_id": beat.speaker,
        "content": fc,
        "sources": follow_result.get("sources", []),
        "confidence": follow_result.get("confidence", "low"),
        "timestamp": datetime.now().isoformat(),
    }
    await room_manager.broadcast(DEFAULT_ROOM, follow_ai_msg, exclude_session=session_id)
    room_manager.add_history(DEFAULT_ROOM, follow_ai_msg)
    session.add_message("assistant", fc, follow_result["persona"])


def _check_duet(session: ChatSession, speaker: str, content: str) -> Optional[DialogueBeat]:
    """
    检测片警-朝阳群众对戏（Duet）
    两条路径，各4轮：
      路径A（@police）:  police(0)→chaoyang(1)→police(2)→chaoyang(3)→end
      路径B（@chaoyang爆料）: chaoyang(0)→police(1)→chaoyang(2)→police(3)→end
    stage 含义：下一位该谁说话（而不是谁刚说完）
    """
    # ---- 路径B开场：朝阳群众爆料太野 → 片警质问 ----
    if speaker == "chaoyang" and session.duet_stage == 0:
        wild_keywords = ["听说", "传闻", "群里", "爆料", "内部", "大户", "偷偷", "尽调", "疯了"]
        if sum(1 for k in wild_keywords if k in content) >= 2:
            session.duet_mode = True
            session.duet_stage = 1   # 下一位：police
            session.duet_round = 1
            return DialogueBeat(speaker="police", beat_type="duet_closer", target="chaoyang")

    # ---- 路径A开场：用户@police → police发言后调度chaoyang接招 ----
    if speaker == "police" and session.duet_stage == 0:
        session.duet_mode = True
        session.duet_stage = 1   # 下一位：chaoyang
        session.duet_round = 1
        return DialogueBeat(speaker="chaoyang", beat_type="duet_reply", target="police")

    # ---- Stage 1：chaoyang接招后 → 调度police再追 ----
    if speaker == "chaoyang" and session.duet_stage == 1:
        session.duet_stage = 2   # 下一位：police
        return DialogueBeat(speaker="police", beat_type="duet_closer", target="chaoyang")

    # ---- Stage 1：police质问后（路径B） → 调度chaoyang接招 ----
    if speaker == "police" and session.duet_stage == 1:
        session.duet_stage = 2   # 下一位：chaoyang
        return DialogueBeat(speaker="chaoyang", beat_type="duet_reply", target="police")

    # ---- Stage 2：police再追后（路径A） → 调度chaoyang收尾 ----
    if speaker == "police" and session.duet_stage == 2:
        session.duet_stage = 3   # 下一位：chaoyang
        return DialogueBeat(speaker="chaoyang", beat_type="duet_closer", target="police")

    # ---- Stage 2：chaoyang接招后（路径B） → 调度police再追 ----
    if speaker == "chaoyang" and session.duet_stage == 2:
        session.duet_stage = 3   # 下一位：police
        return DialogueBeat(speaker="police", beat_type="duet_closer", target="chaoyang")

    # ---- Stage 3：chaoyang收尾后（路径A） → 对戏结束 ----
    if speaker == "chaoyang" and session.duet_stage == 3:
        session.duet_mode = False
        session.duet_stage = 0
        session.duet_round = 0
        return None

    # ---- Stage 3：police再追后（路径B） → 调度chaoyang收尾 ----
    if speaker == "police" and session.duet_stage == 3:
        session.duet_stage = 4   # 下一位：chaoyang（收尾）
        return DialogueBeat(speaker="chaoyang", beat_type="duet_closer", target="police")

    # ---- Stage 4：chaoyang收尾后（路径B） → 对戏结束 ----
    if speaker == "chaoyang" and session.duet_stage == 4:
        session.duet_mode = False
        session.duet_stage = 0
        session.duet_round = 0
        return None

    return None


def _pick_follow_up(persona_id: str, emotion_tag: str) -> Optional[str]:
    """选择一个互补AI做补充回答"""
    pairs = {
        "lao_k": "su_su",
        "su_su": "lao_k",
        "lao_li": "wang_bo",
        "xiao_chen": "lao_li",
        "wang_bo": "xiao_chen",
    }
    return pairs.get(persona_id)


# ============================================
# 自动开场（第一个用户进入时触发）
# ============================================

async def _auto_opening(session: ChatSession, session_id: str):
    """直播间自动开场：根据当前时段触发不同开场内容"""
    await asyncio.sleep(2)
    state = room_manager.get_room_state(DEFAULT_ROOM)
    if state.get("auto_opened"):
        return
    room_manager.update_room_state(DEFAULT_ROOM, "auto_opened", True)

    # 根据时段选择开场模式
    current_slot = show_schedule.current_slot()
    slot_mode = current_slot.mode if current_slot else "freestyle"

    # ========== 晨间通讯社 ==========
    if slot_mode == "morning_news":
        await _auto_opening_morning_news(session, state)
        return

    # ========== 午间悄悄话 ==========
    if slot_mode == "lunch":
        await _auto_opening_lunch(session, state)
        return

    # ========== 日盘剧场 / 浏览者大厅（默认） ==========
    await _auto_opening_default(session, state)


async def _auto_opening_morning_news(session: ChatSession, state: dict):
    """晨间通讯社开场：播报国际REITs要闻"""
    engine = get_morning_engine()
    try:
        broadcast = await engine.run_morning_broadcast()
        bulletin = broadcast["bulletin"]

        # 广播晨报标题
        await room_manager.broadcast(DEFAULT_ROOM, {
            "type": "system",
            "content": "🌍 晨间通讯社开始播报 · 今日国际REITs要闻",
            "timestamp": datetime.now().isoformat(),
        })

        # 广播新闻简报
        await room_manager.broadcast(DEFAULT_ROOM, {
            "type": "morning_news",
            "payload": bulletin,
            "timestamp": datetime.now().isoformat(),
        })

        # 更新话题状态
        room_manager.update_room_state(DEFAULT_ROOM, "current_topic", "晨间通讯社 · 国际REITs要闻")
        room_manager.update_room_state(DEFAULT_ROOM, "topic_desc", "🌍 晨间通讯社播报中...")
        await room_manager.broadcast(DEFAULT_ROOM, {
            "type": "topic_update",
            "current_round": 1,
            "max_rounds": state["max_rounds"],
            "current_topic": state["current_topic"],
            "topic_desc": state["topic_desc"],
            "topic_queue": state["topic_queue"],
        })
    except Exception as e:
        logger.warning(f"Morning news opening failed: {e}")


async def _auto_opening_lunch(session: ChatSession, state: dict):
    """午间悄悄话开场：生成轻松话题，苏苏主场"""
    whisper = get_lunch_whisper()
    try:
        topic_data = await whisper.generate_topic()
        topic = topic_data["topic"]

        # 广播午间开场
        await room_manager.broadcast(DEFAULT_ROOM, {
            "type": "system",
            "content": f"🌿 午间悄悄话开始 · 今日话题：{topic}",
            "timestamp": datetime.now().isoformat(),
        })

        # 广播午间话题卡片
        await room_manager.broadcast(DEFAULT_ROOM, {
            "type": "lunch_whisper",
            "payload": topic_data,
            "timestamp": datetime.now().isoformat(),
        })

        # 更新话题状态
        room_manager.update_room_state(DEFAULT_ROOM, "current_topic", topic)
        room_manager.update_room_state(DEFAULT_ROOM, "topic_desc", "🌿 午间悄悄话 · 轻松聊聊")
        await room_manager.broadcast(DEFAULT_ROOM, {
            "type": "topic_update",
            "current_round": 1,
            "max_rounds": state["max_rounds"],
            "current_topic": state["current_topic"],
            "topic_desc": state["topic_desc"],
            "topic_queue": state["topic_queue"],
        })

        # 苏苏主场接话
        query = f"各位，午休时间了，聊聊这个话题：{topic}"
        result = await generate_response(session, query, "su_su", "neutral", beat_type="opening")
        ai_msg = {
            "type": "ai_message",
            "persona": result["persona"],
            "persona_id": "su_su",
            "content": result["content"],
            "sources": result.get("sources", []),
            "confidence": result.get("confidence", "low"),
            "timestamp": datetime.now().isoformat(),
        }
        await room_manager.broadcast(DEFAULT_ROOM, ai_msg)
        room_manager.add_history(DEFAULT_ROOM, ai_msg)
        session.add_message("assistant", result["content"], result["persona"])
    except Exception as e:
        logger.warning(f"Lunch opening failed: {e}")


async def _auto_opening_default(session: ChatSession, state: dict):
    """默认开场：日盘剧场 / 浏览者大厅"""
    try:
        market_emotion = session.sentiment_engine.get_market_emotion()
        emotion_tag = market_emotion.get("overall", "neutral")
    except Exception:
        emotion_tag = "neutral"

    # 获取热点话题作为开场引子
    topic = state.get("current_topic", "REITs市场热点")
    query = f"各位，今天{topic}有什么看点？给大家开个场。"

    # 导演设计开场节拍
    stances = {k: v["stance"] for k, v in state.get("stances", {}).items()}
    beats = session.director.design_scene(
        topic=topic,
        sentiment={"emotion": emotion_tag, "score": 0, "intensity": 0},
        perspectives=stances,
        round_num=0,
    )

    if not beats:
        # 兜底：老K直接开场
        beats = [DialogueBeat(speaker="lao_k", beat_type="opening")]

    # 逐个执行开场节拍
    for beat in beats[:2]:  # 最多2个AI开场，避免太长
        try:
            result = await generate_response(session, query, beat.speaker, emotion_tag, beat.beat_type)
            content = result["content"]
            persona = result["persona"]

            # 广播给全员（提问者也收到，因为这是系统触发的开场）
            ai_msg = {
                "type": "ai_message",
                "persona": persona,
                "persona_id": beat.speaker,
                "content": content,
                "sources": result.get("sources", []),
                "confidence": result.get("confidence", "low"),
                "timestamp": datetime.now().isoformat(),
            }
            await room_manager.broadcast(DEFAULT_ROOM, ai_msg)
            room_manager.add_history(DEFAULT_ROOM, ai_msg)
            session.add_message("assistant", content, persona)

            # 更新轮次和话题进度
            current = state["current_round"] + 1
            room_manager.update_room_state(DEFAULT_ROOM, "current_round", current)
            room_manager.update_room_state(DEFAULT_ROOM, "topic_desc", f"{persona} 开场分析中...")
            await room_manager.broadcast(DEFAULT_ROOM, {
                "type": "topic_update",
                "current_round": current,
                "max_rounds": state["max_rounds"],
                "current_topic": state["current_topic"],
                "topic_desc": state["topic_desc"],
                "topic_queue": state["topic_queue"],
            })

            await asyncio.sleep(1.5)  # 间隔，营造对话感
        except Exception as e:
            logger.warning(f"Auto-opening beat failed: {e}")
            continue


# ============================================
# 辩论后台任务（触发后异步运行，结果广播全员）
# ============================================

async def _run_debate_broadcast(session: ChatSession, topic: str):
    """运行稀疏辩论并广播结果"""
    try:
        debate_mgr = get_debate_manager(session.persona_router)
        rag_context = []
        try:
            debate_fund_code = _extract_fund_code(topic)
            rag_context = search_articles_for_rag(topic, top_k=5, fund_code=debate_fund_code)
        except Exception:
            pass

        context = {
            "topic": topic,
            "rag_chunks": rag_context,
            "history": [m["content"] for m in session.messages[-3:]],
        }

        result = await debate_mgr.run_debate(topic, context)

        # 广播辩论结果
        await room_manager.broadcast(DEFAULT_ROOM, {
            "type": "DEBATE_RESULT",
            "payload": {
                "topic": result["topic"],
                "proposals": result["proposals"],
                "conflicts": result["conflicts"],
                "consensus": result["consensus"],
                "debate_closed_at": result["debate_closed_at"],
            }
        })

        # 辩论结束后更新话题状态
        state = room_manager.get_room_state(DEFAULT_ROOM)
        room_manager.update_room_state(DEFAULT_ROOM, "topic_desc", "投研辩论会已结束，各位观点见上")
        await room_manager.broadcast(DEFAULT_ROOM, {
            "type": "topic_update",
            "current_round": state["current_round"],
            "max_rounds": state["max_rounds"],
            "current_topic": state["current_topic"],
            "topic_desc": state["topic_desc"],
            "topic_queue": state["topic_queue"],
        })
    except Exception as e:
        logger.error(f"Debate broadcast failed: {e}")
        await room_manager.broadcast(DEFAULT_ROOM, {
            "type": "system",
            "content": f"辩论会出错了: {str(e)[:80]}",
            "timestamp": datetime.now().isoformat(),
        })


# ============================================
# WebSocket 端点
# ============================================

@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket 直播间端点
    统一内容原则：所有用户在同一房间，看到相同的AI对话流

    协议：
    - 客户端发送: {"action": "chat", "message": "...", "persona": "lao_k|su_su|lao_li|xiao_chen|wang_bo|null"}
    - 全员广播-用户消息: {"type": "user_message", "sender": "昵称", "content": "...", "timestamp": "..."}
    - 全员广播-AI回复:   {"type": "ai_message", "persona": "...", "content": "...", "sources": [...]}
    - 历史同步:          {"type": "HISTORY_SYNC", "messages": [...]}
    - 导演续场提示:      {"type": "director_beat", "speaker": "...", "speaker_cn": "...", "beat_type": "..."}
    - 个人流式(可选):    {"type": "message_start|message_chunk|message_end", ...}
    - 错误:              {"type": "error", "message": "..."}
    """
    await websocket.accept()
    session_id = f"ws_{id(websocket)}"

    # 1. 加入默认房间
    nickname = await room_manager.join(DEFAULT_ROOM, session_id, websocket)
    session = ChatSession(session_id, websocket, nickname)

    logger.info(f"WebSocket connected: {session_id} ({nickname})")

    # 2. 发送历史同步（让新用户跟上剧情）
    history = room_manager.get_history(DEFAULT_ROOM, 20)
    try:
        await websocket.send_json({
            "type": "HISTORY_SYNC",
            "messages": history,
        })
    except Exception as e:
        logger.warning(f"History sync failed: {e}")

    # 3. 广播系统消息：新观众进入
    await room_manager.broadcast(DEFAULT_ROOM, {
        "type": "system",
        "content": f"{nickname} 进入了直播间",
        "timestamp": datetime.now().isoformat(),
    })

    # 4. 发送直播间状态初始化（侧边栏动态数据）
    state = room_manager.get_room_state(DEFAULT_ROOM)
    try:
        market_emotion = session.sentiment_engine.get_market_emotion()
    except Exception:
        market_emotion = {"overall": "neutral", "score": 0.0}
    await websocket.send_json({
        "type": "sentiment_update",
        "temp": int((market_emotion.get("score", 0) + 1) * 50),
        "emotion": market_emotion.get("overall", "中性"),
        "splits": [
            {"who": "老K", "says": state["stances"]["老K"]["quote"]},
            {"who": "苏苏", "says": state["stances"]["苏苏"]["quote"]},
        ],
    })
    await websocket.send_json({
        "type": "topic_update",
        "current_round": state["current_round"],
        "max_rounds": state["max_rounds"],
        "current_topic": state["current_topic"],
        "topic_desc": state["topic_desc"],
        "topic_queue": state["topic_queue"],
    })
    await websocket.send_json({
        "type": "quiz_update",
        "up": state["quiz"]["up"],
        "down": state["quiz"]["down"],
        "total": state["quiz"]["total"],
    })
    await websocket.send_json({
        "type": "stance_sync",
        "stances": state["stances"],
    })

    # 5. 自动开场：第一个用户进入时触发AI讨论
    room = room_manager.rooms.get(DEFAULT_ROOM, {})
    if len(room) == 1 and not state.get("auto_opened"):
        asyncio.create_task(_auto_opening(session, session_id))

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            action = data.get("action", "chat")

            if action == "chat":
                query = data.get("message", "").strip()
                if not query:
                    await room_manager.send_to(session_id, {"type": "error", "message": "消息不能为空"})
                    continue

                # 0. 检查当前时段与配额
                current_slot = show_schedule.current_slot()
                butterfly_trigger.update_online_count(len(room_manager.rooms.get(DEFAULT_ROOM, {})))
                
                # showtime 时段检查配额
                if current_slot and current_slot.user_quota > 0:
                    if not quota_manager.can_ask(session_id, current_slot.slot_id, current_slot.user_quota):
                        await room_manager.send_to(session_id, {
                            "type": "quota_exceeded",
                            "slot_name": current_slot.name,
                            "message": f"【{current_slot.name}】每人每场限{current_slot.user_quota}问，你已用完额度。",
                            "current_slot": current_slot.slot_id,
                        })
                        continue
                    quota_manager.consume_quota(session_id, current_slot.slot_id)
                
                # 1. 情感计算
                try:
                    market_emotion = session.sentiment_engine.get_market_emotion()
                    emotion_tag = market_emotion.get("overall", "neutral")
                except Exception:
                    emotion_tag = "neutral"

                # 2. 人设路由
                requested_persona = data.get("persona")
                logger.info(f"[WS] requested_persona={requested_persona}, query={query[:40]}")
                persona_cfg = session.persona_router.route(query, mentioned=requested_persona)
                persona_id = persona_cfg.name
                logger.info(f"[WS] routed to persona_id={persona_id}, name_cn={persona_cfg.name_cn}")

                # 如果切换了人设，通知提问者
                if persona_id != session.current_persona:
                    session.current_persona = persona_id
                    await room_manager.send_to(session_id, {
                        "type": "persona_switch",
                        "persona": persona_cfg.name_cn,
                        "persona_id": persona_id,
                    })

                # 3. 广播用户消息给全员（统一内容核心！）
                user_msg = {
                    "type": "user_message",
                    "sender": nickname,
                    "content": query,
                    "timestamp": datetime.now().isoformat(),
                }
                await room_manager.broadcast(DEFAULT_ROOM, user_msg)
                room_manager.add_history(DEFAULT_ROOM, user_msg)
                session.add_message("user", query)

                # ===== 新增：判断是否进入稀疏辩论 =====
                if DebateManager.should_debate(query) and not requested_persona:
                    # 广播辩论触发提示
                    await room_manager.broadcast(DEFAULT_ROOM, {
                        "type": "system",
                        "content": "🎙️ 已触发投研辩论会，5位分析师正在独立撰写投资备忘录...",
                        "timestamp": datetime.now().isoformat(),
                    })
                    # 后台运行辩论并广播结果
                    asyncio.create_task(_run_debate_broadcast(session, query))
                    continue

                # 3.5 飞行嘉宾调度：扫描用户消息，判断是否需要嘉宾出场
                guest_triggers = session.guest_dispatcher.get_pending_triggers(
                    user_msg=query,
                    mentioned=requested_persona
                )

                # 4. 导演设计场景（节拍序列）
                stances = {k: v["stance"] for k, v in state.get("stances", {}).items()}
                beats = session.director.design_scene(
                    topic=query,
                    sentiment={"emotion": emotion_tag, "score": market_emotion.get("score", 0), "intensity": 0},
                    perspectives=stances,
                    round_num=session.round_count,
                )
                if not beats:
                    beats = [DialogueBeat(speaker=persona_id, beat_type="opening")]

                # 5. 主AI流式回复（提问者独享流式体验）
                beat_type = beats[0].beat_type if beats else ""
                content = ""
                persona_name = persona_cfg.name_cn
                sources = []
                confidence = "low"
                stream_error = None

                # 先发送 message_start，让前端初始化 streamBuffer
                await room_manager.send_to(session_id, {
                    "type": "message_start",
                    "persona": persona_name,
                    "persona_id": persona_id,
                })

                async for item in generate_response_stream(session, query, persona_id, emotion_tag, beat_type):
                    if item["type"] == "chunk":
                        content += item["chunk"]
                        await room_manager.send_to(session_id, {
                            "type": "message_chunk",
                            "chunk": item["chunk"],
                        })
                    elif item["type"] == "done":
                        content = item["content"]
                        persona_name = item["persona"]
                        sources = item["sources"]
                        confidence = item["confidence"]
                    elif item["type"] == "error":
                        stream_error = item["content"]
                        persona_name = item.get("persona", persona_cfg.name_cn)

                if stream_error:
                    content = stream_error

                await room_manager.send_to(session_id, {
                    "type": "message_end",
                    "content": content,
                    "persona": persona_name,
                    "persona_id": persona_id,
                    "sources": sources,
                    "confidence": confidence,
                })

                # 保存 AI 消息到会话上下文
                session.add_message("assistant", content, persona_name)
                session.round_count += 1

                # 6. 广播完整AI回复给全员（统一内容核心！）
                # 提问者已经通过流式看到了内容，其他人需要收到完整消息
                ai_msg = {
                    "type": "ai_message",
                    "persona": persona_name,
                    "persona_id": persona_id,
                    "content": content,
                    "sources": sources,
                    "confidence": confidence,
                    "timestamp": datetime.now().isoformat(),
                }
                await room_manager.broadcast(DEFAULT_ROOM, ai_msg, exclude_session=session_id)
                room_manager.add_history(DEFAULT_ROOM, ai_msg)

                # 6.5 飞行嘉宾调度：扫描AI输出，判断是否需要片警纠察
                police_triggers = session.guest_dispatcher.scan_ai_output(content, persona_id)
                guest_triggers.extend(police_triggers)

                # 去重并排序
                seen = set()
                unique_triggers = []
                for t in sorted(guest_triggers, key=lambda x: x.urgency, reverse=True):
                    if t.guest_id not in seen:
                        seen.add(t.guest_id)
                        unique_triggers.append(t)

                # 执行嘉宾闪现（最高优先级的1-2个嘉宾）
                chunk_size = 80
                for trigger in unique_triggers[:2]:
                    await asyncio.sleep(0.5)  # 短暂停顿，营造"闪现"感
                    await _send_guest_flash(session, session_id, query, trigger, emotion_tag, chunk_size)

                # ===== Duet 对戏检测（片警 ↔ 朝阳群众） =====
                duet_beat = _check_duet(session, persona_id, content)
                if duet_beat:
                    await asyncio.sleep(1.2)
                    await _send_follow_up(session, session_id, query, duet_beat, emotion_tag, chunk_size)

                # 7. 导演续场（原始设计_scene的后续节拍）
                for beat in beats[1:]:
                    await _send_follow_up(session, session_id, query, beat, emotion_tag, chunk_size)

                # 8. 多AI接力：每次提问后，根据主AI选择1个互补AI做补充
                # 60%概率触发，保持节奏感，避免每次都有太多回复
                follow_up = _pick_follow_up(persona_id, emotion_tag)
                if follow_up and random.random() < 0.75:
                    await asyncio.sleep(0.3)
                    await _send_follow_up(
                        session, session_id, query,
                        DialogueBeat(speaker=follow_up, beat_type="support"),
                        emotion_tag, chunk_size
                    )

                # 8.5 蝴蝶效应：用户提问后，概率触发AI自发讨论
                if butterfly_trigger.should_trigger(query):
                    await asyncio.sleep(1.0)
                    # 随机选1个未发言的AI，针对用户话题自发接话
                    spoken = {persona_id}
                    if follow_up:
                        spoken.add(follow_up)
                    for t in unique_triggers:
                        spoken.add(t.guest_id)
                    if duet_beat:
                        spoken.add(duet_beat.speaker)
                    available = [aid for aid in ["lao_k", "su_su", "lao_li", "xiao_chen", "wang_bo"] if aid not in spoken]
                    if available:
                        spark_id = random.choice(available)
                        await room_manager.broadcast(DEFAULT_ROOM, {
                            "type": "system",
                            "content": f"💡 {session.persona_router.registry[spark_id].name_cn} 自发回应了刚才的话题",
                            "timestamp": datetime.now().isoformat(),
                        })
                        await _send_follow_up(
                            session, session_id, query,
                            DialogueBeat(speaker=spark_id, beat_type="challenge"),
                            emotion_tag, chunk_size
                        )

                # 9. 更新直播间轮次状态并广播给全员
                state = room_manager.get_room_state(DEFAULT_ROOM)
                new_round = state["current_round"] + 1
                if new_round > state["max_rounds"]:
                    new_round = 1
                    # 切换话题：把当前话题移到队列末尾，下一个话题激活
                    queue = state["topic_queue"]
                    if queue:
                        current = queue.pop(0)
                        current["active"] = False
                        queue.append(current)
                        if queue:
                            queue[0]["active"] = True
                            state["current_topic"] = queue[0]["title"]
                room_manager.update_room_state(DEFAULT_ROOM, "current_round", new_round)
                room_manager.update_room_state(DEFAULT_ROOM, "topic_desc", f"{persona_name} 刚刚分析完，正在接力...")
                await room_manager.broadcast(DEFAULT_ROOM, {
                    "type": "topic_update",
                    "current_round": new_round,
                    "max_rounds": state["max_rounds"],
                    "current_topic": state["current_topic"],
                    "topic_desc": state["topic_desc"],
                    "topic_queue": state["topic_queue"],
                })

            elif action == "quiz_vote":
                val = data.get("vote")
                if val in ("up", "down"):
                    room_manager.vote_quiz(DEFAULT_ROOM, val)
                    state = room_manager.get_room_state(DEFAULT_ROOM)
                    await room_manager.broadcast(DEFAULT_ROOM, {
                        "type": "quiz_update",
                        "up": state["quiz"]["up"],
                        "down": state["quiz"]["down"],
                        "total": state["quiz"]["total"],
                    })

            elif action == "topic_bump":
                topic_id = data.get("topic_id")
                if room_manager.vote_topic(DEFAULT_ROOM, topic_id):
                    state = room_manager.get_room_state(DEFAULT_ROOM)
                    await room_manager.broadcast(DEFAULT_ROOM, {
                        "type": "topic_update",
                        "current_round": state["current_round"],
                        "max_rounds": state["max_rounds"],
                        "current_topic": state["current_topic"],
                        "topic_desc": state["topic_desc"],
                        "topic_queue": state["topic_queue"],
                    })

            elif action == "init_state":
                state = room_manager.get_room_state(DEFAULT_ROOM)
                try:
                    market_emotion = session.sentiment_engine.get_market_emotion()
                except Exception:
                    market_emotion = {"overall": "neutral", "score": 0.0}
                await room_manager.send_to(session_id, {
                    "type": "sentiment_update",
                    "temp": int((market_emotion.get("score", 0) + 1) * 50),
                    "emotion": market_emotion.get("overall", "中性"),
                    "splits": [
                        {"who": "老K", "says": state["stances"]["老K"]["quote"]},
                        {"who": "苏苏", "says": state["stances"]["苏苏"]["quote"]},
                    ],
                })
                await room_manager.send_to(session_id, {
                    "type": "topic_update",
                    "current_round": state["current_round"],
                    "max_rounds": state["max_rounds"],
                    "current_topic": state["current_topic"],
                    "topic_desc": state["topic_desc"],
                    "topic_queue": state["topic_queue"],
                })
                await room_manager.send_to(session_id, {
                    "type": "quiz_update",
                    "up": state["quiz"]["up"],
                    "down": state["quiz"]["down"],
                    "total": state["quiz"]["total"],
                })
                await room_manager.send_to(session_id, {
                    "type": "stance_sync",
                    "stances": state["stances"],
                })

            elif action == "summarize":
                # AI摘要：总结最近AI对话的共识、分歧、核心论据
                limit = data.get("message_count", 20)
                history = room_manager.get_history(DEFAULT_ROOM, limit)
                ai_messages = [
                    f"[{m.get('persona', 'AI')}] {m.get('content', '')}"
                    for m in history
                    if m.get("type") == "ai_message" and m.get("content")
                ]

                if len(ai_messages) < 2:
                    await room_manager.send_to(session_id, {
                        "type": "summary",
                        "content": "对话还不够多，请先让专家们多聊几句~",
                        "consensus": "",
                        "divergence": "",
                        "key_points": "",
                    })
                    continue

                # 调用LLM生成摘要
                summary_text = await _generate_summary(ai_messages)

                # 解析结构化摘要
                consensus = _extract_section(summary_text, "共识") or _extract_section(summary_text, "1.")
                divergence = _extract_section(summary_text, "分歧") or _extract_section(summary_text, "2.")
                key_points = _extract_section(summary_text, "核心论据") or _extract_section(summary_text, "3.")

                await room_manager.send_to(session_id, {
                    "type": "summary",
                    "content": summary_text,
                    "consensus": consensus,
                    "divergence": divergence,
                    "key_points": key_points,
                })

            elif action == "ping":
                await room_manager.send_to(session_id, {"type": "pong"})

            else:
                await room_manager.send_to(session_id, {"type": "error", "message": f"Unknown action: {action}"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await room_manager.send_to(session_id, {"type": "error", "message": str(e)})
        except:
            pass
    finally:
        # 离开房间
        await room_manager.leave(session_id)
        # 广播离开消息
        await room_manager.broadcast(DEFAULT_ROOM, {
            "type": "system",
            "content": f"{nickname} 离开了直播间",
            "timestamp": datetime.now().isoformat(),
        })


async def _generate_summary(ai_messages: List[str]) -> str:
    """生成对话摘要"""
    from core.config import settings
    from openai import AsyncOpenAI
    try:
        base_url = settings.LLM_CONFIG["deepseek_pro"]["base_url"]
        if not base_url.endswith("/v1"):
            base_url = base_url.rstrip("/") + "/v1"
        api_key = os.getenv("DEEPSEEK_API_KEY", settings.LLM_CONFIG["deepseek_pro"]["api_key"])
        if not api_key:
            return "API Key 未配置，无法生成摘要。"
        client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=30)
        prompt = (
            "请对以下AI对话进行结构化摘要：\n\n"
            + "\n\n".join(ai_messages[-20:])
            + "\n\n请按以下格式输出：\n"
            "共识：...\n"
            "分歧：...\n"
            "核心论据：..."
        )
        response = await client.chat.completions.create(
            model=settings.LLM_CONFIG["deepseek_pro"]["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1024,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        return "摘要生成失败。"


def _extract_section(text: str, keyword: str) -> str:
    """从文本中提取指定章节"""
    import re
    pattern = re.compile(rf"{re.escape(keyword)}[：:]\s*(.+?)(?=\n\n|\n[A-Z]|$)", re.DOTALL)
    match = pattern.search(text)
    return match.group(1).strip() if match else ""
