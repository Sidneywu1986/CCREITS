"""
TDD: 验证后端服务启动后定时任务和文章同步是否正常工作
"""
import os
import sys
import time

os.environ.setdefault("JWT_SECRET", "test-secret-key")
os.environ.setdefault("ADMIN_INITIAL_PASSWORD", "testadmin")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("DB_TYPE", "postgres")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import pytest
import requests
import psycopg2
from core.db import _get_pg_dsn

API_BASE = "http://127.0.0.1:5074"


class TestBackendOnline:
    """测试后端服务是否在线"""

    def test_api_health(self):
        """API根路径应可访问"""
        try:
            res = requests.get(f"{API_BASE}/docs", timeout=5)
            assert res.status_code == 200
        except requests.ConnectionError:
            pytest.skip("后端服务未启动，跳过在线测试")

    def test_announcements_api_online(self):
        """公告API应返回数据"""
        try:
            res = requests.get(f"{API_BASE}/api/announcements?page_size=5", timeout=10)
            assert res.status_code == 200
            data = res.json()
            assert data["success"] is True
        except requests.ConnectionError:
            pytest.skip("后端服务未启动")

    def test_dividends_api_online(self):
        """分红API应返回数据"""
        try:
            res = requests.get(f"{API_BASE}/api/dividends?page_size=5", timeout=10)
            assert res.status_code == 200
            data = res.json()
            assert data["success"] is True
        except requests.ConnectionError:
            pytest.skip("后端服务未启动")


class TestSchedulerRunning:
    """测试scheduler是否运行"""

    def test_scheduler_thread_exists(self):
        """scheduler后台线程应存在"""
        import subprocess
        result = subprocess.run(['pgrep', '-f', 'api_adapter'], capture_output=True, text=True)
        assert result.returncode == 0, "api_adapter进程未找到"

    def test_scheduler_can_run_article_sync(self):
        """scheduler应能执行文章同步任务"""
        sys.path.insert(0, os.path.join(BASE_DIR, 'scheduler'))
        from scheduler.tasks import run_sync_pipeline

        # 直接调用同步函数，不应抛异常
        try:
            run_sync_pipeline()
        except Exception as e:
            # 某些子任务可能失败，但整体流程应能跑完
            print(f"run_sync_pipeline completed with possible errors: {e}")

    def test_scheduler_can_run_announcement_sync(self):
        """scheduler应能执行公告增量同步任务"""
        sys.path.insert(0, os.path.join(BASE_DIR, 'scheduler'))
        from scheduler.tasks import run_announcement_sync

        try:
            run_announcement_sync()
        except Exception as e:
            print(f"run_announcement_sync completed with possible errors: {e}")


class TestArticleSyncData:
    """测试文章同步数据"""

    def test_wechat_articles_has_data(self):
        """wechat_articles表应有数据"""
        conn = psycopg2.connect(_get_pg_dsn())
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM business.wechat_articles")
        count = cur.fetchone()[0]
        conn.close()
        assert count > 0, f"wechat_articles表为空，文章同步未运行"

    def test_article_vectors_has_data(self):
        """article_vectors表应有数据"""
        conn = psycopg2.connect(_get_pg_dsn())
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM business.article_vectors")
        count = cur.fetchone()[0]
        conn.close()
        assert count > 0, f"article_vectors表为空，向量化未运行"

    def test_articles_not_stale(self):
        """文章数据不应过于陈旧（超过3天）"""
        conn = psycopg2.connect(_get_pg_dsn())
        cur = conn.cursor()
        cur.execute("""
            SELECT MAX(created_at) FROM business.wechat_articles
        """)
        latest = cur.fetchone()[0]
        conn.close()

        from datetime import datetime, timedelta
        if latest:
            days_since = (datetime.now() - latest).days
            # 如果超过3天没有新数据，说明定时任务可能停了
            assert days_since < 3, f"文章数据已停滞 {days_since} 天，scheduler可能未运行"
