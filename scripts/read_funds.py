#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REITs 基金列表读取示例
"""

import json
import csv

def read_json():
    """读取 JSON 格式"""
    with open('reits_funds.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['funds']

def read_csv():
    """读取 CSV 格式"""
    funds = []
    with open('reits_funds.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            funds.append(row)
    return funds

def read_txt():
    """读取 TXT 格式"""
    funds = []
    with open('reits_funds_list.txt', 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '|' in line:
                parts = line.split('|')
                funds.append({
                    'code': parts[0],
                    'name': parts[1],
                    'sector': parts[2]
                })
    return funds

def main():
    print("=" * 50)
    print("REITs 基金列表读取示例")
    print("=" * 50)
    
    # 读取数据
    funds = read_json()
    
    print(f"\n共 {len(funds)} 只 REITs 基金\n")
    
    # 按板块分组统计
    sectors = {}
    for fund in funds:
        sector = fund['sector']
        if sector not in sectors:
            sectors[sector] = []
        sectors[sector].append(fund)
    
    print("按板块分布:")
    print("-" * 50)
    for sector, items in sorted(sectors.items(), key=lambda x: -len(x[1])):
        print(f"{sector:12s} : {len(items):2d} 只")
    
    print("\n" + "=" * 50)
    print("前 10 只基金示例:")
    print("-" * 50)
    for fund in funds[:10]:
        print(f"{fund['code']} | {fund['name']:20s} | {fund['sector']}")
    
    print("\n" + "=" * 50)
    print("文件说明:")
    print("  - reits_funds.json : JSON格式，适合程序读取")
    print("  - reits_funds.csv  : CSV格式，适合Excel打开")
    print("  - reits_funds_list.txt : 文本格式，便于阅读")
    print("=" * 50)

if __name__ == '__main__':
    main()
