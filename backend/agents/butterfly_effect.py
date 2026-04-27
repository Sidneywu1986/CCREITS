#!/usr/bin/env python3
"""
蝴蝶效应触发器
用户提问 → 概率触发AI自发讨论
触发率 = 0.8 / sqrt(在线人数)
"""

import random
import math
import logging
from typing import List, Optional

logger = logging.getLogger("butterfly_effect")


class ButterflyTrigger:
    """
    主线5：提问引发AI自发讨论
    人少时高触发（80%），人多时低触发（1人80%，5人36%，10人25%，50人11%）
    """
    
    # 触发关键词
    KEYWORDS = [
        "怎么看", "为什么", "会不会", "能不能", "值得吗",
        "风险", "机会", "底部", "顶部", "泡沫", "黄金坑",
        "估值", "分红", "扩募", "溢价", "折价", "上车", "下车",
    ]
    
    def __init__(self):
        self.online_count: int = 1
        self.base_rate: float = 0.8
    
    def update_online_count(self, count: int):
        """WebSocket连接数更新"""
        self.online_count = max(count, 1)
    
    def should_trigger(self, query: str) -> bool:
        """
        判断是否应该触发蝴蝶效应
        条件：关键词命中 + 概率通过
        """
        query_lower = query.lower()
        
        # 1. 关键词检查
        keyword_hit = any(k in query_lower for k in self.KEYWORDS)
        if not keyword_hit:
            return False
        
        # 2. 动态概率计算
        # trigger_rate = 0.8 / sqrt(n)
        rate = self.base_rate / math.sqrt(self.online_count)
        rate = min(rate, 0.95)  # 上限95%
        
        roll = random.random()
        triggered = roll < rate
        
        logger.info(
            f"蝴蝶效应判定: 在线{self.online_count}人, 概率{rate:.1%}, "
            f"掷骰{roll:.3f}, 结果{'触发' if triggered else '未触发'}"
        )
        
        return triggered
    
    def get_current_rate(self) -> float:
        """返回当前触发概率（供前端展示）"""
        return self.base_rate / math.sqrt(self.online_count)


# 全局单例
_butterfly: Optional[ButterflyTrigger] = None

def get_butterfly_trigger() -> ButterflyTrigger:
    global _butterfly
    if _butterfly is None:
        _butterfly = ButterflyTrigger()
    return _butterfly
