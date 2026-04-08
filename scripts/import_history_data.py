#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入81只REITs历史日线数据到数据库
从 data/rixian/ 目录读取txt文件
"""

import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

# 路径配置
DATA_DIR = Path(__file__).parent.parent / 'data' / 'rixian'
DB_PATH = Path(__file__).parent.parent / 'backend' / 'database' / 'reits.db'

def parse_file(filepath):
    """解析单个历史数据文件"""
    fund_code = filepath.stem.replace('SH#', '').replace('SZ#', '')
    
    records = []
    with open(filepath, 'r', encoding='gbk', errors='ignore') as f:
        lines = f.readlines()
    
    # 第一行是标题，包含基金名称
    header = lines[0].strip() if lines else ''
    fund_name_match = re.search(r'\d{6}\s+(.+?)\s', header)
    fund_name = fund_name_match.group(1) if fund_name_match else ''
    
    # 第二行是列名
    # 第三行开始是数据
    for line in lines[2:]:
        line = line.strip()
        if not line:
            continue
        
        parts = line.split('\t')
        if len(parts) < 7:
            continue
        
        try:
            date_str = parts[0]
            # 转换日期格式 2021/06/21 -> 2021-06-21
            date = datetime.strptime(date_str, '%Y/%m/%d').strftime('%Y-%m-%d')
            
            record = {
                'fund_code': fund_code,
                'date': date,
                'open': float(parts[1]),
                'high': float(parts[2]),
                'low': float(parts[3]),
                'close': float(parts[4]),
                'volume': int(float(parts[5])),
                'amount': float(parts[6])
            }
            records.append(record)
        except (ValueError, IndexError) as e:
            print(f"  解析行失败: {line}, 错误: {e}")
            continue
    
    return {
        'code': fund_code,
        'name': fund_name,
        'records': records
    }

def import_to_database():
    """导入所有数据到数据库"""
    print('='*70)
    print('导入81只REITs历史日线数据')
    print('='*70)
    print()
    
    # 检查目录
    if not DATA_DIR.exists():
        print(f'[错误] 数据目录不存在: {DATA_DIR}')
        return
    
    # 获取所有txt文件
    txt_files = sorted(DATA_DIR.glob('*.txt'))
    print(f'[*] 找到 {len(txt_files)} 个数据文件')
    print()
    
    # 连接数据库
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 清空历史数据表
    print('[*] 清空历史数据表...')
    cursor.execute('DELETE FROM price_history')
    conn.commit()
    print('[OK] 已清空')
    print()
    
    # 统计
    total_records = 0
    success_count = 0
    
    # 逐个导入
    for i, filepath in enumerate(txt_files, 1):
        try:
            data = parse_file(filepath)
            records = data['records']
            
            if not records:
                print(f'[{i:2d}/{len(txt_files)}] {data["code"]} - 无数据')
                continue
            
            # 批量插入
            cursor.executemany('''
                INSERT OR REPLACE INTO price_history 
                (fund_code, date, open, high, low, close, volume, amount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', [
                (r['fund_code'], r['date'], r['open'], r['high'], 
                 r['low'], r['close'], r['volume'], r['amount'])
                for r in records
            ])
            conn.commit()
            
            total_records += len(records)
            success_count += 1
            
            date_range = f"{records[0]['date']} ~ {records[-1]['date']}"
            print(f'[{i:2d}/{len(txt_files)}] {data["code"]} - {len(records):4d}条 - {date_range}')
            
        except Exception as e:
            print(f'[{i:2d}/{len(txt_files)}] {filepath.name} - [错误] {e}')
    
    print()
    print('='*70)
    print('导入完成')
    print('='*70)
    print(f'成功导入: {success_count}/{len(txt_files)} 只基金')
    print(f'总记录数: {total_records:,} 条')
    
    # 统计
    cursor.execute('SELECT COUNT(DISTINCT fund_code) FROM price_history')
    fund_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM price_history')
    record_count = cursor.fetchone()[0]
    
    print(f'数据库统计: {fund_count} 只基金, {record_count:,} 条记录')
    
    # 显示数据日期范围
    cursor.execute('SELECT MIN(date), MAX(date) FROM price_history')
    min_date, max_date = cursor.fetchone()
    print(f'数据日期范围: {min_date} ~ {max_date}')
    
    conn.close()
    print('='*70)

if __name__ == '__main__':
    import_to_database()
