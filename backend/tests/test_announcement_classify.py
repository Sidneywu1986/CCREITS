"""
TDD: 公告分类优化测试
"""
import os
import sys

os.environ.setdefault("JWT_SECRET", "test-secret-key")
os.environ.setdefault("ADMIN_INITIAL_PASSWORD", "testadmin")
os.environ.setdefault("DEBUG", "true")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from services.announcements import classify_announcement


class TestClassifyAnnouncement:
    """测试公告分类准确性"""

    # === 财务报告类 ===
    def test_classify_annual_report(self):
        assert classify_announcement("2024年年度报告") == "financial"
        assert classify_announcement("2024年年度审计报告") == "financial"

    def test_classify_quarterly_report(self):
        assert classify_announcement("2024年第一季度报告") == "financial"
        assert classify_announcement("2024年半年度报告") == "financial"

    def test_classify_evaluation_report(self):
        assert classify_announcement("资产评估报告") == "financial"

    # === 分红类 ===
    def test_classify_dividend(self):
        assert classify_announcement("2024年度收益分配公告") == "dividend"
        assert classify_announcement("分红实施公告") == "dividend"
        assert classify_announcement("权益分派公告") == "dividend"

    # === 上市/募集类 ===
    def test_classify_listing(self):
        assert classify_announcement("招募说明书") == "listing"
        assert classify_announcement("上市交易公告书") == "listing"

    def test_classify_fund_contract(self):
        assert classify_announcement("基金合同") == "listing"
        assert classify_announcement("托管协议") == "listing"

    # === 运营类 ===
    def test_classify_operation(self):
        assert classify_announcement("2024年第4季度运营数据") == "operation"
        assert classify_announcement("出租率公告") == "operation"
        assert classify_announcement("车流量数据") == "operation"

    # === 问询类 ===
    def test_classify_inquiry(self):
        assert classify_announcement("关于审核问询函的回复") == "inquiry"
        assert classify_announcement("监管工作函") == "inquiry"

    # === 基金管理人变更类 ===
    def test_classify_manager_change(self):
        assert classify_announcement("关于基金管理人高级管理人员变更情况的公告") == "manager_change"
        assert classify_announcement("关于基金管理人总经理变更情况的公告") == "manager_change"
        assert classify_announcement("基金经理变更公告") == "manager_change"
        assert classify_announcement("董事长（法定代表人）、高级管理人员变更公告") == "manager_change"

    # === 基金事件类 ===
    def test_classify_fund_event(self):
        assert classify_announcement("基金份额持有人大会表决结果暨决议生效的公告") == "fund_event"
        assert classify_announcement("变更基金名称的公告") == "fund_event"
        assert classify_announcement("变更基金简称的公告") == "fund_event"

    # === 其他 ===
    def test_classify_other(self):
        assert classify_announcement("某某公告") == "other"
        assert classify_announcement("临时公告") == "other"
