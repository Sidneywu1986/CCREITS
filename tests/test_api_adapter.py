#!/usr/bin/env python3
"""
API适配层测试 - TDD模式
"""

import pytest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.api_adapter import (
    load_funds_data,
    get_fund_detail_mock,
    get_price_history_mock,
    get_financial_data_mock,
    get_operation_data_mock
)


class TestApiAdapter:
    """API适配层测试类"""

    def test_load_funds_data(self):
        """测试加载基金数据"""
        data = load_funds_data()

        assert "funds" in data
        assert "total" in data
        assert isinstance(data["funds"], list)
        assert isinstance(data["total"], int)

        if data["total"] > 0:
            # 验证数据结构
            fund = data["funds"][0]
            assert "code" in fund
            assert "name" in fund
            assert "short_name" in fund

    def test_fund_detail_mock_existing_fund(self):
        """测试获取已存在基金的Mock详情"""
        import asyncio
        result = asyncio.run(get_fund_detail_mock("508001"))

        assert result["success"] == True
        assert result["data"] is not None
        assert result["data"]["code"] == "508001"
        assert "price" in result["data"]
        assert "nav" in result["data"]
        assert "change_percent" in result["data"]

    def test_fund_detail_mock_nonexistent_fund(self):
        """测试获取不存在基金的Mock详情"""
        import asyncio
        result = asyncio.run(get_fund_detail_mock("999999"))

        assert result["success"] == False
        assert result["data"] is None
        assert "基金不存在" in result["message"]

    def test_price_history_mock_daily(self):
        """测试获取日线价格历史Mock数据"""
        import asyncio
        result = asyncio.run(get_price_history_mock("508001", "daily"))

        assert result["success"] == True
        assert isinstance(result["data"], list)
        assert len(result["data"]) > 0

        # 验证数据结构
        item = result["data"][0]
        assert "date" in item
        assert "nav" in item
        assert "price" in item
        assert "volume" in item

    def test_price_history_mock_minute(self):
        """测试获取分时价格历史Mock数据"""
        import asyncio
        result = asyncio.run(get_price_history_mock("508001", "minute"))

        assert result["success"] == True
        assert isinstance(result["data"], list)
        assert len(result["data"]) > 0

        # 验证数据结构
        item = result["data"][0]
        assert "time" in item
        assert "price" in item
        assert "volume" in item

    def test_price_history_mock_weekly(self):
        """测试获取周线价格历史Mock数据"""
        import asyncio
        result = asyncio.run(get_price_history_mock("508001", "weekly"))

        assert result["success"] == True
        assert isinstance(result["data"], list)
        assert len(result["data"]) > 0

    def test_financial_data_mock(self):
        """测试获取财务数据Mock"""
        import asyncio
        result = asyncio.run(get_financial_data_mock("508001"))

        assert result["success"] == True
        assert result["data"] is not None

        # 验证财务数据结构
        data = result["data"]
        assert "fund_code" in data
        assert "total_assets" in data
        assert "net_assets" in data
        assert "total_revenue" in data
        assert "net_profit" in data
        assert "eps" in data
        assert "nav_per_share" in data
        assert "debt_ratio" in data

    def test_operation_data_mock(self):
        """测试获取运营数据Mock"""
        import asyncio
        result = asyncio.run(get_operation_data_mock("508001"))

        assert result["success"] == True
        assert result["data"] is not None

        # 验证运营数据结构
        data = result["data"]
        assert "fund_code" in data
        assert "operation_date" in data
        assert "occupancy_rate" in data
        assert "average_lease_term" in data
        assert "rental_income" in data
        assert "total_income" in data
        assert "nav" in data
        assert "dividend_per_share" in data

    def test_data_consistency(self):
        """测试数据一致性"""
        import asyncio

        # 获取基金详情
        detail_result = asyncio.run(get_fund_detail_mock("508001"))
        # 获取价格历史
        history_result = asyncio.run(get_price_history_mock("508001", "daily"))

        assert detail_result["success"] == True
        assert history_result["success"] == True

        # 基金代码应该一致
        assert detail_result["data"]["code"] == "508001"

    def test_response_format(self):
        """测试响应格式一致性"""
        import asyncio

        # 测试各种Mock函数的响应格式
        functions = [
            get_fund_detail_mock,
            get_price_history_mock,
            get_financial_data_mock,
            get_operation_data_mock
        ]

        for func in functions:
            result = asyncio.run(func("508001"))
            # 所有响应都应该包含success、data、message字段
            assert "success" in result
            assert "data" in result
            assert "message" in result
            # success应该是布尔值
            assert isinstance(result["success"], bool)
            # message应该是字符串
            assert isinstance(result["message"], str)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])