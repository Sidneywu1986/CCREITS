#!/usr/bin/env python3
"""
公告调度器 — 自动同步所有REIT公告到数据库
"""
import os
import sys
import asyncio
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawlers.cninfo_db_sync import sync_all_reits

logger = logging.getLogger(__name__)


class AnnouncementScheduler:
    """公告同步调度器"""

    def __init__(self, max_count: int = 30):
        self.max_count = max_count
        self.cron_hours = [6, 10, 14, 18, 22]

    async def crawl(self):
        """执行公告同步"""
        logger.info("[AnnouncementScheduler] Starting crawl...")
        stats = sync_all_reits(max_count=self.max_count)
        logger.info(
            f"[AnnouncementScheduler] Done: success={stats['success']}/{stats['total']}, "
            f"inserted={stats['total_inserted']}, skipped={stats['total_skipped']}"
        )
        return stats

    def run_sync(self):
        """同步入口（供外部调用）"""
        return asyncio.run(self.crawl())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="公告同步调度器")
    parser.add_argument("--max-count", type=int, default=30, help="每只REIT最大同步条数")
    args = parser.parse_args()

    scheduler = AnnouncementScheduler(max_count=args.max_count)
    scheduler.run_sync()
