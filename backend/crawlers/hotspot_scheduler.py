"""
Social hotspot crawler scheduler (30 min interval)
Using Playwright to bypass anti-bot measures
"""
import logging
import random
import asyncio
from typing import List, Dict
from crawlers.base_scheduler import BaseScheduler
from ai_db.models import SocialHotspot

logger = logging.getLogger(__name__)


class HotspotScheduler(BaseScheduler):
    """Crawler for social hotspot data using Playwright"""

    def __init__(self):
        super().__init__(name="hotspot_spider", max_retries=3, alert_threshold=5)
        self.interval_minutes = 30

    async def crawl(self):
        """Crawl hotspots from multiple sources"""
        # Ensure database is initialized
        from tortoise import Tortoise
        if not Tortoise.is_inited():
            await Tortoise.init(
                db_url='postgres://postgres:postgres@localhost:5432/ai_db',
                modules={'ai_db': ['backend.ai_db.models']}
            )

        all_items = []

        # Source 1: Weibo hot search (via Playwright)
        weibo_items = await self._crawl_weibo()
        all_items.extend(weibo_items)

        # Wait between sources to avoid overloading
        await asyncio.sleep(random.uniform(2, 5))

        # Source 2: Baidu hot search (via Playwright)
        baidu_items = await self._crawl_baidu()
        all_items.extend(baidu_items)

        # Deduplicate by title
        seen = set()
        unique_items = []
        for item in all_items:
            if item["title"] not in seen:
                seen.add(item["title"])
                unique_items.append(item)

        # Save all items
        if unique_items:
            await self._save_hotspots(unique_items)
            logger.info(f"Saved {len(unique_items)} hotspots")
        else:
            logger.warning("No hotspots found from any source")

    async def _crawl_weibo(self) -> List[Dict]:
        """Crawl Weibo hot search using Playwright"""
        try:
            from playwright.async_api import async_playwright

            items = []
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                )
                page = await context.new_page()

                # Block images and media to speed up
                await page.route("**/*.{png,jpg,jpeg,gif,svg,mp4,webm}", lambda route: route.abort())

                logger.info("Fetching Weibo hot search...")
                await page.goto("https://s.weibo.com/top/summary?cate=realtimehot", timeout=30000)
                await page.wait_for_load_state("networkidle", timeout=30000)

                # Wait for hot search table
                await page.wait_for_selector("#pl_top_realtimehot tbody tr", timeout=15000)

                # Extract data
                rows = await page.query_selector_all("#pl_top_realtimehot tbody tr")
                for row in rows[:20]:
                    try:
                        rank_el = await row.query_selector("td.ranktop")
                        title_el = await row.query_selector("td.td-02 a")
                        heat_el = await row.query_selector("td.td-02 span")

                        rank = await rank_el.inner_text() if rank_el else ""
                        title = await title_el.inner_text() if title_el else ""
                        heat = await heat_el.inner_text() if heat_el else ""

                        if title:
                            items.append({
                                "source": "weibo",
                                "title": title.strip(),
                                "url": f"https://s.weibo.com/weibo?q={title.strip()}",
                                "content": heat.strip(),
                                "author": None,
                                "publish_time": None,
                            })
                    except Exception as e:
                        logger.debug(f"Weibo row parse error: {e}")
                        continue

                await browser.close()

            logger.info(f"Weibo: fetched {len(items)} items")
            return items

        except Exception as e:
            logger.warning(f"Weibo crawl failed: {e}")
            return []

    async def _crawl_baidu(self) -> List[Dict]:
        """Crawl Baidu hot search using Playwright"""
        try:
            from playwright.async_api import async_playwright

            items = []
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                )
                page = await context.new_page()

                await page.route("**/*.{png,jpg,jpeg,gif,svg,mp4,webm}", lambda route: route.abort())

                logger.info("Fetching Baidu hot search...")
                await page.goto("https://top.baidu.com/board?tab=realtime", timeout=30000)
                await page.wait_for_load_state("networkidle", timeout=30000)

                # Wait for content
                await page.wait_for_selector(".category-wrap_iQLoo", timeout=15000)

                cards = await page.query_selector_all(".category-wrap_iQLoo")
                for card in cards[:20]:
                    try:
                        title_el = await card.query_selector(".c-single-text-ellipsis")
                        heat_el = await card.query_selector(".hot-index_1Bl1a")

                        title = await title_el.inner_text() if title_el else ""
                        heat = await heat_el.inner_text() if heat_el else ""

                        if title:
                            items.append({
                                "source": "baidu",
                                "title": title.strip(),
                                "url": f"https://www.baidu.com/s?wd={title.strip()}",
                                "content": heat.strip(),
                                "author": None,
                                "publish_time": None,
                            })
                    except Exception as e:
                        logger.debug(f"Baidu card parse error: {e}")
                        continue

                await browser.close()

            logger.info(f"Baidu: fetched {len(items)} items")
            return items

        except Exception as e:
            logger.warning(f"Baidu crawl failed: {e}")
            return []

    async def _save_hotspots(self, items: List[Dict]):
        """Save hotspot items to database"""
        saved = 0
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
                saved += 1
        logger.info(f"Saved {saved} new hotspots (skipped {len(items) - saved} duplicates)")


# Main entry
if __name__ == "__main__":
    import sys
    import time

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    scheduler = HotspotScheduler()
    while True:
        try:
            asyncio.run(scheduler.run())
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
            break
        except Exception as e:
            logger.error(f"Scheduler error: {e}")

        logger.info(f"Sleeping {scheduler.interval_minutes} minutes...")
        time.sleep(scheduler.interval_minutes * 60)
