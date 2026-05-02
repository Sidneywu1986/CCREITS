"""
TDD: 508XXX SSE增量同步测试
"""
import os
import sys
import importlib.util

os.environ.setdefault("JWT_SECRET", "test-secret-key")
os.environ.setdefault("ADMIN_INITIAL_PASSWORD", "testadmin")
os.environ.setdefault("DEBUG", "true")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'crawlers'))

import pytest
from datetime import datetime, timedelta


def _load_cninfo_db_sync():
    """绕过 crawlers/__init__.py 直接加载 cninfo_db_sync 模块"""
    path = os.path.join(BASE_DIR, 'crawlers', 'cninfo_db_sync.py')
    spec = importlib.util.spec_from_file_location("cninfo_db_sync", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cninfo_db_sync"] = mod
    spec.loader.exec_module(mod)
    return mod


class TestSSEIncrementalSync:
    """测试508XXX SSE增量同步"""

    def test_get_sse_announcements_supports_date_range(self):
        """get_sse_announcements 应支持 start_date/end_date 参数"""
        from cninfo_crawler import CNInfoCrawler
        crawler = CNInfoCrawler()

        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

        result = crawler.get_sse_announcements(
            '508000', start_date=start_date, end_date=end_date, page_size=100
        )
        assert isinstance(result, list)
        # 增量结果应少于全量
        full_result = crawler.get_sse_announcements(
            '508000', start_date='2021-01-01', end_date=end_date, page_size=100
        )
        assert len(result) <= len(full_result)

    def test_get_sse_announcements_date_filter_actually_works(self):
        """日期参数应真正过滤结果，不能返回范围外的公告"""
        from cninfo_crawler import CNInfoCrawler
        crawler = CNInfoCrawler()

        # 取一个非常窄的日期范围
        start_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')

        result = crawler.get_sse_announcements(
            '508000', start_date=start_date, end_date=end_date, page_size=100
        )

        for ann in result:
            ann_date = ann.get('time', '')
            if ann_date:
                # SSE API 返回的日期格式可能是 YYYY-MM-DD 或其他格式
                assert ann_date >= start_date, f"公告日期 {ann_date} 早于开始日期 {start_date}"
                assert ann_date <= end_date, f"公告日期 {ann_date} 晚于结束日期 {end_date}"

    def test_sync_single_fund_supports_incremental(self):
        """sync_single_fund 应支持增量同步模式"""
        mod = _load_cninfo_db_sync()
        sync_single_fund = mod.sync_single_fund

        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

        # 增量同步应只获取最近7天的公告
        result = sync_single_fund('508000', start_date=start_date, end_date=end_date)
        assert result['success'] is True
        # 增量结果应明显少于全量（508000全量约178条）
        assert result['total_found'] < 50

    def test_sync_single_fund_full_sync_still_works(self):
        """sync_single_fund 全量同步模式仍然正常工作"""
        mod = _load_cninfo_db_sync()
        sync_single_fund = mod.sync_single_fund

        # 用数据量较小的508029做全量测试，避免超时
        result = sync_single_fund('508029', start_date='2021-01-01')
        assert result['success'] is True
        assert result['total_found'] > 10  # 508029历史公告应该有一些

    def test_incremental_does_not_duplicate(self):
        """增量同步不应重复插入已有数据"""
        import psycopg2
        from core.db import _get_pg_dsn
        mod = _load_cninfo_db_sync()
        sync_single_fund = mod.sync_single_fund

        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

        # 第一次增量同步
        result1 = sync_single_fund('508000', start_date=start_date, end_date=end_date)
        inserted1 = result1['inserted']

        # 第二次同样的增量同步
        result2 = sync_single_fund('508000', start_date=start_date, end_date=end_date)
        inserted2 = result2['inserted']

        # 第二次应该没有新插入（因为已经存在）
        assert inserted2 == 0, f"重复同步不应插入新数据，但插入了 {inserted2} 条"
