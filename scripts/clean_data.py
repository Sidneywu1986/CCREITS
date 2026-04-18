#!/usr/bin/env python3
"""
数据清洗脚本 - 修复reits_funds_79.json中的重复记录问题
"""

import json
import os
import sys
from collections import Counter
from typing import Dict, List, Any
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_clean.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class DataCleaner:
    """数据清洗器"""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.data = None
        self.duplicates = {}

    def load_data(self) -> Dict[str, Any]:
        """加载JSON数据"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            logger.info(f"成功加载数据文件: {self.file_path}")
            logger.info(f"总基金数量: {self.data.get('total', 0)}")
            return self.data
        except Exception as e:
            logger.error(f"加载数据文件失败: {e}")
            raise

    def find_duplicates(self, funds: List[Dict]) -> Dict[str, List[Dict]]:
        """查找重复记录"""
        codes = [f['code'] for f in funds]
        code_counts = Counter(codes)

        duplicates = {}
        for code, count in code_counts.items():
            if count > 1:
                dup_funds = [f for f in funds if f['code'] == code]
                duplicates[code] = dup_funds
                logger.warning(f"发现重复: {code} 出现 {count} 次")

        self.duplicates = duplicates
        return duplicates

    def analyze_duplicates(self):
        """分析重复记录的类型"""
        if not self.duplicates:
            logger.info("没有发现重复记录")
            return

        logger.info(f"\n{'='*60}")
        logger.info(f"重复记录详细分析")
        logger.info(f"{'='*60}")

        for code, funds in self.duplicates.items():
            logger.info(f"\n基金代码: {code} (重复 {len(funds)} 次)")

            # 检查名称是否相同
            names = [f['name'] for f in funds]
            unique_names = set(names)

            if len(unique_names) == 1:
                logger.info(f"  类型: 完全重复 (名称相同)")
                logger.info(f"  名称: {names[0]}")
            else:
                logger.info(f"  类型: 名称冲突 (不同名称)")
                for i, fund in enumerate(funds):
                    logger.info(f"    第{i+1}次: {fund['name']} (简称: {fund['short_name']})")

    def validate_fund(self, fund: Dict) -> bool:
        """验证基金数据完整性"""
        required_fields = ['code', 'name', 'short_name']

        for field in required_fields:
            if not fund.get(field):
                logger.error(f"基金数据不完整: 缺少字段 {field}")
                return False

        if not fund['code'].isdigit():
            logger.error(f"基金代码格式错误: {fund['code']}")
            return False

        return True

    def remove_duplicates(self, funds: List[Dict], code: str) -> List[Dict]:
        """移除指定代码的重复记录，保留第一条有效记录"""
        group = [f for f in funds if f['code'] == code]

        if len(group) == 0:
            return []
        if len(group) == 1:
            return [group[0]] if self.validate_fund(group[0]) else []

        # 有重复，需要处理
        logger.info(f"处理重复代码: {code} ({len(group)} 条记录)")

        # 检查是否所有名称都相同
        names = [f['name'] for f in group]
        unique_names = set(names)

        if len(unique_names) == 1:
            # 完全重复，保留第一条有效记录
            logger.info(f"  完全重复，保留第一条记录: {names[0]}")
            for fund in group:
                if self.validate_fund(fund):
                    return [fund]
            return []
        else:
            # 名称冲突，需要人工判断
            logger.warning(f"  名称冲突，保留第一条记录:")
            for i, name in enumerate(unique_names):
                logger.warning(f"    选项{i+1}: {name}")

            # 保留第一条有效记录
            for fund in group:
                if self.validate_fund(fund):
                    logger.info(f"  保留: {fund['name']}")
                    return [fund]
            return []

    def clean_duplicates(self) -> List[Dict]:
        """清理重复记录"""
        if not self.data:
            raise ValueError("未加载数据")

        funds = self.data['funds']
        cleaned_funds = []

        # 按代码分组处理
        code_groups = {}
        for fund in funds:
            code = fund['code']
            if code not in code_groups:
                code_groups[code] = []
            code_groups[code].append(fund)

        # 处理每个代码组
        for code, group in code_groups.items():
            if len(group) == 1:
                # 无重复，直接添加
                if self.validate_fund(group[0]):
                    cleaned_funds.append(group[0])
            else:
                # 有重复，使用remove_duplicates处理
                unique_funds = self.remove_duplicates(funds, code)
                cleaned_funds.extend(unique_funds)

        logger.info(f"清理完成: 从 {len(funds)} 条记录清理到 {len(cleaned_funds)} 条")
        return cleaned_funds

    def clean_and_save(self, output_path: str = None):
        """执行清洗并保存结果"""
        if not output_path:
            output_path = self.file_path.replace('.json', '_cleaned.json')

        # 加载数据
        self.load_data()

        # 查找重复记录
        self.find_duplicates(self.data['funds'])

        # 分析重复记录
        self.analyze_duplicates()

        # 清理重复记录
        cleaned_funds = self.clean_duplicates()

        # 创建清洗后的数据
        cleaned_data = {
            "total": len(cleaned_funds),
            "update_time": self.data.get('update_time', ''),
            "funds": cleaned_funds,
            "cleaning_info": {
                "original_total": self.data.get('total', 0),
                "removed_duplicates": self.data.get('total', 0) - len(cleaned_funds),
                "duplicate_codes": list(self.duplicates.keys())
            }
        }

        # 保存清洗后的数据
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
            logger.info(f"清洗后的数据已保存: {output_path}")
        except Exception as e:
            logger.error(f"保存清洗数据失败: {e}")
            raise

        return cleaned_data

    def backup_original(self):
        """备份原始文件"""
        backup_path = self.file_path + '.backup'
        try:
            import shutil
            shutil.copy2(self.file_path, backup_path)
            logger.info(f"原始文件已备份: {backup_path}")
        except Exception as e:
            logger.error(f"备份原始文件失败: {e}")


def main():
    """主函数"""
    data_path = "data/reits_funds_79.json"
    output_path = "data/reits_funds_79_cleaned.json"

    if not os.path.exists(data_path):
        logger.error(f"数据文件不存在: {data_path}")
        sys.exit(1)

    try:
        # 创建清洗器
        cleaner = DataCleaner(data_path)

        # 备份原始文件
        cleaner.backup_original()

        # 执行清洗
        cleaned_data = cleaner.clean_and_save(output_path)

        # 统计结果
        logger.info(f"\n{'='*60}")
        logger.info(f"清洗结果统计")
        logger.info(f"{'='*60}")
        logger.info(f"原始记录数: {cleaned_data['cleaning_info']['original_total']}")
        logger.info(f"清洗后记录数: {cleaned_data['total']}")
        logger.info(f"移除重复记录: {cleaned_data['cleaning_info']['removed_duplicates']}")
        logger.info(f"唯一基金代码数: {len(set(f['code'] for f in cleaned_data['funds']))}")

        logger.info(f"\n数据清洗完成！")
        logger.info(f"清洗后的文件: {output_path}")
        logger.info(f"日志文件: data_clean.log")

    except Exception as e:
        logger.error(f"数据清洗失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()