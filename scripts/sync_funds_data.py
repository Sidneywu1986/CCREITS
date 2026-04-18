#!/usr/bin/env python3
"""
数据同步脚本 - 以Excel文件为基准同步基金数据
"""

import pandas as pd
import json
import os
from pathlib import Path
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataSynchronizer:
    """数据同步器"""

    def __init__(self, excel_path: str, json_path: str):
        self.excel_path = excel_path
        self.json_path = json_path
        self.excel_data = None
        self.json_data = None

    def load_excel_data(self) -> pd.DataFrame:
        """加载Excel数据"""
        try:
            df = pd.read_excel(self.excel_path)
            # 假设Excel格式：序号、基金代码、基金名称、资产类型
            df.columns = ['index', 'code', 'name', 'sector']
            self.excel_data = df
            logger.info(f"成功加载Excel数据: {len(df)} 行")
            return df
        except Exception as e:
            logger.error(f"加载Excel数据失败: {e}")
            raise

    def load_json_data(self) -> dict:
        """加载JSON数据"""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                self.json_data = json.load(f)
            logger.info(f"成功加载JSON数据: {self.json_data.get('total', 0)} 条记录")
            return self.json_data
        except Exception as e:
            logger.error(f"加载JSON数据失败: {e}")
            raise

    def create_standard_json(self, output_path: str):
        """创建标准化的JSON数据文件"""
        if self.excel_data is None:
            self.load_excel_data()

        # 创建标准格式的基金数据
        funds = []
        for _, row in self.excel_data.iterrows():
            fund = {
                "code": str(row['code']),
                "name": row['name'],
                "short_name": row['name'][:10] + "REIT" if len(row['name']) > 10 else row['name'],
                "sector": row['sector']
            }
            funds.append(fund)

        # 创建标准JSON结构
        standard_data = {
            "total": len(funds),
            "update_time": "2026-04-16",
            "funds": funds
        }

        # 保存到新文件
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(standard_data, f, ensure_ascii=False, indent=2)
            logger.info(f"标准化JSON数据已保存: {output_path}")
            logger.info(f"基金总数: {len(funds)}")
        except Exception as e:
            logger.error(f"保存标准化JSON失败: {e}")
            raise

        return standard_data


def main():
    """主函数"""
    # 文件路径
    excel_path = "data/中国公募REITs完整分类清单_81只_20260405.xlsx"
    json_path = "data/reits_funds_79.json"
    output_path = "data/reits_funds_81_standardized.json"

    if not os.path.exists(excel_path):
        logger.error(f"Excel文件不存在: {excel_path}")
        return

    # 创建同步器
    synchronizer = DataSynchronizer(excel_path, json_path)

    try:
        # 加载Excel数据
        synchronizer.load_excel_data()

        # 创建标准化JSON
        standard_data = synchronizer.create_standard_json(output_path)

        # 验证结果
        print("\n" + "="*60)
        print("数据同步结果")
        print("="*60)
        print(f"Excel文件基金数量: {len(synchronizer.excel_data)}")
        print(f"标准化JSON基金数量: {standard_data['total']}")
        print(f"输出文件: {output_path}")

        # 显示前10只基金
        print("\n前10只基金:")
        for i, fund in enumerate(standard_data['funds'][:10], 1):
            print(f"  {i:2d}. {fund['code']} - {fund['name']} ({fund['sector']})")

        print(f"\n数据同步完成！")
        print(f"请使用 {output_path} 替换原有的JSON文件")

    except Exception as e:
        logger.error(f"数据同步失败: {e}")
        return


if __name__ == "__main__":
    main()