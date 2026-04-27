"""
Tests for crawler schedulers
"""
import pytest
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.crawlers.base_scheduler import BaseScheduler


class ConcreteTestScheduler(BaseScheduler):
    """Test scheduler implementation"""
    async def crawl(self):
        pass  # No-op for testing


def test_base_scheduler_init():
    """Test BaseScheduler initialization with custom parameters"""
    scheduler = ConcreteTestScheduler(name="test_spider", max_retries=3, alert_threshold=5)
    assert scheduler.name == "test_spider"
    assert scheduler.max_retries == 3
    assert scheduler.alert_threshold == 5
    assert scheduler.consecutive_failures == 0


def test_hotspot_scheduler_defaults():
    """Test HotspotScheduler has correct default values"""
    from backend.crawlers.hotspot_scheduler import HotspotScheduler
    scheduler = HotspotScheduler()
    assert scheduler.name == "hotspot_spider"
    assert scheduler.interval_minutes == 30


def test_article_scheduler_defaults():
    """Test ArticleScheduler has correct default values"""
    from backend.crawlers.article_scheduler import ArticleScheduler
    scheduler = ArticleScheduler()
    assert scheduler.name == "article_spider"
    assert scheduler.cron_hour == 8


def test_announcement_scheduler_defaults():
    """Test AnnouncementScheduler has correct default values"""
    from backend.crawlers.announcement_scheduler import AnnouncementScheduler
    scheduler = AnnouncementScheduler()
    assert scheduler.name == "announcement_spider"
    assert scheduler.cron_hours == [6, 18]


def test_scheduler_consecutive_failures():
    """Test consecutive failures tracking"""
    scheduler = ConcreteTestScheduler(name="test", max_retries=3, alert_threshold=2)
    assert scheduler.consecutive_failures == 0
    scheduler.consecutive_failures += 1
    assert scheduler.consecutive_failures == 1
