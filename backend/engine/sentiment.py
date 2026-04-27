#!/usr/bin/env python3
"""
情感计算引擎 —— 纯本地，零外部API
V2: 扩展词典（资产类别×事件类型×程度副词×否定处理）
输出：sentiment_score(-1~1) / emotion_tag / intensity / keywords / summary
"""

import os
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from core.db import get_conn


# ==================== 核心情感词典 ====================

BULLISH_CORE = {
    "大涨", "涨停", "飙升", "突破", "利好", "超预期", "放量", "资金流入",
    "分红", "高股息", "稳定", "护城河", "稀缺", "抢筹", "底部", "反弹",
    "政策红利", "扩募", "并购", "资产注入", "租金上涨", "满租", "供不应求",
    "增持", "回购", "估值修复", "业绩兑现", "现金流", "确定性", "龙头",
    "逆势上涨", "领跑", "创新高", "收复失地", "企稳回升", "困境反转",
    "价值洼地", "安全边际", "抗周期", "穿越牛熊", "长期配置",
}

BEARISH_CORE = {
    "大跌", "跌停", "暴跌", "跳水", "破位", "利空", "不及预期", "缩量",
    "资金流出", "砍仓", "套牢", "崩盘", "违约", "空置率", "退租", "降租",
    "政策收紧", "减持", "赎回", "折价", "破发", "亏损", "风险暴露",
    "暴雷", "黑天鹅", "流动性危机", "评级下调", "收益率下降",
    "踩踏", "多杀多", "割肉", "阴跌", "破位下行", "趋势走坏",
    "基本面恶化", "现金流断裂", "资不抵债", "技术性违约",
}

PANIC_WORDS = {
    "恐慌", "逃命", "清仓", "爆雷", "危机", "崩盘", "闪崩",
    "断崖", "血洗", "崩盘式", "系统性风险", "连锁反应", "踩踏式",
}

GREED_WORDS = {
    "梭哈", "满仓", "加杠杆", "翻倍", "暴富", "ALL IN", "踏空",
    "错过", "追", "追高", "FOMO", "一夜暴富", "财富自由", "闭眼买",
}

# ==================== 中性稀释词（降低行政公告/ routine 的极端分数）====================

NEUTRAL_DILUTION = {
    "公告", "通知", "提示", "披露", "发布", "关于", "周报", "日报", "复盘",
    "回顾", "简报", "快讯", "资讯", "动态", "更新", "解读", "分析",
    "行情", "走势", "收盘", "开盘", "成交额", "成交量", "涨跌",
    "获准", "准予", "批复", "注册生效", "过会", "受理",
}

ROUTINE_TITLE_PATTERNS = [
    r"每日.*复盘", r"市场.*回顾", r".*日报", r".*周报", r".*简报",
    r"公募REITs.*每日", r"每日公募REITs", r".*行情.*回顾", r".*每日.*行情",
]

# ==================== 资产类别专属词典 ====================

ASSET_BULLISH = {
    # 仓储物流
    "仓储物流": {"高标仓", "智能仓", "冷链", "电商物流", "快递", "供应链", "物流园", "吞吐", "周转", "吞吐量增长"},
    # 高速公路
    "高速公路": {"车流量", "通行费", "路网", "里程", "贯通", "互联互通", "车流恢复", "货车增长", "跨省", "ETC", "路网效应"},
    # 产业园
    "产业园": {"入驻率", "产业集群", "科技企业", "独角兽", "专精特新", "孵化器", "加速器", "亩均税收", "产值", "招商引资"},
    # 保障房
    "保障房": {"保租房", "人才公寓", "公租房", "租赁需求", "刚需", "供不应求", "轮候", "满租", "租金稳定", "政策支持"},
    # 能源环保
    "能源环保": {"绿电", "光伏", "风电", "储能", "碳中和", "ESG", "可再生能源", "并网", "电价上涨", "补贴到位"},
    # 数据中心
    "数据中心": {"算力", "AI", "大模型", "GPU", "上架率", "PUE", "东数西算", "云服务", "互联网企业", "液冷", "高功率"},
}

ASSET_BEARISH = {
    "仓储物流": {"空置", "退仓", "物流萎缩", "电商退潮", "过剩", "同质化", "价格战", "周转慢"},
    "高速公路": {"车流下降", "免费通行", "分流", "替代路线", "高铁冲击", "货车减少", "修路封道"},
    "产业园": {"空置", "退租", "企业迁出", "产值下滑", "招商难", "同质化", "配套差", "僵尸企业"},
    "保障房": {"配租率低", "位置偏", "配套差", "租金倒挂", "退租潮", "需求饱和", "政策退出"},
    "能源环保": {"补贴退坡", "弃风弃光", "电价下调", "产能过剩", "技术路线失败", "环保处罚"},
    "数据中心": {"上架率低", "客户流失", "PUE超标", "电力不足", "算力过剩", "价格战", "液冷故障"},
}

# ==================== 事件类型词典 ====================

EVENT_BULLISH = {
    "分红": {"高分红", "分红稳定", "分红率", "股息率", "派息", "除权", "填权", "连续分红", "提升分红"},
    "扩募": {"扩募成功", "新资产", "资产注入", "规模扩张", "份额增加", "稀释有限", "优质资产"},
    "并购": {"并购", "收购", "整合", "协同效应", "溢价收购", "战略投资", "产业链整合"},
    "政策": {"政策支持", "监管放松", "税收优惠", "绿色通道", "试点扩容", "纳入指数", "外资开放"},
    "租金": {"租金上涨", "提价", "满租", "续租率高", "租金弹性", "议价能力", "租金回收期"},
    "客流": {"客流恢复", "客流增长", "节假日高峰", "商圈人气", "出租率", "翻台率", "入住率"},
}

EVENT_BEARISH = {
    "分红": {"分红下降", "不分红", "推迟分红", "股息率下降", "现金流紧张", "挪用资金"},
    "扩募": {"扩募失败", "资产质量差", "稀释严重", "破发", "认购不足", "定价过高"},
    "并购": {"并购失败", "商誉减值", "整合困难", "文化冲突", "标的暴雷", "对赌失败"},
    "政策": {"政策收紧", "监管趋严", "加税", "限制外资", "退出试点", "退市风险"},
    "租金": {"租金下降", "免租期", "降租谈判", "空置", "退租", "租金倒挂", "租约到期"},
    "客流": {"客流下滑", "淡季", "关店潮", "商圈衰落", "出租率下降", "空置期"},
}

# ==================== 程度副词（加权） ====================

INTENSITY_MODIFIERS = {
    # 极度强化 (+1.5x)
    "大幅": 1.5, "巨幅": 1.5, "剧烈": 1.5, "急剧": 1.5, "疯狂": 1.5,
    "断崖式": 1.5, "雪崩": 1.5, "暴跌": 1.5, "暴涨": 1.5,
    # 强化 (+1.2x)
    "明显": 1.2, "显著": 1.2, "持续": 1.2, "加速": 1.2, "超预期": 1.2,
    "强劲": 1.2, "稳健": 1.2, "扎实": 1.2, "实质性": 1.2,
    # 弱化 (+0.6x)
    "小幅": 0.6, "略微": 0.6, "温和": 0.6, "有限": 0.6, "短期": 0.6,
    "暂时": 0.6, "局部": 0.6, "个别": 0.6, "结构性": 0.6,
    # 负面修饰（反转方向）
    "不及": -0.5, "低于": -0.5, "弱于": -0.5, "差于": -0.5,
}

# ==================== 否定词处理 ====================

NEGATION_WORDS = {"不", "没", "未", "无", "别", "勿", "否", "非", "未曾", "尚未"}

# 否定 + 情感词的反转规则
NEGATION_DISTANCE = 3  # 否定词与情感词的最大距离（字）


@dataclass
class SentimentResult:
    score: float          # -1.0 ~ 1.0
    emotion: str          # panic/fear/neutral/hope/greed
    intensity: float      # 0.0 ~ 1.0
    keywords: List[str]   # 命中的关键词
    summary: str          # 一句话总结
    asset_tags: List[str] # 识别到的资产类别
    event_tags: List[str] # 识别到的事件类型


class SentimentEngine:
    def __init__(self, db_path: Optional[str] = None):
        # db_path 参数保留兼容，不再使用
        self.db_path = None

    def analyze(self, text: str) -> SentimentResult:
        """单条文本情感分析（V2 增强版）"""
        text_lower = text.lower()

        # 1. 收集所有命中的词及其位置（用于否定检测）
        hits: List[Tuple[str, float, int]] = []  # (word, weight, pos)
        asset_tags: List[str] = []
        event_tags: List[str] = []

        # 核心情感词
        for w in BULLISH_CORE:
            pos = text_lower.find(w)
            if pos >= 0:
                hits.append((w, 1.0, pos))
        for w in BEARISH_CORE:
            pos = text_lower.find(w)
            if pos >= 0:
                hits.append((w, -1.0, pos))

        # 资产类别词
        for asset, words in ASSET_BULLISH.items():
            for w in words:
                pos = text_lower.find(w)
                if pos >= 0:
                    hits.append((w, 0.8, pos))
                    if asset not in asset_tags:
                        asset_tags.append(asset)
        for asset, words in ASSET_BEARISH.items():
            for w in words:
                pos = text_lower.find(w)
                if pos >= 0:
                    hits.append((w, -0.8, pos))
                    if asset not in asset_tags:
                        asset_tags.append(asset)

        # 事件类型词
        for evt, words in EVENT_BULLISH.items():
            for w in words:
                pos = text_lower.find(w)
                if pos >= 0:
                    hits.append((w, 0.9, pos))
                    if evt not in event_tags:
                        event_tags.append(evt)
        for evt, words in EVENT_BEARISH.items():
            for w in words:
                pos = text_lower.find(w)
                if pos >= 0:
                    hits.append((w, -0.9, pos))
                    if evt not in event_tags:
                        event_tags.append(evt)

        # 恐慌/贪婪词（权重更高）
        for w in PANIC_WORDS:
            pos = text_lower.find(w)
            if pos >= 0:
                hits.append((w, -2.0, pos))
        for w in GREED_WORDS:
            pos = text_lower.find(w)
            if pos >= 0:
                hits.append((w, 2.0, pos))

        # 2. 程度副词加权 + 否定检测
        total_score = 0.0
        bull_count = bear_count = 0
        panic_count = greed_count = 0
        hit_keywords = []

        for word, weight, pos in hits:
            # 检查前方是否有否定词
            prefix = text_lower[max(0, pos - 10):pos]
            negated = any(n in prefix for n in NEGATION_WORDS)
            if negated:
                weight *= -0.8  # 反转但保留80%强度（"不是底部"→偏空但不完全）

            # 检查前方是否有程度副词
            prefix2 = text_lower[max(0, pos - 8):pos]
            modifier = 1.0
            for mod, mod_weight in INTENSITY_MODIFIERS.items():
                if mod in prefix2:
                    if mod_weight < 0:
                        # 负面修饰（如"不及预期"）
                        weight *= abs(mod_weight)
                        if weight > 0:
                            weight = -weight
                    else:
                        modifier = mod_weight
                    break

            final_weight = weight * modifier
            total_score += final_weight
            hit_keywords.append(word)

            if weight > 0:
                bull_count += 1
            else:
                bear_count += 1
            if word in PANIC_WORDS:
                panic_count += 1
            if word in GREED_WORDS:
                greed_count += 1

        # 3. 中性稀释 + 归一化
        neutral_count = sum(1 for w in NEUTRAL_DILUTION if w in text_lower)
        dilution = 1.0 + neutral_count * 0.12

        # 标题为 routine 复盘/日报类，进一步稀释
        if any(re.search(p, text_lower) for p in ROUTINE_TITLE_PATTERNS):
            dilution += 0.4

        total = bull_count + bear_count + 1e-6
        base_score = total_score / (total * dilution) if total > 0 else 0.0
        base_score = max(-1.0, min(1.0, base_score))

        # 4. 情绪判定
        if panic_count > 0 and base_score < -0.3:
            emotion = "panic"
        elif greed_count > 0 and base_score > 0.3:
            emotion = "greed"
        elif base_score > 0.3:
            emotion = "hope"
        elif base_score < -0.3:
            emotion = "fear"
        else:
            emotion = "neutral"

        # 5. 强度计算
        intensity = min((bull_count + bear_count + panic_count + greed_count) / 6, 1.0)

        # 6. 总结生成
        summary = self._generate_summary(emotion, hit_keywords[:5], asset_tags, event_tags)

        return SentimentResult(
            score=round(base_score, 2),
            emotion=emotion,
            intensity=round(intensity, 2),
            keywords=list(set(hit_keywords)),
            summary=summary,
            asset_tags=asset_tags,
            event_tags=event_tags,
        )

    def _generate_summary(self, emotion: str, keywords: List[str], assets: List[str], events: List[str]) -> str:
        asset_str = f"涉及{ '/'.join(assets[:2]) }" if assets else ""
        event_str = f"{ '/'.join(events[:2]) }事件" if events else ""
        kw_str = "/".join(keywords[:3]) if keywords else "无明显关键词"

        templates = {
            "panic": f"{'【' + asset_str + '】' if asset_str else ''}市场恐慌情绪蔓延，{event_str}触发，关键词：{kw_str}",
            "fear": f"{'【' + asset_str + '】' if asset_str else ''}市场偏谨慎，关注{event_str}风险，关键词：{kw_str}",
            "neutral": f"{'【' + asset_str + '】' if asset_str else ''}情绪平稳，{event_str}观察中，提及：{kw_str}",
            "hope": f"{'【' + asset_str + '】' if asset_str else ''}市场情绪回暖，{event_str}有亮点，关键词：{kw_str}",
            "greed": f"{'【' + asset_str + '】' if asset_str else ''}市场过热，{event_str}需警惕，关键词：{kw_str}",
        }
        return templates.get(emotion, "情绪待观察")

    def analyze_hotspot(self, title: str, content: str = "") -> SentimentResult:
        """分析热点话题情感"""
        return self.analyze(title + " " + content)

    def _ensure_columns(self, conn):
        """确保 wechat_articles 表有情感字段"""
        cur = conn.cursor()
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'business' AND table_name = 'wechat_articles'
        """)
        cols = [row[0] for row in cur.fetchall()]
        if "sentiment_score" not in cols:
            cur.execute("ALTER TABLE business.wechat_articles ADD COLUMN sentiment_score NUMERIC(8,4) DEFAULT 0")
        if "emotion_tag" not in cols:
            cur.execute("ALTER TABLE business.wechat_articles ADD COLUMN emotion_tag VARCHAR(20) DEFAULT 'neutral'")
        if "asset_tags" not in cols:
            cur.execute("ALTER TABLE business.wechat_articles ADD COLUMN asset_tags TEXT DEFAULT ''")
        if "event_tags" not in cols:
            cur.execute("ALTER TABLE business.wechat_articles ADD COLUMN event_tags TEXT DEFAULT ''")
        conn.commit()

    def batch_tag_articles(self, retag_extremes: bool = False) -> int:
        """离线脚本：给 wechat_articles 表所有文章打情感标签
        
        Args:
            retag_extremes: 为 True 时，同时重打 sentiment_score 为 0 或 ±1.0 的极端值文章
        """
        with get_conn() as conn:
            self._ensure_columns(conn)
            cur = conn.cursor()

            if retag_extremes:
                cur.execute("""
                    SELECT id, title, content FROM business.wechat_articles
                    WHERE content IS NOT NULL AND length(trim(content)) > 10
                      AND (sentiment_score = 0 OR sentiment_score = 1.0 OR sentiment_score = -1.0)
                """)
            else:
                cur.execute("""
                    SELECT id, title, content FROM business.wechat_articles
                    WHERE sentiment_score = 0 AND content IS NOT NULL AND length(trim(content)) > 10
                """)
            rows = cur.fetchall()
            count = 0
            for row in rows:
                art_id, title, content = row
                res = self.analyze(title + " " + (content or "")[:500])
                cur.execute("""
                    UPDATE business.wechat_articles
                    SET sentiment_score = %s, emotion_tag = %s, asset_tags = %s, event_tags = %s
                    WHERE id = %s
                """, (res.score, res.emotion, ",".join(res.asset_tags), ",".join(res.event_tags), art_id))
                count += 1

            conn.commit()
        return count

    def get_market_emotion(self, date: Optional[str] = None) -> Dict:
        """获取当日市场整体情绪"""
        date = date or datetime.now().strftime("%Y-%m-%d")
        with get_conn() as conn:
            self._ensure_columns(conn)
            cur = conn.cursor()

            cur.execute("""
                SELECT emotion_tag, COUNT(*), AVG(sentiment_score)
                FROM business.wechat_articles
                WHERE date(published) = %s AND sentiment_score != 0
                GROUP BY emotion_tag
            """, (date,))
            rows = cur.fetchall()

            # 资产分布
            cur.execute("""
                SELECT asset_tags, COUNT(*) FROM business.wechat_articles
                WHERE date(published) = %s AND asset_tags != ''
                GROUP BY asset_tags
            """, (date,))
            asset_rows = cur.fetchall()

        if not rows:
            return {"overall": "neutral", "score": 0.0, "dominant": "暂无数据", "distribution": {}, "asset_breakdown": {}}

        dominant = max(rows, key=lambda x: x[1])
        total_count = sum(r[1] for r in rows)
        avg_score = sum(r[2] * r[1] for r in rows) / total_count if total_count else 0

        return {
            "overall": dominant[0],
            "score": round(avg_score, 2),
            "dominant": dominant[0],
            "distribution": {r[0]: r[1] for r in rows},
            "total_articles": total_count,
            "asset_breakdown": {r[0]: r[1] for r in asset_rows},
        }

    def get_emotion_trend(self, days: int = 7) -> List[Dict]:
        """获取近N天情绪趋势"""
        with get_conn() as conn:
            cur = conn.cursor()
            self._ensure_columns(conn)

            cur.execute("""
                SELECT date(published) as dt, AVG(sentiment_score) as avg_score,
                       MODE() WITHIN GROUP (ORDER BY emotion_tag) as emotion_tag
                FROM business.wechat_articles
                WHERE published IS NOT NULL AND sentiment_score != 0
                GROUP BY date(published)
                ORDER BY dt DESC
                LIMIT %s
            """, (days,))

            results = []
            for row in cur.fetchall():
                results.append({
                    "date": str(row[0]) if row[0] else None,
                    "avg_score": round(row[1], 3) if row[1] else 0,
                    "dominant_emotion": row[2],
                })
        return results


# 全局单例
_engine: Optional[SentimentEngine] = None


def get_sentiment_engine() -> SentimentEngine:
    global _engine
    if _engine is None:
        _engine = SentimentEngine()
    return _engine
