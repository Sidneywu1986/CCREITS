#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入巨潮资讯网爬取的公告数据到数据库
"""

import os
import sys
import sqlite3
import re
from pathlib import Path
from datetime import datetime

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'reits.db')

# 爬虫数据目录
CRAWLER_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'announcements')


def guess_category(title):
    """根据标题猜测公告分类"""
    dividend_keywords = ['分红', '派息', '收益分配', '权益分派', '每份派', '收益分配']
    financial_keywords = ['年报', '季报', '半年报', '审计报告', '财务']
    inquiry_keywords = ['问询函', '关注函', '回复']
    
    title_lower = title.lower()
    if any(k in title_lower for k in dividend_keywords):
        return 'dividend'
    elif any(k in title_lower for k in financial_keywords):
        return 'financial'
    elif any(k in title_lower for k in inquiry_keywords):
        return 'inquiry'
    else:
        return 'operation'


def parse_date_from_filename(filename):
    """从文件名解析日期"""
    match = re.search(r'(\d{8})', filename)
    if match:
        date_str = match.group(1)
        try:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        except:
            pass
    return datetime.now().strftime('%Y-%m-%d')


def import_announcements():
    """导入公告到数据库"""
    print("="*60)
    print("导入巨潮资讯网公告数据")
    print("="*60)
    
    if not os.path.exists(DB_PATH):
        print(f"错误: 数据库不存在 {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    imported_count = 0
    
    # 扫描爬虫数据目录
    if os.path.exists(CRAWLER_DATA_DIR):
        for folder in os.listdir(CRAWLER_DATA_DIR):
            folder_path = os.path.join(CRAWLER_DATA_DIR, folder)
            if not os.path.isdir(folder_path):
                continue
            
            # 解析基金代码
            fund_code = folder.split('_')[0] if '_' in folder else folder
            
            # 扫描PDF文件
            for filename in os.listdir(folder_path):
                if not filename.endswith('.pdf'):
                    continue
                
                # 解析标题
                title_match = re.search(r'\d{8}_(.+?)\.pdf$', filename)
                if title_match:
                    title = title_match.group(1)
                else:
                    title = filename.replace('.pdf', '')
                
                # 解析日期
                publish_date = parse_date_from_filename(filename)
                
                # 猜测分类
                category = guess_category(title)
                
                # 判断交易所
                exchange = 'SZSE' if fund_code.startswith('180') else 'SSE'
                
                # 文件路径
                pdf_path = os.path.join(folder_path, filename)
                file_url = f"file:///{pdf_path.replace('\\', '/')}"
                
                # 插入数据库
                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO announcements 
                        (fund_code, title, category, publish_date, source_url, exchange, is_read, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, 0, datetime('now'))
                    ''', (fund_code, title, category, publish_date, file_url, exchange))
                    
                    if cursor.rowcount > 0:
                        imported_count += 1
                except Exception as e:
                    print(f"导入失败 {filename}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n导入完成！新增 {imported_count} 条公告")
    print("="*60)


if __name__ == '__main__':
    import_announcements()
