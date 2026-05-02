"""
TDD: 公告查询API测试
Run: JWT_SECRET=test pytest tests/test_announcements_api.py -v
"""
import os
import sys

os.environ.setdefault("JWT_SECRET", "test-secret-key")
os.environ.setdefault("ADMIN_INITIAL_PASSWORD", "testadmin")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("DB_TYPE", "postgres")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from api_adapter import adapter_app


@pytest.fixture
def client():
    return TestClient(adapter_app)


class TestAnnouncementsList:
    """测试公告列表查询API"""

    def test_list_announcements_basic(self, client):
        """基础列表查询应返回成功"""
        res = client.get("/api/announcements")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "data" in data
        assert isinstance(data["data"], list)
        assert "total" in data

    def test_list_announcements_pagination(self, client):
        """分页参数应生效"""
        res = client.get("/api/announcements?page=1&page_size=5")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert len(data["data"]) <= 5

    def test_list_announcements_by_fund_code(self, client):
        """按基金代码筛选应生效"""
        res = client.get("/api/announcements?fund_code=508000")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        items = data["data"]
        for item in items:
            assert item["fund_code"] == "508000"

    def test_list_announcements_by_category(self, client):
        """按分类筛选应生效"""
        res = client.get("/api/announcements?category=financial")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        items = data["data"]
        for item in items:
            assert item["category"] == "financial"

    def test_list_announcements_by_exchange(self, client):
        """按交易所筛选应生效"""
        res = client.get("/api/announcements?exchange=SSE")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        items = data["data"]
        for item in items:
            assert item["exchange"] == "SSE"

    def test_list_announcements_search(self, client):
        """搜索标题应生效"""
        res = client.get("/api/announcements?search=招募说明书")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        items = data["data"]
        for item in items:
            assert "招募说明书" in item["title"]

    def test_list_announcements_date_range(self, client):
        """按日期范围筛选应生效"""
        res = client.get("/api/announcements?start_date=2024-01-01&end_date=2024-12-31")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        items = data["data"]
        for item in items:
            date = item["publish_date"]
            assert "2024-" in date

    def test_list_announcements_combined_filters(self, client):
        """组合筛选应生效"""
        res = client.get("/api/announcements?fund_code=508000&category=financial&page_size=3")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        items = data["data"]
        assert len(items) <= 3
        for item in items:
            assert item["fund_code"] == "508000"
            assert item["category"] == "financial"

    def test_list_announcements_invalid_page(self, client):
        """无效分页参数应返回空列表但不报错"""
        res = client.get("/api/announcements?page=99999")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert len(data["data"]) == 0


class TestAnnouncementStats:
    """测试公告统计API"""

    def test_announcements_stats(self, client):
        """统计接口应返回正确结构"""
        res = client.get("/api/announcements/stats")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "data" in data
        stats = data["data"]
        assert "total" in stats
        assert "by_exchange" in stats
        assert "by_category" in stats
        assert "funds_count" in stats
        assert isinstance(stats["total"], int)
        assert isinstance(stats["by_exchange"], dict)
        assert isinstance(stats["by_category"], dict)
