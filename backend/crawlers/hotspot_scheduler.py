"""
Social hotspot crawler scheduler (30 min interval)
"""
import logging
from typing import List, Dict
import httpx
from backend.crawlers.base_scheduler import BaseScheduler
from backend.ai_db.models import SocialHotspot

logger = logging.getLogger(__name__)


class HotspotScheduler(BaseScheduler):
    """Crawler for social hotspot data (Weibo, Eastmoney, etc.)"""

    def __init__(self):
        super().__init__(name="hotspot_spider", max_retries=3, alert_threshold=5)
        self.interval_minutes = 30

    async def crawl(self):
        """Crawl Weibo hot search, Eastmoney guba, Tonghuashun, Xueqiu"""
        all_items = []

        # Weibo hot search
        weibo_items = await self._crawl_weibo()
        all_items.extend(weibo_items)

        # Save all items
        await self._save_hotspots(all_items)

    async def _crawl_weibo(self) -> List[Dict]:
        """Crawl Weibo hot search"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://weibo.com/ajax/side/hotSearch",
                    timeout=10
                )
                data = response.json()
                items = []
                for item in data.get("data", {}).get("realtime", [])[:20]:
                    items.append({
                        "source": "weibo",
                        "title": item.get("word", ""),
                        "url": f"https://s.weibo.com/weibo?q={item.get('word', '')}",
                        "publish_time": None,
                        "content": item.get("raw_hot", ""),
                        "author": None,
                    })
                return items
        except Exception as e:
            logger.warning(f"Weibo crawl failed: {e}")
            return []

    async def _save_hotspots(self, items: List[Dict]):
        """Save hotspot items to database"""
        for item in items:
            existing = await SocialHotspot.filter(
                source=item["source"],
                title=item["title"]
            ).first()
            if not existing:
                await SocialHotspot.create(
                    source=item["source"],
                    title=item["title"],
                    content=item.get("content"),
                    url=item.get("url"),
                    author=item.get("author"),
                    publish_time=item.get("publish_time"),
                    entity_tags="[]"
                )


# Main entry
if __name__ == "__main__":
    import asyncio
    import time

    scheduler = HotspotScheduler()
    while True:
        asyncio.run(scheduler.run())
        time.sleep(scheduler.interval_minutes * 60)
