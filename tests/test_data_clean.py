#!/usr/bin/env python3
"""
数据清洗测试 - TDD模式
"""

import pytest
import json
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.clean_data import DataCleaner


class TestDataCleaning:
    """数据清洗测试类"""

    @pytest.fixture
    def sample_data(self):
        """创建测试用的样本数据"""
        return {
            "total": 5,
            "update_time": "2026-04-06",
            "funds": [
                {"code": "508001", "name": "浙商证券沪杭甬高速REIT", "short_name": "浙商沪杭甬REIT"},
                {"code": "508001", "name": "浙商证券沪杭甬高速REIT", "short_name": "浙商沪杭甬REIT"},  # 重复
                {"code": "180101", "name": "博时招商蛇口产业园REIT", "short_name": "博时蛇口产园REIT"},
                {"code": "180106", "name": "中金印力消费基础设施REIT", "short_name": "中金印力消费REIT"},
                {"code": "180106", "name": "南方万国数据中心REIT", "short_name": "南方万国数据中心"},  # 不同名称的重复
            ]
        }

    @pytest.fixture
    def expected_clean_data(self):
        """期望的清洗后数据"""
        return {
            "total": 3,
            "update_time": "2026-04-06",
            "funds": [
                {"code": "508001", "name": "浙商证券沪杭甬高速REIT", "short_name": "浙商沪杭甬REIT"},
                {"code": "180101", "name": "博时招商蛇口产业园REIT", "short_name": "博时蛇口产园REIT"},
                {"code": "180106", "name": "中金印力消费基础设施REIT", "short_name": "中金印力消费REIT"},
            ]
        }

    def test_load_json_file(self, tmp_path):
        """测试JSON文件加载"""
        # 创建临时JSON文件
        test_data = {"total": 1, "funds": [{"code": "508001", "name": "Test REIT"}]}
        test_file = tmp_path / "test.json"
        with open(test_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, ensure_ascii=False)

        cleaner = DataCleaner(str(test_file))
        loaded_data = cleaner.load_data()

        assert loaded_data == test_data
        assert loaded_data['total'] == 1

    def test_find_duplicates(self, sample_data):
        """测试重复记录识别"""
        cleaner = DataCleaner("dummy_path")
        duplicates = cleaner.find_duplicates(sample_data['funds'])

        # 应该找到2个重复的code
        assert len(duplicates) == 2
        assert "508001" in duplicates
        assert "180106" in duplicates
        assert len(duplicates["508001"]) == 2  # 重复2次
        assert len(duplicates["180106"]) == 2  # 重复2次

    def test_remove_duplicates_same_name(self):
        """测试移除名称相同的重复记录"""
        funds = [
            {"code": "508001", "name": "Test REIT", "short_name": "Test"},
            {"code": "508001", "name": "Test REIT", "short_name": "Test"},  # 完全重复
        ]

        cleaner = DataCleaner("dummy_path")
        cleaned = cleaner.remove_duplicates(funds, "508001")

        assert len(cleaned) == 1
        assert cleaned[0]['code'] == "508001"

    def test_remove_duplicates_different_name(self):
        """测试处理名称不同的重复记录"""
        funds = [
            {"code": "180106", "name": "REIT A", "short_name": "A"},
            {"code": "180106", "name": "REIT B", "short_name": "B"},  # 不同名称
        ]

        cleaner = DataCleaner("dummy_path")
        cleaned = cleaner.remove_duplicates(funds, "180106")

        # 应该保留第一条记录，并记录警告
        assert len(cleaned) == 1
        assert cleaned[0]['name'] == "REIT A"

    def test_clean_data_integration(self, sample_data, expected_clean_data, tmp_path):
        """测试完整的数据清洗流程"""
        # 创建临时输入文件
        input_file = tmp_path / "input.json"
        with open(input_file, 'w', encoding='utf-8') as f:
            json.dump(sample_data, f, ensure_ascii=False)

        # 创建临时输出文件
        output_file = tmp_path / "output.json"

        # 执行清洗
        cleaner = DataCleaner(str(input_file))
        cleaner.clean_and_save(str(output_file))

        # 验证结果
        with open(output_file, 'r', encoding='utf-8') as f:
            result = json.load(f)

        assert result['total'] == expected_clean_data['total']
        assert len(result['funds']) == len(expected_clean_data['funds'])

        # 验证每个基金都存在
        result_codes = {f['code'] for f in result['funds']}
        expected_codes = {f['code'] for f in expected_clean_data['funds']}
        assert result_codes == expected_codes

    def test_data_integrity_validation(self):
        """测试数据完整性验证"""
        valid_funds = [
            {"code": "508001", "name": "Test REIT", "short_name": "Test"},
            {"code": "180101", "name": "Another REIT", "short_name": "Another"},
        ]

        invalid_funds = [
            {"code": "508001", "name": "", "short_name": "Test"},  # 空名称
            {"code": "", "name": "Test REIT", "short_name": "Test"},  # 空代码
        ]

        cleaner = DataCleaner("dummy_path")

        assert cleaner.validate_fund(valid_funds[0]) == True
        assert cleaner.validate_fund(valid_funds[1]) == True
        assert cleaner.validate_fund(invalid_funds[0]) == False
        assert cleaner.validate_fund(invalid_funds[1]) == False

    def test_real_data_file(self):
        """测试真实数据文件"""
        data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                "data", "reits_funds_79.json")

        if not os.path.exists(data_path):
            pytest.skip(f"数据文件不存在: {data_path}")

        cleaner = DataCleaner(data_path)
        data = cleaner.load_data()

        # 验证基本结构
        assert 'total' in data
        assert 'funds' in data
        assert len(data['funds']) == data['total']

        # 检查重复记录
        codes = [f['code'] for f in data['funds']]
        unique_codes = set(codes)
        duplicates = [code for code in unique_codes if codes.count(code) > 1]

        # 应该存在重复记录（这是我们需要修复的问题）
        print(f"发现 {len(duplicates)} 个重复的基金代码: {duplicates}")
        for dup in duplicates:
            count = codes.count(dup)
            print(f"  - {dup}: 出现 {count} 次")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])