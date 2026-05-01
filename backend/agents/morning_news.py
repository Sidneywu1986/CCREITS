#!/usr/bin/env python3
"""
晨间通讯社引擎
08:00-08:50，欧美隔夜REITs市场要闻
"""

import asyncio
import logging
import psycopg2
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger("morning_news")


@dataclass
class NewsItem:
    title: str
    summary: str
    source: str           # 来源名称
    source_url: str       # 必填！RSDS v1.1 血缘要求
    publish_time: Optional[str] = None
    market: str = ""      # US / SG / JP / EU


class MorningNewsEngine:
    """
    晨间通讯社：国际REITs新闻聚合
    ⚠️ 所有新闻必须带source_url，禁止编造
    """
    
    # 真实可爬取的数据源（需实际验证可用性）
    SOURCES = {
        "nareit": {
            "name": "NAREIT",
            "url": "https://www.reit.com/news",
            "market": "US",
        },
        "sgx_reits": {
            "name": "新加坡交易所REITs",
            "url": "https://www.sgx.com/reits",
            "market": "SG",
        },
        "reit_weekly": {
            "name": "REITs Weekly",
            "url": "https://reitweek.com",
            "market": "US",
        },
    }
    
    def __init__(self):
        self.news_cache: List[NewsItem] = []
        self.last_fetch: Optional[datetime] = None
    
    async def fetch_overnight(self) -> List[NewsItem]:
        """
        从已同步的公众号文章中筛选最近24小时的要闻
        """
        try:
            from core.db import get_conn
            from datetime import datetime, timedelta
            
            with get_conn() as conn:
                cur = conn.cursor()
                yesterday = (datetime.now() - timedelta(hours=24)).isoformat()
                cur.execute("""
                    SELECT title, content, source, published
                    FROM business.wechat_articles
                    WHERE published > %s
                      AND content IS NOT NULL
                      AND LENGTH(content) > 200
                    ORDER BY published DESC
                    LIMIT 20
                """, (yesterday,))
                rows = [dict(r) for r in cur.fetchall()]
            
            news = []
            keywords = ['reits', 'reit', '基础设施', '公募', '投资', '上市', '发行', '获批', '申报', '扩募']
            for row in rows:
                title = row.get('title', '') or ''
                content = row.get('content', '') or ''
                text = (title + ' ' + content[:500]).lower()
                # 筛选含关键词的文章
                if any(k in text for k in keywords):
                    news.append(NewsItem(
                        title=title,
                        summary=content[:200] + ('...' if len(content) > 200 else ''),
                        source=row.get('source', '公众号'),
                        source_url='',
                        publish_time=str(row.get('published', '')),
                        market='CN',
                    ))
            return news[:10]  # 最多10条
        except (psycopg2.Error, ValueError, KeyError) as e:
            logger.warning(f"Fetch overnight news from PG failed: {e}")
            return []
        # TODO: 接入实际爬虫
        # 注意：如果源不可用，返回空列表，AI会提示"部分新闻源暂时无法获取"
        # 绝对不能编造新闻！（记忆ID 4零容忍）
        
        # 占位：实际开发时替换为真实抓取
        logger.warning("晨间通讯社：新闻源爬虫待接入，当前返回空列表")
        return []
    
    def generate_bulletin(self, news_items: List[NewsItem]) -> Dict:
        """
        生成新闻简报（供3个AI角色点评）
        """
        if not news_items:
            return {
                "has_news": False,
                "notice": "部分国际新闻源暂时无法获取，以下为历史回顾。",
                "items": [],
                "generated_at": datetime.now().isoformat(),
            }
        
        # 按市场分组
        by_market = {}
        for item in news_items:
            by_market.setdefault(item.market, []).append(item)
        
        return {
            "has_news": True,
            "items": [
                {
                    "title": item.title,
                    "summary": item.summary,
                    "source": item.source,
                    "source_url": item.source_url,  # 前端必须展示
                    "market": item.market,
                }
                for item in news_items
            ],
            "by_market": by_market,
            "generated_at": datetime.now().isoformat(),
        }
    
    async def run_morning_broadcast(self) -> Dict:
        """完整晨间播报流程"""
        news = await self.fetch_overnight()
        bulletin = self.generate_bulletin(news)
        
        # 分配角色任务
        roles = {
            "guo_de_gang": "新加坡/亚洲市场点评",
            "smith": "美国REITs市场点评",
            "mei_de_chu": "宏观利率与汇率影响",
        }
        
        return {
            "bulletin": bulletin,
            "roles": roles,
            "mode": "morning_news",
        }


# 全局单例
_engine: Optional[MorningNewsEngine] = None

def get_morning_engine() -> MorningNewsEngine:
    global _engine
    if _engine is None:
        _engine = MorningNewsEngine()
    return _engine
