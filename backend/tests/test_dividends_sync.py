"""
TDD: 分红数据同步与API测试
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


class TestDividendSync:
    """测试分红数据同步"""

    def test_parse_dividend_amount(self):
        """解析分红金额文本"""
        from services.dividend_sync import parse_dividend_amount
        assert parse_dividend_amount("每份派现金0.0549元") == 0.0549
        assert parse_dividend_amount("每份派现金0.5000元") == 0.5
        assert parse_dividend_amount("暂无分红") is None
        assert parse_dividend_amount("") is None

    def test_fetch_single_fund_dividends(self):
        """获取单只基金分红数据"""
        from services.dividend_sync import fetch_fund_dividends
        data = fetch_fund_dividends("508000")
        assert isinstance(data, list)
        if len(data) > 0:
            item = data[0]
            assert "fund_code" in item
            assert "dividend_year" in item
            assert "record_date" in item
            assert "ex_dividend_date" in item
            assert "dividend_per_share" in item
            assert "dividend_payment_date" in item
            assert item["fund_code"] == "508000"

    def test_sync_dividends_to_db(self):
        """同步分红数据到数据库"""
        from services.dividend_sync import sync_fund_dividends
        count = sync_fund_dividends("508000")
        assert isinstance(count, int)
        assert count >= 0


class TestDividendAPI:
    """测试分红数据API"""

    def test_dividend_list(self, client):
        """分红列表API应返回正确结构"""
        res = client.get("/api/dividends")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "data" in data
        assert "total" in data

    def test_dividend_by_fund(self, client):
        """按基金查询分红"""
        res = client.get("/api/dividends?fund_code=508000")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        for item in data["data"]:
            assert item["fund_code"] == "508000"

    def test_dividend_stats(self, client):
        """分红统计API"""
        res = client.get("/api/dividends/stats")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        stats = data["data"]
        assert "total" in stats
        assert "total_amount" in stats
        assert "funds_with_dividends" in stats
        assert isinstance(stats["total"], int)
