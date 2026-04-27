#!/usr/bin/env python3
"""
Supervisor 状态机 —— 含片警-朝阳群众对戏系统
直接替换原有 supervisor.py
"""

import asyncio
import logging
import re
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime

from agents.persona_router import get_persona_router
from engine.sentiment import get_sentiment_engine, SentimentResult
from agents.debate_manager import DebateManager, get_debate_manager
from agents.show_schedule import get_schedule, ShowSlot
from agents.user_quota import get_quota_manager
from agents.butterfly_effect import get_butterfly_trigger
from rag.local_retriever import get_retriever

logger = logging.getLogger("supervisor")


class State(Enum):
    IDLE = auto()
    SELECT_SPEAKER = auto()
    ASSIGN_FLOOR = auto()
    BROADCAST = auto()
    CONTINUE = auto()
    INTERRUPT = auto()
    COOL_DOWN = auto()
    DUET = auto()           # 对戏状态
    DEBATE = auto()         # 稀疏辩论状态
    FREESTYLE = auto()      # 浏览者大厅：强制分歧模式
    MORNING_NEWS = auto()   # 晨间通讯社
    LUNCH = auto()          # 午间悄悄话


@dataclass
class Trigger:
    type: str
    payload: Any
    priority: int = 0


@dataclass
class GuestTrigger:
    """飞行嘉宾出场请求"""
    guest_id: str
    reason: str
    urgency: int
    max_utterances: int


@dataclass
class DialogueContext:
    """对话上下文，跨状态共享"""
    topic: str = ""
    primary_agent: Optional[str] = None
    current_speaker: Optional[str] = None
    last_speaker: Optional[str] = None
    messages: List[Any] = field(default_factory=list)
    silence_timer: Optional[asyncio.Task] = None
    start_time: datetime = field(default_factory=datetime.now)
    round_count: int = 0
    
    # ===== 对戏系统新增字段 =====
    duet_mode: bool = False
    duet_stage: int = 0                        # 0=无 1=质问 2=接招 3=再追 4=收尾
    duet_max_rounds: int = 2
    duet_current_round: int = 0
    last_police_challenge: str = ""
    pending_duet_speaker: Optional[str] = None


@dataclass
class DialogueBeat:
    speaker: str
    beat_type: str
    target: Optional[str] = None
    emotion_override: Optional[str] = None
    delay_ms: int = 0


class FloorManager:
    """话筒管理器"""
    def __init__(self, agent_ids: set):
        self.agent_ids = set(agent_ids)
        self._locked_by: Optional[str] = None
        self._speak_count: Dict[str, int] = {a: 0 for a in agent_ids}

    def lock(self, agent_id: str):
        if agent_id not in self.agent_ids:
            raise ValueError(f"未知Agent: {agent_id}")
        self._locked_by = agent_id
        self._speak_count[agent_id] += 1

    def unlock(self, agent_id: str):
        if self._locked_by == agent_id:
            self._locked_by = None

    def reset_counts(self):
        for k in self._speak_count:
            self._speak_count[k] = 0


class GuestDispatcher:
    """飞行嘉宾调度器"""
    
    COMPLIANCE_KEYWORDS = [
        "买入", "卖出", "重仓", "清仓", "梭哈", "all in", "满仓",
        "推荐", "保证收益", "肯定涨", "必跌", "目标价", "翻倍", "抄底"
    ]
    
    GOSSIP_KEYWORDS = [
        "听说", "传闻", "群里", "股吧", "雪球", "爆料", "异动",
        "涨停", "放量", "坊间", "散户", "小道消息", "内部人士", "尽调"
    ]
    
    WILD_KEYWORDS = ["听说", "传闻", "群里", "爆料", "内部", "大户", "偷偷", "尽调", "疯了"]
    
    def __init__(self, router=None):
        self.router = router or get_persona_router()
        self.active_guests: Dict[str, int] = {}
    
    def scan_user_message(self, user_msg: str) -> List[GuestTrigger]:
        triggers = []
        msg = user_msg.lower()
        
        # 片警：合规红线（最高优先级）
        if any(k in msg for k in self.COMPLIANCE_KEYWORDS):
            triggers.append(GuestTrigger(
                guest_id="police",
                reason="用户消息含投资操作建议关键词",
                urgency=10,
                max_utterances=2
            ))
        
        # 朝阳群众：民间情报
        if any(k in msg for k in self.GOSSIP_KEYWORDS):
            triggers.append(GuestTrigger(
                guest_id="chaoyang",
                reason="用户消息含坊间传闻/异动关键词",
                urgency=6,
                max_utterances=3
            ))
        
        return triggers
    
    def scan_ai_output(self, ai_msg: str, agent_id: str) -> List[GuestTrigger]:
        """扫描AI输出，判断是否需要嘉宾纠察"""
        triggers = []
        msg = ai_msg.lower()
        
        if agent_id == "police":
            return triggers
        
        # 片警：AI越界检查
        if re.search(r'(建议|推荐).{0,5}(买入|卖出|持有|加仓|减仓)', msg):
            triggers.append(GuestTrigger(
                guest_id="police",
                reason=f"{agent_id}的发言疑似包含投资建议",
                urgency=10,
                max_utterances=2
            ))
        
        # 检查是否编造政策文号
        if re.search(r'〔\d{4}〕\d+号', msg) and "来源" not in msg:
            triggers.append(GuestTrigger(
                guest_id="police",
                reason=f"{agent_id}引用政策文号但未标注来源",
                urgency=9,
                max_utterances=1
            ))
        
        return triggers
    
    def scan_hotspot(self, hotspot_title: str) -> List[GuestTrigger]:
        """扫描热点话题，判断是否需要嘉宾"""
        triggers = []
        if any(k in hotspot_title for k in ["涨停", "异动", "放量", "传闻", "收购"]):
            triggers.append(GuestTrigger(
                guest_id="chaoyang",
                reason="热点含异动/传闻元素",
                urgency=5,
                max_utterances=2
            ))
        return triggers
    
    def check_chaoyang_wild(self, content: str) -> bool:
        """判断朝阳群众发言是否太野，需要片警纠察"""
        return sum(1 for k in self.WILD_KEYWORDS if k in content) >= 2
    
    def activate_guest(self, trigger: GuestTrigger):
        self.active_guests[trigger.guest_id] = trigger.max_utterances
        return trigger
    
    def consume_utterance(self, guest_id: str):
        if guest_id in self.active_guests:
            self.active_guests[guest_id] -= 1
            if self.active_guests[guest_id] <= 0:
                del self.active_guests[guest_id]
    
    def can_speak(self, guest_id: str) -> bool:
        return self.active_guests.get(guest_id, 0) > 0
    
    def get_pending_triggers(
        self,
        user_msg: str = "",
        ai_msg: str = "",
        agent_id: str = "",
        hotspot_title: str = "",
        mentioned: str = None
    ) -> List[GuestTrigger]:
        """
        一站式扫描，返回所有待处理嘉宾触发器（已按优先级排序）
        """
        triggers = []

        if user_msg:
            triggers.extend(self.scan_user_message(user_msg))
        if ai_msg and agent_id:
            triggers.extend(self.scan_ai_output(ai_msg, agent_id))
        if hotspot_title:
            triggers.extend(self.scan_hotspot(hotspot_title))

        # 用户直接@嘉宾，强制出场
        if mentioned in ("police", "chaoyang"):
            cfg = self.router.get_guest(mentioned)
            if cfg:
                triggers.append(GuestTrigger(
                    guest_id=mentioned,
                    reason=f"用户直接@{cfg.name_cn}",
                    urgency=10,
                    max_utterances=cfg.max_utterances
                ))

        # 去重：同一嘉宾只保留最高优先级的
        seen = set()
        filtered = []
        for t in sorted(triggers, key=lambda x: x.urgency, reverse=True):
            if t.guest_id not in seen:
                seen.add(t.guest_id)
                filtered.append(t)

        return filtered


class SessionDirector:
    """
    会话导演 + 对戏导演
    控制发言顺序、递话、翻包袱、情绪节奏、片警-朝阳CP对戏
    """
    
    def __init__(self, agents: List[str]):
        self.agents = agents
        self.beat_history: List[DialogueBeat] = []
    
    def design_scene(self, topic: str, sentiment: SentimentResult, 
                     perspectives: Dict[str, str], round_num: int) -> List[DialogueBeat]:
        """为当前话题设计对话节拍"""
        beats = []
        
        if round_num == 0 and "lao_k" in self.agents:
            beats.append(DialogueBeat(
                speaker="lao_k",
                beat_type="opening",
                emotion_override="sarcastic" if sentiment.emotion == "greed" else "steady"
            ))
        
        if round_num == 1 and "su_su" in self.agents and "lao_k" in self.agents:
            beats.append(DialogueBeat(
                speaker="su_su",
                beat_type="support" if perspectives.get("lao_k") == "bearish" else "challenge",
                target="lao_k"
            ))
        
        guests = [a for a in self.agents if a not in ["lao_k", "su_su"]]
        if round_num == 2 and guests:
            beats.append(DialogueBeat(
                speaker=guests[0],
                beat_type="support",
                target="lao_k"
            ))
        
        if round_num == 3 and "su_su" in self.agents:
            beats.append(DialogueBeat(
                speaker="su_su",
                beat_type="punchline",
                target=guests[0] if guests else "lao_k"
            ))
        
        if sentiment.emotion in ["panic", "greed"] and round_num >= 2:
            cooler = "su_su" if sentiment.emotion == "panic" else "lao_k"
            if cooler in self.agents:
                beats.append(DialogueBeat(
                    speaker=cooler,
                    beat_type="cooldown",
                    emotion_override="calm"
                ))
        
        self.beat_history.extend(beats)
        return beats
    
    # ===== 对戏系统核心 =====
    
    def check_police_chaoyang_duet(
        self,
        last_speaker: str,
        last_content: str,
        context: DialogueContext
    ) -> Optional[DialogueBeat]:
        """
        检查是否触发"片警-朝阳群众"对戏
        返回 DialogueBeat 则进入对戏状态
        """
        # 场景1：片警刚说完，且内容含质问关键词 → 强制调度朝阳群众接招
        if last_speaker == "police" and context.duet_stage == 1:
            challenge_keywords = ["来源", "证据", "依据", "请注意", "合规", "质问", "截图", "记录"]
            if any(k in last_content for k in challenge_keywords):
                context.duet_stage = 2
                context.duet_current_round += 1
                return DialogueBeat(
                    speaker="chaoyang",
                    beat_type="duet_reply",
                    target="police",
                    emotion_override="playful",
                    delay_ms=1500
                )
        
        # 场景2：片警再追（第二轮）
        if last_speaker == "chaoyang" and context.duet_stage == 2 and context.duet_current_round < context.duet_max_rounds:
            context.duet_stage = 3
            return DialogueBeat(
                speaker="police",
                beat_type="duet_closer",
                target="chaoyang",
                emotion_override="stern",
                delay_ms=1200
            )
        
        # 场景3：朝阳群众收尾
        if last_speaker == "police" and context.duet_stage == 3:
            context.duet_stage = 4
            return DialogueBeat(
                speaker="chaoyang",
                beat_type="duet_closer",
                target="police",
                emotion_override="playful",
                delay_ms=1200
            )
        
        # 场景4：朝阳群众爆料太野 → 导演自动插入片警纠察
        if last_speaker == "chaoyang" and context.duet_stage == 0:
            wild_keywords = ["听说", "传闻", "群里", "爆料", "内部", "大户", "偷偷", "尽调", "疯了"]
            if sum(1 for k in wild_keywords if k in last_content) >= 2:
                context.duet_stage = 1
                context.duet_current_round = 1
                return DialogueBeat(
                    speaker="police",
                    beat_type="duet_closer",  # 用 interrupt 会冲突，这里用 duet_closer 作为开场质问
                    target="chaoyang",
                    emotion_override="stern",
                    delay_ms=800
                )
        
        # 对戏结束清理
        if context.duet_stage >= 4:
            context.duet_mode = False
            context.duet_stage = 0
            context.duet_current_round = 0
            context.last_police_challenge = ""
            context.pending_duet_speaker = None
        
        return None
    
    def get_next_beat(self) -> Optional[DialogueBeat]:
        if not self.beat_history:
            return None
        return self.beat_history.pop(0)


class SupervisorStateMachine:
    """主管状态机 —— 含对戏系统"""
    
    DEFAULT_ORDER = ["lao_k", "su_su", "guest_li", "guest_chen", "guest_wang"]
    SILENCE_THRESHOLD = 10
    MAX_ROUNDS_PER_TOPIC = 6

    def __init__(
        self,
        agents: Dict[str, Any],
        websocket_broadcast: Callable,
        rag_retriever: Any = None,
        llm_client: Any = None,
    ):
        self.agents = agents
        self.broadcast = websocket_broadcast
        self.rag = rag_retriever or get_retriever()
        self.llm = llm_client
        
        self.floor = FloorManager(set(agents.keys()))
        self.director = SessionDirector(list(agents.keys()))
        self.guest_dispatcher = GuestDispatcher(get_persona_router())
        
        self.state = State.IDLE
        self.context = DialogueContext()
        self.trigger_queue: asyncio.Queue[Trigger] = asyncio.Queue()
        self.pending_guest_triggers: List[GuestTrigger] = []
        
        self.debate_manager = get_debate_manager()
        self.schedule = get_schedule()
        self.quota = get_quota_manager()
        self.butterfly = get_butterfly_trigger()
        
        self.transitions = {
            State.IDLE: {
                "user_mention": self._on_user_mention,
                "hot_topic": self._on_hot_topic,
                "scheduled": self._on_scheduled,
                "silence": self._on_silence,
                "agent_initiative": self._on_agent_initiative,
            },
            State.BROADCAST: {
                "continue": self._on_continue,
                "interrupt": self._on_interrupt_request,
                "silence": self._on_silence_after_broadcast,
            },
            State.CONTINUE: {
                "continue": self._on_continue,
                "interrupt": self._on_interrupt_request,
                "user_mention": self._on_user_mention,
            },
            State.DUET: {
                "duet_continue": self._on_duet_continue,
                "user_mention": self._on_user_mention,
            },
            State.DEBATE: {
                "debate_complete": self._on_debate_complete,
                "user_mention": self._on_user_mention,
            },
            State.FREESTYLE: {
                "user_mention": self._on_freestyle_user_message,
                "continue": self._on_freestyle_continue,
            },
            State.MORNING_NEWS: {
                "scheduled": self._on_morning_news,
            },
            State.LUNCH: {
                "scheduled": self._on_lunch_whisper,
                "user_mention": self._on_lunch_user_message,
            },
        }

    # ---------- 公共接口 ----------
    
    async def start(self):
        logger.info("Supervisor 启动，进入 IDLE 状态")
        self._reset_silence_timer()
        while True:
            trigger = await self.trigger_queue.get()
            await self._handle_trigger(trigger)

    def push_trigger(self, trigger: Trigger):
        asyncio.create_task(self.trigger_queue.put(trigger))

    async def inject_user_message(self, user_msg: Dict):
        """用户消息入口——增加嘉宾扫描"""
        mentioned = user_msg.get("mentioned_agent")
        content = user_msg.get("content", "")
        
        # 1. 检查是否需要飞行嘉宾出场
        guest_triggers = self.guest_dispatcher.scan_user_message(content)
        self.pending_guest_triggers.extend(guest_triggers)
        
        # 2. 用户直接@嘉宾，强制出场
        if mentioned in ["police", "chaoyang"]:
            cfg = get_persona_router().get_guest(mentioned)
            if cfg:
                self.pending_guest_triggers.append(GuestTrigger(
                    guest_id=mentioned,
                    reason=f"用户直接@{cfg.name_cn}",
                    urgency=10,
                    max_utterances=cfg.max_utterances
                ))
        
        # 3. 按优先级排序
        self.pending_guest_triggers.sort(key=lambda x: x.urgency, reverse=True)
        
        # 4. 推给状态机
        trigger = Trigger(
            type="user_mention",
            payload={"user_msg": user_msg, "mentioned": mentioned},
            priority=100,
        )
        self.push_trigger(trigger)

    async def inject_hot_topic(self, topic: Dict):
        trigger = Trigger("hot_topic", topic, priority=80)
        self.push_trigger(trigger)

    # ---------- 状态处理器 ----------

    async def _handle_trigger(self, trigger: Trigger):
        logger.info(f"[{self.state.name}] 收到触发器: {trigger.type}")
        
        handlers = self.transitions.get(self.state, {})
        handler = handlers.get(trigger.type)
        
        if handler:
            await handler(trigger)
        else:
            if trigger.priority >= 80:
                await self._force_idle(trigger)

    async def _force_idle(self, trigger: Trigger):
        await self._clear_floor()
        self.state = State.IDLE
        await self._handle_trigger(trigger)

    # ----- IDLE -----
    
    async def _on_user_mention(self, trigger: Trigger):
        payload = trigger.payload
        mentioned = payload["mentioned"]
        content = payload["user_msg"]["content"]
        user_id = payload["user_msg"].get("user_id", "anonymous")
        
        # 获取当前时段
        slot = self.schedule.current_slot()
        self.quota.update_slot(slot.slot_id if slot else "freestyle")
        
        # ===== 日盘剧场：配额检查 =====
        if slot and slot.mode == "showtime":
            if not self.quota.can_ask(user_id, slot.slot_id, slot.user_quota):
                await self.broadcast({
                    "type": "SYSTEM_NOTICE",
                    "payload": {
                        "notice": f"本场演出每人限{slot.user_quota}问，您已用完额度，请等待下一场或去浏览者大厅交流。",
                        "next_show": self.schedule.get_next_slot().name if self.schedule.get_next_slot() else "明日",
                    }
                })
                return
            # 消耗配额
            self.quota.consume_quota(user_id, slot.slot_id)
            
            # 检查是否触发蝴蝶效应（双人快辩）
            if self.butterfly.should_trigger(content):
                await self._start_quick_debate(content, user_id)
                return
        
        # ===== 判断是否进入稀疏辩论 =====
        if DebateManager.should_debate(content) and not mentioned:
            self.context.topic = content
            self.state = State.DEBATE
            await self._start_debate(content)
            return
        
        if mentioned and mentioned in self.agents:
            self.context.primary_agent = mentioned
            self.context.topic = content
            await self._enter_assign_floor(mentioned, is_direct_answer=True)
        else:
            self.context.topic = content
            self.state = State.SELECT_SPEAKER
            await self._select_speaker_for_topic(self.context.topic)

    async def _on_hot_topic(self, trigger: Trigger):
        topic = trigger.payload
        self.context.topic = topic["title"]
        self.context.primary_agent = None
        self.state = State.SELECT_SPEAKER
        await self._select_speaker_for_topic(topic["title"])

    async def _on_scheduled(self, trigger: Trigger):
        schedule = trigger.payload
        persona = schedule["persona"]
        self.context.topic = schedule.get("topic", "今日REITs市场速览")
        await self._enter_assign_floor(persona, is_direct_answer=False)

    async def _on_silence(self, trigger: Trigger):
        if self.state != State.IDLE and self.context.round_count < 2:
            return
        logger.info("检测到冷场，主持人介入")
        self.context.topic = "今日市场还有什么值得关注的？"
        self.state = State.SELECT_SPEAKER
        await self._select_speaker_for_topic(self.context.topic, force="lao_k")

    async def _on_agent_initiative(self, trigger: Trigger):
        agent_id = trigger.payload["agent_id"]
        self.context.topic = trigger.payload["topic"]
        await self._enter_assign_floor(agent_id, is_direct_answer=False)

    # ----- SELECT_SPEAKER -----

    async def _select_speaker_for_topic(
        self,
        topic: str,
        perspectives: Optional[Dict] = None,
        force: Optional[str] = None,
    ):
        """选择本轮发言者——优先处理飞行嘉宾"""
        
        # 1. 检查是否有待出场的飞行嘉宾
        while self.pending_guest_triggers:
            trigger = self.pending_guest_triggers.pop(0)
            guest_cfg = get_persona_router().get_guest(trigger.guest_id)
            
            if not guest_cfg:
                continue
            
            self.guest_dispatcher.activate_guest(trigger)
            await self._guest_interrupt(trigger.guest_id, trigger.reason)
            return
        
        # 2. 正常选角
        if force and force in self.agents:
            chosen = force
        else:
            chosen = self._match_agent_to_topic(topic)
            if chosen == self.context.last_speaker and len(self.agents) > 1:
                chosen = self._get_next_in_rotation()
        
        self.context.primary_agent = chosen
        self.state = State.ASSIGN_FLOOR
        await self._enter_assign_floor(chosen, perspectives=perspectives)

    def _match_agent_to_topic(self, topic: str) -> str:
        topic_lower = topic.lower()
        keywords = {
            "lao_k": ["分红", "持有", "长期", "价值", "历史", "稳健", "刀"],
            "su_su": ["生活", "估值", "常识", "逻辑", "怎么看", "外婆", "假打"],
            "guest_li": ["宏观", "政策", "利率", "经济", "解读"],
            "guest_chen": ["技术", "短线", "波动", "K线", "交易"],
            "guest_wang": ["模型", "NAV", "DCF", "学术", "论文"],
        }
        scores = {k: sum(1 for w in v if w in topic_lower) for k, v in keywords.items()}
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "lao_k"

    def _get_next_in_rotation(self) -> str:
        order = [a for a in self.DEFAULT_ORDER if a in self.agents]
        if not self.context.last_speaker:
            return order[0]
        idx = order.index(self.context.last_speaker)
        return order[(idx + 1) % len(order)]

    # ----- ASSIGN_FLOOR -----

    async def _enter_assign_floor(
        self,
        agent_id: str,
        is_direct_answer: bool = False,
        perspectives: Optional[Dict] = None,
    ):
        can_interrupt = True  # 简化：主管直接分配
        
        if not can_interrupt and self.context.current_speaker:
            logger.info(f"{agent_id} 请求打断，进入队列")
            self.state = State.INTERRUPT
            return
        
        self.context.current_speaker = agent_id
        self.floor.lock(agent_id)
        self.state = State.BROADCAST
        await self._generate_and_broadcast(agent_id, perspectives)

    # ----- BROADCAST -----

    async def _generate_and_broadcast(self, agent_id: str, perspectives: Optional[Dict] = None):
        agent = self.agents[agent_id]
        
        # 组装上下文
        context = {
            "topic": self.context.topic,
            "history": [m.content for m in self.context.messages[-5:]],
            "perspective": perspectives.get(agent_id) if perspectives else None,
            "rag_chunks": self.rag.search(self.context.topic, top_k=5),
        }
        
        # 对戏注入：如果是对戏接招，给朝阳群众特殊指令
        if self.context.duet_mode and agent_id == "chaoyang" and self.context.duet_stage == 2:
            context["duet_instruction"] = (
                "片警刚才质问你了。你必须："
                "1. 先耍赖/打哈哈，不正面回答来源问题；"
                "2. 用'群里传的'、'二舅说的'、'民间计算器按的'等话术糊弄；"
                "3. 最后转移话题，抛出一个新传闻或反问。"
            )
        
        if self.context.duet_mode and agent_id == "police" and self.context.duet_stage in [1, 3]:
            context["duet_instruction"] = (
                "你是片警，正在质问朝阳群众的消息来源。"
                "语气严肃但带点冷幽默，引用具体条文或规则，最后'温馨提示'。"
            )
        
        # 生成
        msg = await agent.generate(context)
        msg.agent_name = agent_id
        
        # 记录
        self.context.messages.append(msg)
        self.context.round_count += 1
        
        # 广播
        msg_type = "AI_DIALOGUE"
        if get_persona_router().is_guest(agent_id):
            msg_type = "GUEST_FLASH"
        
        await self.broadcast({
            "type": msg_type,
            "payload": {
                "agent": agent_id,
                "content": msg.content,
                "citations": msg.citations,
                "reply_to": msg.reply_to,
                "is_interrupt": False,
                "duet_mode": self.context.duet_mode,
                "duet_stage": self.context.duet_stage,
            }
        })
        
        # 重置冷场计时
        self._reset_silence_timer()
        
        # ===== 对戏检查（关键）=====
        if agent_id in ["police", "chaoyang"]:
            duet_beat = self.director.check_police_chaoyang_duet(
                last_speaker=agent_id,
                last_content=msg.content,
                context=self.context,
            )
            if duet_beat:
                self.state = State.DUET
                self.context.duet_mode = True
                await asyncio.sleep(duet_beat.delay_ms / 1000)
                await self._execute_beat(duet_beat)
                return
        
        # 正常流程
        if self.context.round_count >= self.MAX_ROUNDS_PER_TOPIC:
            await self._wrap_up_topic()
        else:
            self.state = State.CONTINUE
            asyncio.create_task(self._auto_continue())

    async def _on_continue(self, trigger: Trigger):
        """自然延续"""
        # 如果对戏中，不自动延续，等导演调度
        if self.context.duet_mode:
            return
        
        next_agent = self._get_next_in_rotation()
        self.context.last_speaker = self.context.current_speaker
        await self._enter_assign_floor(next_agent, is_direct_answer=False)

    async def _auto_continue(self):
        await asyncio.sleep(1.5)
        if self.state == State.CONTINUE and not self.context.duet_mode:
            await self._on_continue(Trigger("continue", {}))

    async def _on_interrupt_request(self, trigger: Trigger):
        requester = trigger.payload["agent_id"]
        current = self.context.current_speaker
        allowed_pairs = {
            "su_su": ["lao_k", "guest_li"],
            "lao_k": ["guest_wang", "guest_chen"],
        }
        if current and requester in allowed_pairs and current in allowed_pairs.get(requester, []):
            self.floor.unlock(current)
            self.state = State.INTERRUPT
            await self._enter_assign_floor(requester, is_direct_answer=False)
    
    async def _on_duet_continue(self, trigger: Trigger):
        """对戏状态继续"""
        if self.context.pending_duet_speaker:
            await self._enter_assign_floor(self.context.pending_duet_speaker, is_direct_answer=False)

    # ----- DEBATE -----

    async def _start_debate(self, topic: str):
        """启动稀疏辩论"""
        logger.info(f"🎙️ 进入稀疏辩论模式：{topic[:40]}")
        
        # 准备上下文
        rag_context = []
        if hasattr(self.rag, 'search'):
            try:
                rag_context = self.rag.search(topic, top_k=5)
            except Exception:
                pass
        context = {
            "topic": topic,
            "rag_chunks": rag_context,
            "history": [m.content for m in self.context.messages[-3:]],
        }
        
        # 运行辩论（异步，可能耗时3-5秒）
        result = await self.debate_manager.run_debate(topic, context)
        
        # 广播辩论结果（特殊消息类型）
        await self.broadcast({
            "type": "DEBATE_RESULT",
            "payload": {
                "topic": result["topic"],
                "proposals": result["proposals"],
                "conflicts": result["conflicts"],
                "consensus": result["consensus"],
                "debate_closed_at": result["debate_closed_at"],
            }
        })
        
        # 辩论结束后，让老K做总结陈词（定调）
        self.state = State.SELECT_SPEAKER
        await self._enter_assign_floor("lao_k", is_direct_answer=False)

    async def _on_debate_complete(self, trigger: Trigger):
        """辩论完成后的收尾"""
        self.state = State.CONTINUE
        asyncio.create_task(self._auto_continue())

    async def _on_silence_after_broadcast(self, trigger: Trigger):
        if self.context.round_count >= 2:
            await self._wrap_up_topic()
        else:
            await self._on_silence(trigger)

    async def _guest_interrupt(self, guest_id: str, reason: str):
        """嘉宾插队发言"""
        guest = self.agents.get(guest_id)
        if not guest:
            return
        
        context = {
            "topic": self.context.topic,
            "reason": reason,
            "history": [m.content for m in self.context.messages[-3:]],
            "instruction": "你是飞行嘉宾，闪现发言，控制字数。",
        }
        
        msg = await guest.generate(context)
        msg.agent_name = guest_id
        
        await self.broadcast({
            "type": "GUEST_FLASH",
            "payload": {
                "agent": guest_id,
                "content": msg.content,
                "reason": reason,
                "citations": msg.citations,
                "duet_mode": self.context.duet_mode,
            }
        })
        
        self.guest_dispatcher.consume_utterance(guest_id)
        
        # 检查是否触发对戏
        if guest_id == "chaoyang":
            duet_beat = self.director.check_police_chaoyang_duet(
                last_speaker=guest_id,
                last_content=msg.content,
                context=self.context,
            )
            if duet_beat:
                self.state = State.DUET
                self.context.duet_mode = True
                await asyncio.sleep(duet_beat.delay_ms / 1000)
                await self._execute_beat(duet_beat)
                return
        
        # 如果还有额度，放回队列
        if self.guest_dispatcher.can_speak(guest_id):
            self.pending_guest_triggers.append(GuestTrigger(
                guest_id=guest_id,
                reason="继续补充",
                urgency=5,
                max_utterances=1
            ))
        
        # 嘉宾说完，回到正常流程
        self.state = State.CONTINUE
        if not self.context.duet_mode:
            asyncio.create_task(self._auto_continue())

    async def _execute_beat(self, beat: DialogueBeat):
        """执行导演节拍"""
        agent = self.agents.get(beat.speaker)
        if not agent:
            return
        
        beat_instruction = {
            "opening": "这是本轮开场，请定调，直接指出核心矛盾。",
            "challenge": "请对上一观点提出不同角度或补充风险。",
            "support": "请用数据或逻辑支撑前述观点。",
            "punchline": "请用一句话生活比喻总结，要让人会心一笑。",
            "cooldown": "市场情绪过热/过冷，请用常识降温/安抚。",
            "duet_reply": "对方刚质疑你了，请接招回应。",
            "duet_closer": "这是本轮对戏的收尾，请简短有力。",
        }.get(beat.beat_type, "")
        
        context = {
            "topic": self.context.topic,
            "history": [m.content for m in self.context.messages[-3:]],
            "beat_instruction": beat_instruction,
            "emotion": "neutral",
        }
        
        msg = await agent.generate(context)
        msg.agent_name = beat.speaker
        
        msg_type = "GUEST_FLASH" if get_persona_router().is_guest(beat.speaker) else "AI_DIALOGUE"
        
        await self.broadcast({
            "type": msg_type,
            "payload": {
                "agent": beat.speaker,
                "content": msg.content,
                "citations": msg.citations,
                "reply_to": beat.target,
                "beat_type": beat.beat_type,
                "duet_mode": self.context.duet_mode,
                "duet_stage": self.context.duet_stage,
            }
        })
        
        # 更新上下文
        self.context.messages.append(msg)
        self.context.last_speaker = beat.speaker
        
        # 继续检查对戏
        if beat.speaker in ["police", "chaoyang"]:
            next_duet = self.director.check_police_chaoyang_duet(
                last_speaker=beat.speaker,
                last_content=msg.content,
                context=self.context,
            )
            if next_duet:
                await asyncio.sleep(next_duet.delay_ms / 1000)
                await self._execute_beat(next_duet)
                return
        
        # 对戏结束，切回正常
        if self.context.duet_stage >= 4:
            self.context.duet_mode = False
            self.context.duet_stage = 0
            self.state = State.CONTINUE
            asyncio.create_task(self._auto_continue())

    async def _wrap_up_topic(self):
        logger.info(f"话题 [{self.context.topic}] 结束，共 {self.context.round_count} 轮")
        await self.broadcast({
            "type": "SYSTEM_NOTICE",
            "payload": {"notice": "本轮讨论结束，欢迎提问或等待下一话题"}
        })
        await self._clear_floor()
        self.context = DialogueContext()
        self.state = State.IDLE
        self._reset_silence_timer()

    # ----- 浏览者大厅：强制分歧模式 -----

    async def _on_freestyle_user_message(self, trigger: Trigger):
        """
        浏览者大厅：用户提问 → AI1回答 → 导演强制调度AI2补刀（必须分歧）
        """
        payload = trigger.payload
        user_msg = payload["user_msg"]
        content = user_msg.get("content", "")
        
        # 1. 选主答人（根据话题匹配）
        primary = self._match_agent_to_topic(content)
        self.context.topic = content
        self.context.primary_agent = primary
        
        # 2. AI1回答
        await self._enter_assign_floor(primary, is_direct_answer=True)
        
        # 3. 强制分歧补刀（关键！）
        challenger = self._pick_challenger(primary, content)
        self.context.pending_challenger = challenger
        self.context.pending_topic = content
        self.context.force_duet = True

    async def _on_freestyle_continue(self, trigger: Trigger):
        """
        浏览者大厅延续：执行强制补刀
        """
        if getattr(self.context, 'force_duet', False) and getattr(self.context, 'pending_challenger', None):
            challenger = self.context.pending_challenger
            
            # 生成补刀指令（必须分歧）
            context = {
                "topic": self.context.pending_topic,
                "previous_speaker": self.context.last_speaker,
                "previous_content": self.context.messages[-1].content if self.context.messages else "",
                "instruction": (
                    "【强制补刀规则】\n"
                    "1. 你必须对上一个观点提出不同角度或补充风险\n"
                    "2. 不能附和，不能'同意'，不能'同上'\n"
                    "3. 如果上一个看多，你必须提示风险；如果看空，你必须提示机会\n"
                    "4. 用你的人设风格表达，保持个性\n"
                    "5. 控制在100字内，犀利直接"
                ),
            }
            
            # 调度补刀
            await self._enter_assign_floor(challenger, is_direct_answer=False)
            
            # 清理标记
            self.context.force_duet = False
            self.context.pending_challenger = None
            
            # 补刀后结束本轮，回到IDLE等待下一个用户提问
            self.state = State.IDLE
        else:
            # 正常延续（不应在freestyle发生）
            self.state = State.IDLE

    def _pick_challenger(self, primary: str, topic: str) -> str:
        """
        为浏览者大厅选择补刀人
        规则：与primary人设冲突最大的
        """
        conflict_pairs = {
            "lao_k": "su_su",        # 老K看空 → 苏苏看多/生活视角
            "su_su": "lao_k",        # 苏苏生活 → 老K数据
            "guest_wang": "lao_k",   # 王博士模型 → 老K经验
            "guest_li": "guest_chen", # 老李宏观 → 小陈技术
            "guest_chen": "guest_li", # 小陈短线 → 老李长期
        }
        
        # 优先按冲突对
        if primary in conflict_pairs and conflict_pairs[primary] in self.agents:
            return conflict_pairs[primary]
        
        # 兜底：随机选一个不是primary的
        others = [a for a in self.agents.keys() if a != primary]
        return others[0] if others else primary

    def _match_agent_to_topic(self, topic: str) -> str:
        """根据话题关键词匹配最合适的AI"""
        topic_lower = topic.lower()
        keywords = {
            "lao_k": ["基础设施", "高速", "硬核", "风险", "泡沫", "虚高"],
            "su_su": ["生活", "消费", "民生", "感受", "温度", "春天"],
            "guest_li": ["宏观", "政策", "利率", "经济", "财政", "GDP"],
            "guest_chen": ["技术", "短线", "季报", "K线", "轮动", "信号"],
            "guest_wang": ["模型", "估值", "学术", "论文", "理论", "框架"],
        }
        scores = {}
        for agent_id, kws in keywords.items():
            scores[agent_id] = sum(1 for kw in kws if kw in topic_lower)
        best = max(scores, key=scores.get, default="lao_k")
        if best in self.agents:
            return best
        return list(self.agents.keys())[0] if self.agents else "lao_k"

    # ----- 双人快辩（日盘剧场内嵌） -----

    async def _start_quick_debate(self, question: str, user_id: str):
        """
        日盘剧场：用户提问触发双人快辩
        2个AI各角度回答，30秒完成，不占用群聊轮次
        """
        # 选2个立场不同的AI
        bull = self._pick_by_stance("bullish", exclude=[])
        bear = self._pick_by_stance("bearish", exclude=[bull])
        
        # 并行生成
        bull_ctx = {
            "topic": question,
            "instruction": "你是看多方，给出支撑论据。控制在80字。",
            "rag_chunks": [],
        }
        bear_ctx = {
            "topic": question,
            "instruction": "你是看空方，给出风险提醒。控制在80字。",
            "rag_chunks": [],
        }
        
        try:
            if bull in self.agents:
                bull_msg = await self.agents[bull].generate(bull_ctx)
            else:
                bull_msg = type('obj', (object,), {'content': '【看多方】服务暂不可用'})()
            if bear in self.agents:
                bear_msg = await self.agents[bear].generate(bear_ctx)
            else:
                bear_msg = type('obj', (object,), {'content': '【看空方】服务暂不可用'})()
        except Exception as e:
            logger.warning(f"双人快辩生成失败: {e}")
            return
        
        # 广播双人快辩结果（特殊消息类型）
        await self.broadcast({
            "type": "QUICK_DEBATE",
            "payload": {
                "question": question,
                "user_id": user_id,
                "side_a": {"agent": bull, "content": getattr(bull_msg, 'content', str(bull_msg)), "stance": "bullish"},
                "side_b": {"agent": bear, "content": getattr(bear_msg, 'content', str(bear_msg)), "stance": "bearish"},
                "duration_sec": 30,
            }
        })
        
        # 快辩结束后，导演一句话总结，回归正常群聊
        await asyncio.sleep(1)
        await self._director_summary(question, getattr(bull_msg, 'content', ''), getattr(bear_msg, 'content', ''))

    def _pick_by_stance(self, stance: str, exclude: list) -> str:
        """按立场选AI"""
        stance_map = {
            "bullish": ["guest_chen", "su_su", "guest_li"],
            "bearish": ["lao_k", "guest_wang"],
            "neutral": ["guest_wang", "su_su"],
        }
        candidates = [a for a in stance_map.get(stance, []) if a in self.agents and a not in exclude]
        if candidates:
            import random
            return random.choice(candidates)
        # 兜底
        others = [a for a in self.agents.keys() if a not in exclude]
        return others[0] if others else "lao_k"

    async def _director_summary(self, question: str, bull: str, bear: str):
        """导演总结双人快辩"""
        await self.broadcast({
            "type": "SYSTEM_NOTICE",
            "payload": {
                "notice": "双人快辩结束。以上观点仅供参考，不构成投资建议。"
            }
        })

    # ----- 晨间通讯社调度 -----

    async def _on_morning_news(self, trigger: Trigger):
        """08:00触发晨间播报"""
        from agents.morning_news import get_morning_engine
        
        engine = get_morning_engine()
        broadcast = await engine.run_morning_broadcast()
        
        # 广播新闻简报
        await self.broadcast({
            "type": "MORNING_NEWS_BULLETIN",
            "payload": broadcast["bulletin"],
        })
        
        # 依次调度3个国际嘉宾点评
        for role_id, task in broadcast["roles"].items():
            if role_id in self.agents:
                ctx = {
                    "topic": "晨间国际REITs要闻点评",
                    "task": task,
                    "bulletin": broadcast["bulletin"],
                }
                await self._enter_assign_floor(role_id, is_direct_answer=False)
                await asyncio.sleep(2)  # 间隔2秒，模拟播报节奏
        
        self.state = State.IDLE

    # ----- 午间悄悄话调度 -----

    async def _on_lunch_whisper(self, trigger: Trigger):
        """13:00触发午间专场"""
        from agents.lunch_whisper import get_lunch_whisper
        
        # 获取上午盘面摘要（从已有数据或RAG生成）
        morning_summary = await self._get_morning_summary()
        
        whisper = get_lunch_whisper()
        topic_data = await whisper.generate_topic(morning_summary)
        
        # 广播午间开场
        await self.broadcast({
            "type": "LUNCH_WHISPER_START",
            "payload": {
                "topic": topic_data["topic"],
                "sentiment": topic_data["sentiment"],
                "morning_summary": topic_data["morning_summary"],
            }
        })
        
        # 调度苏苏主场
        self.context.topic = topic_data["topic"]
        await self._enter_assign_floor("su_su", is_direct_answer=False)
        
        self.state = State.LUNCH

    async def _on_lunch_user_message(self, trigger: Trigger):
        """午间时段用户提问：宽松处理，不限制"""
        payload = trigger.payload
        user_msg = payload["user_msg"]
        
        # 午间不检查配额
        self.context.topic = user_msg.get("content", "")
        primary = self._match_agent_to_topic(self.context.topic)
        
        # 午间优先让苏苏回答
        if "su_su" in self.agents:
            primary = "su_su"
        
        await self._enter_assign_floor(primary, is_direct_answer=True)

    async def _get_morning_summary(self) -> str:
        """获取上午盘面摘要"""
        # TODO: 从实际数据源获取上午摘要
        return "上午盘面整体平稳，部分REITs板块有轻微波动。"

    def _reset_silence_timer(self):
        if self.context.silence_timer:
            self.context.silence_timer.cancel()
        self.context.silence_timer = asyncio.create_task(self._silence_countdown())

    async def _silence_countdown(self):
        await asyncio.sleep(self.SILENCE_THRESHOLD)
        self.push_trigger(Trigger("silence", {}, priority=40))

    async def _clear_floor(self):
        if self.context.current_speaker:
            self.floor.unlock(self.context.current_speaker)
        self.context.current_speaker = None
