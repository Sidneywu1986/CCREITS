"""
TDD: 数据库索引优化测试
"""
import os
import sys

os.environ.setdefault("JWT_SECRET", "test-secret-key")
os.environ.setdefault("ADMIN_INITIAL_PASSWORD", "testadmin")
os.environ.setdefault("DEBUG", "true")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import psycopg2
from core.db import _get_pg_dsn


def get_index_names():
    conn = psycopg2.connect(_get_pg_dsn())
    cur = conn.cursor()
    cur.execute("""
        SELECT indexname FROM pg_indexes
        WHERE schemaname = 'business' AND tablename = 'announcements'
    """)
    names = {row[0] for row in cur.fetchall()}
    conn.close()
    return names


class TestAnnouncementIndexes:
    """测试公告表索引优化"""

    def test_index_on_publish_date(self):
        assert 'idx_announcements_date' in get_index_names()

    def test_index_on_fund_code(self):
        assert 'idx_announcements_fund' in get_index_names()

    def test_index_on_category(self):
        assert 'idx_announcements_category' in get_index_names()

    def test_index_on_exchange(self):
        assert 'idx_announcements_exchange' in get_index_names()

    def test_index_on_title_trgm(self):
        assert 'idx_announcements_title_trgm' in get_index_names()

    def test_index_on_fund_date_composite(self):
        assert 'idx_announcements_fund_date' in get_index_names()

    def test_pg_trgm_extension(self):
        conn = psycopg2.connect(_get_pg_dsn())
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'")
        assert cur.fetchone() is not None
        conn.close()
