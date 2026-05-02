"""
TDD: 公告数据质量检查API测试
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


class TestAnnouncementsQuality:
    """测试公告数据质量检查API"""

    def test_quality_report_structure(self, client):
        """质量报告应包含所有关键字段"""
        res = client.get("/api/announcements/quality")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        report = data["data"]
        assert "total" in report
        assert "missing_pdf" in report
        assert "missing_category" in report
        assert "duplicate_titles" in report
        assert "suspicious_dates" in report
        assert "funds_count" in report
        assert "low_confidence" in report

    def test_quality_report_types(self, client):
        """质量报告数值应为正确类型"""
        res = client.get("/api/announcements/quality")
        assert res.status_code == 200
        data = res.json()
        report = data["data"]
        assert isinstance(report["total"], int)
        assert isinstance(report["missing_pdf"], int)
        assert isinstance(report["missing_category"], int)
        assert isinstance(report["duplicate_titles"], int)
        assert isinstance(report["suspicious_dates"], int)
        assert isinstance(report["funds_count"], int)
        assert isinstance(report["low_confidence"], int)

    def test_quality_report_consistency(self, client):
        """质量报告内部一致性检查"""
        res = client.get("/api/announcements/quality")
        assert res.status_code == 200
        data = res.json()
        report = data["data"]
        assert report["missing_pdf"] <= report["total"]
        assert report["missing_category"] <= report["total"]
        assert report["duplicate_titles"] <= report["total"]
        assert report["suspicious_dates"] <= report["total"]
        assert report["low_confidence"] <= report["total"]

    def test_quality_by_fund_structure(self, client):
        """按基金质量检查应返回正确结构"""
        res = client.get("/api/announcements/quality/by-fund?fund_code=508000")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        report = data["data"]
        assert "fund_code" in report
        assert "total" in report
        assert "missing_pdf" in report
        assert "categories" in report
        assert isinstance(report["categories"], dict)

    def test_quality_by_fund_invalid_code(self, client):
        """无效基金代码应返回空报告但不报错"""
        res = client.get("/api/announcements/quality/by-fund?fund_code=999999")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["data"]["total"] == 0
