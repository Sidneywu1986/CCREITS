#!/usr/bin/env python3
"""
稀疏辩论管理器 (Sparse Debate Manager)
模式：独立生成 → 邻居交换 → 各自修正 → 导演聚合分歧点
"""

import os
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger("debate_manager")


@dataclass
class DebateProposal:
    agent_id: str
    round_0: str = ""           # 初始独立观点（投资备忘录）
    round_1: str = ""           # 看过邻居后的修正观点
    stance: str = "neutral"     # bullish | bearish | neutral
    confidence: float = 0.5


@dataclass
class ConflictPoint:
    type: str                   # "核心分歧" | "数据争议" | "估值差异"
    between: List[str]          # ["老K", "苏苏"]
    side_a: str                 # 甲方观点摘要
    side_b: str                 # 乙方观点摘要
    highlight: str              # 一句话总结分歧本质


class DebateManager:
    """
    稀疏辩论管理器
    拓扑规则：每人只和指定邻居交换，模拟真实投研会的信息隔离
    """

    # 辩论邻居拓扑（有向图：key 向 value 展示观点）
    # 映射到项目中的 persona_id: lao_k, su_su, lao_li, xiao_chen, wang_bo
    DEBATE_TOPOLOGY = {
        "lao_k": ["wang_bo"],      # 老K ↔ 王博士：市井 vs 学术
        "wang_bo": ["lao_k"],
        "su_su": ["lao_li"],         # 苏苏 ↔ 老李：生活 vs 数据
        "lao_li": ["su_su"],
        "xiao_chen": ["lao_k"],       # 小陈 → 老K：短线信号汇报
    }

    # 触发辩论的关键词
    DEBATE_TRIGGERS = [
        "怎么看", "能不能买", "值不值得", "估值", "多空", "争议",
        "分歧", "值得投", "上车", "下车", "抄底", "逃顶", "观点",
        "为什么涨", "为什么跌", "未来", "前景", "潜力", "风险大不大"
    ]

    # agent_id → persona_router 中的 id 映射（一致，无需额外映射）
    AGENT_NAME_MAP = {
        "lao_k": "老K",
        "su_su": "苏苏",
        "lao_li": "老李",
        "xiao_chen": "小陈",
        "wang_bo": "王博士",
    }

    def __init__(self, persona_router=None):
        self.persona_router = persona_router
        self.proposals: Dict[str, DebateProposal] = {}
        self.conflicts: List[ConflictPoint] = []
        self.debate_log: List[Dict] = []

    @classmethod
    def should_debate(cls, query: str) -> bool:
        """判断是否应该进入辩论模式"""
        q = query.lower()
        return any(t in q for t in cls.DEBATE_TRIGGERS)

    async def run_debate(self, topic: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        运行完整辩论流程（2轮）
        返回：聚合结果，供前端展示
        """
        logger.info(f"🎙️ 稀疏辩论开始：{topic[:40]}...")
        self.proposals.clear()
        self.conflicts.clear()

        # ===== Round 0：独立撰写投资备忘录 =====
        logger.info("Round 0: 独立生成初始观点...")
        round0_tasks = []
        for agent_id in self.DEBATE_TOPOLOGY.keys():
            task = self._generate_proposal(agent_id, topic, context, round_num=0)
            round0_tasks.append(task)

        round0_results = await asyncio.gather(*round0_tasks, return_exceptions=True)
        for r in round0_results:
            if isinstance(r, Exception):
                logger.warning(f"Round 0 生成失败: {r}")
                continue
            self.proposals[r.agent_id] = r

        # ===== Round 1：邻居交换 + 修正 =====
        logger.info("Round 1: 邻居交换并修正...")
        round1_tasks = []
        for agent_id, proposal in self.proposals.items():
            neighbors = self.DEBATE_TOPOLOGY.get(agent_id, [])
            neighbor_views = {
                n: self.proposals[n].round_0
                for n in neighbors
                if n in self.proposals
            }

            task = self._revise_proposal(agent_id, topic, context, proposal, neighbor_views)
            round1_tasks.append(task)

        round1_results = await asyncio.gather(*round1_tasks, return_exceptions=True)
        for r in round1_results:
            if isinstance(r, Exception):
                continue
            if r.agent_id in self.proposals:
                self.proposals[r.agent_id].round_1 = r.round_1
                self.proposals[r.agent_id].stance = r.stance

        # ===== 导演聚合：提取分歧点 =====
        self.conflicts = self._extract_conflicts()

        # 组装最终输出
        return {
            "topic": topic,
            "round_count": 2,
            "proposals": {
                aid: {
                    "agent": aid,
                    "agent_name": self._agent_name(aid),
                    "round_0": p.round_0,
                    "round_1": p.round_1,
                    "stance": p.stance,
                    "confidence": p.confidence,
                }
                for aid, p in self.proposals.items()
            },
            "conflicts": [
                {
                    "type": c.type,
                    "between": c.between,
                    "side_a": c.side_a,
                    "side_b": c.side_b,
                    "highlight": c.highlight,
                }
                for c in self.conflicts
            ],
            "consensus": self._extract_consensus(),
            "debate_closed_at": datetime.now().isoformat(),
        }

    async def _generate_proposal(
        self,
        agent_id: str,
        topic: str,
        context: Dict,
        round_num: int
    ) -> DebateProposal:
        """生成独立投资备忘录"""
        system_prompt = self._build_system_prompt(agent_id)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": (
                f"【独立投资备忘录】\n"
                f"话题：{topic}\n\n"
                f"你是本场投研会的独立分析师。请基于你的专业视角，"
                f"独立撰写一份关于该话题的投资备忘录。\n"
                f"要求：\n"
                f"1. 明确立场：看多/看空/中性\n"
                f"2. 列出2-3条核心论据（带数据或逻辑）\n"
                f"3. 指出1-2个关键风险点\n"
                f"4. 禁止参考他人观点，禁止使用'同上'、'同意'等附和词\n"
                f"5. 控制在150字内"
            )},
        ]

        content = await self._call_llm(messages, agent_id)
        stance = self._parse_stance(content)

        return DebateProposal(
            agent_id=agent_id,
            round_0=content,
            stance=stance,
        )

    async def _revise_proposal(
        self,
        agent_id: str,
        topic: str,
        context: Dict,
        my_proposal: DebateProposal,
        neighbor_views: Dict[str, str],
    ) -> DebateProposal:
        """看过邻居观点后修正"""
        system_prompt = self._build_system_prompt(agent_id)

        neighbor_text = "\n\n".join([
            f"【{self._agent_name(nid)}的观点】\n{view[:200]}"
            for nid, view in neighbor_views.items()
        ])

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": (
                f"【修正投资备忘录】\n"
                f"话题：{topic}\n\n"
                f"你刚刚独立写了一份投资备忘录：\n"
                f"{my_proposal.round_0}\n\n"
                f"现在你的邻居提出了不同角度：\n"
                f"{neighbor_text}\n\n"
                f"要求：\n"
                f"1. 审视自己的立场，可以坚持、修正或补充\n"
                f"2. 如果邻居的观点有道理，请吸收并说明为什么修正\n"
                f"3. 如果坚持原观点，请反驳邻居的论据漏洞\n"
                f"4. 输出修正后的完整备忘录（立场+论据+风险）\n"
                f"5. 控制在150字内"
            )},
        ]

        content = await self._call_llm(messages, agent_id)
        stance = self._parse_stance(content)

        return DebateProposal(
            agent_id=agent_id,
            round_1=content,
            stance=stance,
        )

    async def _call_llm(self, messages: List[Dict], agent_id: str) -> str:
        """调用 LLM 生成内容"""
        try:
            from core.config import settings
            from openai import AsyncOpenAI
        except ImportError:
            logger.warning("LLM dependencies not available, returning placeholder")
            return f"【{self._agent_name(agent_id)}】抱歉，AI服务暂时不可用。"

        try:
            base_url = settings.LLM_CONFIG["deepseek_pro"]["base_url"]
            if not base_url.endswith("/v1"):
                base_url = base_url.rstrip("/") + "/v1"
            api_key = os.getenv("DEEPSEEK_API_KEY", settings.LLM_CONFIG["deepseek_pro"]["api_key"])
            if not api_key:
                return f"【{self._agent_name(agent_id)}】API Key 未配置。"

            client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=30)
            response = await client.chat.completions.create(
                model=settings.LLM_CONFIG["deepseek_pro"]["model"],
                messages=messages,
                temperature=0.7,
                max_tokens=512,
                stream=False,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"LLM call failed for {agent_id}: {e}")
            return f"【{self._agent_name(agent_id)}】服务暂时不可用。"

    def _build_system_prompt(self, agent_id: str) -> str:
        """从 persona_router 获取 system_prompt"""
        if self.persona_router:
            cfg = self.persona_router.registry.get(agent_id)
            if cfg:
                return cfg.system_prompt
        # 兜底
        return "你是一位REITs分析师。"

    def _extract_conflicts(self) -> List[ConflictPoint]:
        """从修正后的观点中提取分歧点"""
        conflicts = []

        # 冲突对定义（使用项目中的 persona_id）
        conflict_pairs = [
            ("lao_k", "su_su", "核心分歧"),
            ("lao_k", "wang_bo", "估值差异"),
            ("su_su", "lao_li", "数据争议"),
            ("xiao_chen", "lao_k", "周期之争"),
        ]

        for a_id, b_id, ctype in conflict_pairs:
            if a_id not in self.proposals or b_id not in self.proposals:
                continue

            a = self.proposals[a_id]
            b = self.proposals[b_id]

            # 只有立场相反才算分歧
            if a.stance == b.stance:
                continue

            a_text = a.round_1 or a.round_0
            b_text = b.round_1 or b.round_0

            conflicts.append(ConflictPoint(
                type=ctype,
                between=[self._agent_name(a_id), self._agent_name(b_id)],
                side_a=a_text[:80] + ("..." if len(a_text) > 80 else ""),
                side_b=b_text[:80] + ("..." if len(b_text) > 80 else ""),
                highlight=self._summarize_conflict(a_id, b_id, a.stance, b.stance),
            ))

        return conflicts

    def _extract_consensus(self) -> Optional[str]:
        """提取共识（如果所有人都同意）"""
        stances = [p.stance for p in self.proposals.values()]
        if not stances:
            return None

        if all(s == "bullish" for s in stances):
            return "全员看多，但需警惕一致性风险"
        elif all(s == "bearish" for s in stances):
            return "全员看空，或存在错杀机会"
        elif stances.count("neutral") >= len(stances) // 2:
            return "整体偏观望，等待更明确信号"

        bullish = stances.count("bullish")
        bearish = stances.count("bearish")
        if bullish > bearish:
            return f"多数看多（{bullish}/{len(stances)}），分歧集中在风险点"
        elif bearish > bullish:
            return f"多数看空（{bearish}/{len(stances)}），分歧集中在底部位置"
        return "多空均衡，市场处于关键决策窗口"

    def _parse_stance(self, text: str) -> str:
        """从文本中解析立场"""
        t = text.lower()
        bullish = ["看多", "看好", "推荐", "买入", "机会", "底部", "反弹", "上行", "配置价值"]
        bearish = ["看空", "谨慎", "风险", "卖出", "承压", "下行", "泡沫", "高估", "警惕"]

        b_score = sum(1 for w in bullish if w in t)
        s_score = sum(1 for w in bearish if w in t)

        if b_score > s_score + 1:
            return "bullish"
        elif s_score > b_score + 1:
            return "bearish"
        return "neutral"

    def _summarize_conflict(self, a_id: str, b_id: str, a_stance: str, b_stance: str) -> str:
        """一句话总结分歧"""
        templates = {
            ("lao_k", "su_su"): "老K看风险，苏苏看韧性，核心在对底层资产现金流的信心",
            ("lao_k", "wang_bo"): "老K凭经验喊贵，王博士算模型说合理，估值方法论之争",
            ("su_su", "lao_li"): "苏苏讲生活常识，老李要历史数据，定性vs定量之争",
            ("xiao_chen", "lao_k"): "小陈看短线技术信号，老K看长期价值，周期维度之争",
        }
        key = (a_id, b_id)
        if key not in templates:
            key = (b_id, a_id)
        return templates.get(key, "方法论与视角差异")

    def _agent_name(self, agent_id: str) -> str:
        return self.AGENT_NAME_MAP.get(agent_id, agent_id)


# 全局单例
_debate_manager: Optional[DebateManager] = None

def get_debate_manager(persona_router=None) -> DebateManager:
    global _debate_manager
    if _debate_manager is None:
        _debate_manager = DebateManager(persona_router)
    return _debate_manager
