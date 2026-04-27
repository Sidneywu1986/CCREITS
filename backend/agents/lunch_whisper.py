#!/usr/bin/env python3
"""
午间悄悄话主题生成器
13:00-13:50，轻松氛围，苏苏主场
"""

import random
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger("lunch_whisper")


class LunchWhisper:
    """
    午间专场主题生成
    规则：轻松、生活化，可简要回顾上午盘面
    """
    
    TOPIC_TEMPLATES = {
        "calm": [  # 上午盘面平稳
            "午休时看盘 vs 睡觉，哪个更亏？",
            "如果REITs分红像工资，你打算怎么花？",
            "聊聊你最想投资的'理想生活场景'",
            "老K今天没亏钱，苏苏怎么'打击'他？",
            "下午开盘前，做什么能让自己不冲动？",
        ],
        "bullish": [  # 上午涨
            "早盘涨了点，午休该庆祝还是该冷静？",
            "老K今天赚了，苏苏怎么让他别飘？",
            "如果分红到账了，先还债还是先消费？",
            "聊聊你因为'贪心'错过的最佳卖出点",
        ],
        "bearish": [  # 上午跌
            "早盘跌惨了，午休怎么让自己不割肉？",
            "苏苏，老K今天亏了，你怎么安慰他？",
            "聊聊你因为'恐慌'错过的最佳买入点",
            "REITs跌了，但生活还要继续，下午怎么调整心态？",
        ],
        "volatile": [  # 上午剧烈波动
            "上午坐过山车，午休怎么平复心情？",
            "老K和苏苏，你们谁更适合做'情绪管理教练'？",
            "如果REITs像天气，今天算什么季节？",
        ],
    }
    
    async def generate_topic(self, morning_summary: Optional[str] = None) -> Dict:
        """
        生成午间话题
        morning_summary: 上午盘面简要摘要（可为空）
        """
        # 解析上午情绪
        sentiment = self._parse_morning_sentiment(morning_summary or "")
        
        # 选模板
        templates = self.TOPIC_TEMPLATES.get(sentiment, self.TOPIC_TEMPLATES["calm"])
        topic = random.choice(templates)
        
        return {
            "topic": topic,
            "sentiment": sentiment,
            "morning_summary": morning_summary,
            "generated_at": datetime.now().isoformat(),
            "mode": "lunch_whisper",
        }
    
    def _parse_morning_sentiment(self, summary: str) -> str:
        """从上午盘面摘要判断情绪"""
        s = summary.lower()
        bullish = ["涨", "红", "突破", "放量", "反弹"]
        bearish = ["跌", "绿", "破位", "缩量", "回调"]
        
        b_score = sum(1 for w in bullish if w in s)
        s_score = sum(1 for w in bearish if w in s)
        
        if b_score > s_score + 2:
            return "bullish"
        elif s_score > b_score + 2:
            return "bearish"
        elif b_score > 0 and s_score > 0:
            return "volatile"
        return "calm"


# 全局单例
_whisper: Optional[LunchWhisper] = None

def get_lunch_whisper() -> LunchWhisper:
    global _whisper
    if _whisper is None:
        _whisper = LunchWhisper()
    return _whisper
