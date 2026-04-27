#!/usr/bin/env python3
"""
会话导演（Session Director）—— 控制递话、翻包袱、情绪节奏
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class DialogueBeat:
    """一个'节拍' = 谁说话 + 说什么类型的话"""
    speaker: str
    beat_type: str   # "opening" | "challenge" | "support" | "punchline" | "cooldown"
    target: Optional[str] = None  # 回应谁
    emotion_override: Optional[str] = None


class SessionDirector:
    """
    导演规则：
    1. 老K开场（质疑/定调）
    2. 苏苏接话（软化/比喻）
    3. 特邀嘉宾补充（数据/学术）
    4. 不允许连续两人同一立场（必须有轻微冲突）
    5. 情绪极化时，自动插入"冷静角色"
    """

    def __init__(self, agents: List[str]):
        self.agents = agents
        self.beat_history: List[DialogueBeat] = []

    def design_scene(
        self,
        topic: str,
        sentiment: Dict,  # {score, emotion, intensity}
        perspectives: Dict[str, str],  # {agent: "bullish"|"bearish"|"neutral"}
        round_num: int,
    ) -> List[DialogueBeat]:
        """
        为当前话题设计对话节拍
        """
        beats = []
        emotion = sentiment.get("emotion", "neutral")

        # 规则1：第一轮，老K开场（如果是他主场）
        if round_num == 0 and "lao_k" in self.agents:
            beats.append(DialogueBeat(
                speaker="lao_k",
                beat_type="opening",
                emotion_override="sarcastic" if emotion == "greed" else "steady"
            ))

        # 规则2：第二轮，苏苏必须接话，且立场与老K不同或软化
        if round_num == 1 and "su_su" in self.agents and "lao_k" in self.agents:
            beats.append(DialogueBeat(
                speaker="su_su",
                beat_type="support" if perspectives.get("lao_k") == "bearish" else "challenge",
                target="lao_k"
            ))

        # 规则3：第三轮，特邀嘉宾（如果有）提供数据支撑
        guests = [a for a in self.agents if a not in ["lao_k", "su_su"]]
        if round_num == 2 and guests:
            beats.append(DialogueBeat(
                speaker=guests[0],
                beat_type="support",
                target="lao_k"
            ))

        # 规则4：第四轮，苏苏翻包袱（如果前面太学术）
        if round_num == 3 and "su_su" in self.agents:
            beats.append(DialogueBeat(
                speaker="su_su",
                beat_type="punchline",
                target=guests[0] if guests else "lao_k"
            ))

        # 规则5：情绪极化时，强制插入冷静
        if emotion in ["panic", "greed"] and round_num >= 2:
            cooler = "su_su" if emotion == "panic" else "lao_k"
            if cooler in self.agents:
                beats.append(DialogueBeat(
                    speaker=cooler,
                    beat_type="cooldown",
                    emotion_override="calm"
                ))

        self.beat_history.extend(beats)
        return beats

    def should_interrupt(self, current_speaker: str, requester: str, sentiment: str) -> bool:
        """
        打断规则：
        - 苏苏可以打断老K（软刀子）
        - 老K可以打断王博士（嫌太学术）
        - 恐慌/贪婪时，任何人可以打断以纠正极端观点
        """
        allowed = {
            "su_su": ["lao_k"],
            "lao_k": ["guest_wang", "guest_chen", "standard"],
        }

        if sentiment in ["panic", "greed"]:
            return True

        return requester in allowed and current_speaker in allowed.get(requester, [])

    def get_beat_instruction(self, beat_type: str) -> str:
        """根据节拍类型返回提示词"""
        return {
            "opening": "这是本轮开场，请定调，直接指出核心矛盾。结尾加一句'老K一刀'式扎心总结。",
            "challenge": "请对上一观点提出不同角度或补充风险。语气要有碰撞感。",
            "support": "请用数据或逻辑支撑前述观点。保持专业但不说教。",
            "punchline": "请用一句话生活比喻总结，要让人会心一笑或恍然大悟。",
            "cooldown": "市场情绪过热/过冷，请用常识降温/安抚。不要堆砌术语。",
        }.get(beat_type, "")

    def get_next_beat(self) -> Optional[DialogueBeat]:
        """取出下一个节拍"""
        if not self.beat_history:
            return None
        return self.beat_history.pop(0)
