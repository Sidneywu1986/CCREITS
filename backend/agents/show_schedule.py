#!/usr/bin/env python3
"""
演出日程表 v1.0
管理5条主线的时段、模式、AI阵容
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime, time
import logging

logger = logging.getLogger("show_schedule")


@dataclass
class ShowSlot:
    slot_id: str           # morning / afternoon / lunch / morning_news / freestyle
    name: str              # 显示名称
    start: time
    end: time
    mode: str              # showtime / freestyle / lunch / morning_news
    agent_roster: List[str]  # 本场出席AI
    user_quota: int = 0    # 每人限问次数（0=不限）
    description: str = ""


class ShowSchedule:
    """
    全天5时段调度
    """
    
    SLOTS = {
        "morning_news": ShowSlot(
            slot_id="morning_news",
            name="🌍 晨间通讯社",
            start=time(8, 0),
            end=time(8, 50),
            mode="morning_news",
            agent_roster=["guo_de_gang", "smith", "mei_de_chu"],  # 锅的刚、史密斯、美的储
            user_quota=0,
            description="欧美隔夜REITs市场要闻播报",
        ),
        "morning": ShowSlot(
            slot_id="morning",
            name="🎭 早盘热点剧场",
            start=time(9, 30),
            end=time(10, 15),
            mode="showtime",
            agent_roster=["lao_k", "su_su", "guest_li", "guest_chen", "guest_wang"],
            user_quota=1,  # 每人每场限1问
            description="5人全阵容，用户限1问，可触发双人快辩",
        ),
        "lunch": ShowSlot(
            slot_id="lunch",
            name="🌿 午间悄悄话",
            start=time(13, 0),
            end=time(13, 50),
            mode="lunch",
            agent_roster=["lao_k", "su_su"],  # 苏苏主场，老K陪衬
            user_quota=0,
            description="轻松氛围，可回顾上午盘面",
        ),
        "afternoon": ShowSlot(
            slot_id="afternoon",
            name="🎭 午盘热点剧场",
            start=time(14, 0),
            end=time(14, 45),
            mode="showtime",
            agent_roster=["lao_k", "su_su", "guest_li", "guest_chen", "guest_wang"],
            user_quota=1,
            description="5人全阵容，用户限1问，可触发双人快辩",
        ),
        "freestyle": ShowSlot(
            slot_id="freestyle",
            name="💬 浏览者大厅",
            start=time(0, 0),  # 兜底时段
            end=time(23, 59),
            mode="freestyle",
            agent_roster=["lao_k", "su_su", "guest_li", "guest_chen", "guest_wang"],
            user_quota=0,
            description="强制分歧模式：回答→补刀，必须立场相反",
        ),
    }

    def current_slot(self) -> Optional[ShowSlot]:
        """返回当前时段配置"""
        now = datetime.now().time()
        
        # 按优先级匹配（精确时段优先于兜底）
        for key in ["morning_news", "morning", "lunch", "afternoon"]:
            slot = self.SLOTS[key]
            if slot.start <= now <= slot.end:
                return slot
        
        # 非演出时段 = 浏览者大厅
        return self.SLOTS["freestyle"]

    def get_next_slot(self) -> Optional[ShowSlot]:
        """返回下一个即将开始的时段（用于倒计时）"""
        now = datetime.now()
        today_slots = []
        for key in ["morning_news", "morning", "lunch", "afternoon"]:
            slot = self.SLOTS[key]
            slot_dt = datetime.combine(now.date(), slot.start)
            if slot_dt > now:
                today_slots.append((slot_dt, slot))
        
        if today_slots:
            today_slots.sort(key=lambda x: x[0])
            return today_slots[0][1]
        return None

    def countdown_to_next(self) -> Optional[str]:
        """返回距离下一场的倒计时"""
        next_slot = self.get_next_slot()
        if not next_slot:
            return None
        
        now = datetime.now()
        next_dt = datetime.combine(now.date(), next_slot.start)
        delta = next_dt - now
        
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def is_showtime(self) -> bool:
        """是否在日盘剧场时段（上午或下午）"""
        slot = self.current_slot()
        return slot.mode == "showtime"

    def is_freestyle(self) -> bool:
        """是否在浏览者大厅时段"""
        slot = self.current_slot()
        return slot.mode == "freestyle"


# 全局单例
_schedule: Optional[ShowSchedule] = None

def get_schedule() -> ShowSchedule:
    global _schedule
    if _schedule is None:
        _schedule = ShowSchedule()
    return _schedule
