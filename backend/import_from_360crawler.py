#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从360Downloads爬虫目录导入公告数据到数据库
源目录: D:\360Downloads\crawler
"""

import sqlite3
import json
import os
import re
from datetime import datetime
from pathlib import Path

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'reits.db')
CRAWLER_DIR = r'D:\360Downloads\crawler\announcements'

def get_crawl_report():
    """读取爬取报告"""
    report_file = os.path.join(CRAWLER_DIR, 'final_crawl_report.json')
    if os.path.exists(report_file):
        with open(report_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def scan_announcement_folders():
    """扫描公告文件夹"""
    announcements = []
    
    for item in os.listdir(CRAWLER_DIR):
        item_path = os.path.join(CRAWLER_DIR, item)
        
        # 匹配REIT公告文件夹
        match = re.match(r'^(\d{6})_(.+)_公告$', item)
        if match and os.path.isdir(item_path):
            code = match.group(1)
            name = match.group(2)
            
            # 扫描PDF文件
            pdf_files = []
            for file in os.listdir(item_path):
                if file.endswith('.pdf'):
                    pdf_path = os.path.join(item_path, file)
                    pdf_match = re.match(r'^(\d{8})_(.+)\.pdf$', file)
                    if pdf_match:
                        date_str = pdf_match.group(1)
                        title = pdf_match.group(2)
                        try:
                            date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
                        except:
                            date = date_str
                        
                        pdf_files.append({
                            'file': file,
                            'path': pdf_path,
                            'date': date,
                            'title': title
                        })
            
            announcements.append({
                'code': code,
                'name': name,
                'folder': item,
                'pdfs': pdf_files
            })
    
    return announcements

def classify_announcement(title):
    """分类公告"""
    title = title.lower()
    
    if any(kw in title for kw in ['分红', '收益分配', '现金红利', '权益分派']):
        return 'dividend'
    elif any(kw in title for kw in ['年报', '中报', '季报', '审计报告', '评估报告']):
        return 'financial'
    elif any(kw in title for kw in ['问询', '关注函', '监管']):
        return 'inquiry'
    elif any(kw in title for kw in ['扩募', '发售', '认购']):
        return 'offering'
    else:
        return 'operation'

def import_to_database(announcements):
    """导入数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    total_imported = 0
    
    for reit in announcements:
        code = reit['code']
        name = reit['name']
        pdfs = reit['pdfs']
        
        exchange = 'SZSE' if code.startswith('180') else 'SSE'
        
        imported = 0
        for pdf in pdfs:
            try:
                category = classify_announcement(pdf['title'])
                pdf_path_normalized = pdf['path'].replace('\\', '/')
                pdf_url = f"file:///{pdf_path_normalized}"
                
                cursor.execute("""
                    INSERT OR IGNORE INTO announcements 
                    (fund_code, title, category, publish_date, source_url, exchange, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                """, (
                    code,
                    pdf['title'],
                    category,
                    pdf['date'],
                    pdf_url,
                    exchange
                ))
                
                if cursor.rowcount > 0:
                    imported += 1
                    
            except Exception as e:
                print(f"  [ERROR] {code} - {pdf['file']}: {e}")
        
        total_imported += imported
        print(f"OK {code} ({name}): {imported}/{len(pdfs)}")
    
    conn.commit()
    conn.close()
    
    return total_imported

def main():
    print("="*60)
    print("Import from 360 crawler")
    print("="*60)
    
    # 读取报告
    report = get_crawl_report()
    if report:
        print(f"\nReport:")
        print(f"  Total REITs: {report.get('total_reits', 'N/A')}")
        print(f"  Total PDFs: {report.get('total_pdfs', 'N/A')}")
    
    # 扫描文件夹
    print("\nScanning folders...")
    announcements = scan_announcement_folders()
    print(f"  Found {len(announcements)} REITs")
    
    total_pdfs = sum(len(reit['pdfs']) for reit in announcements)
    print(f"  Total PDFs: {total_pdfs}")
    
    # 导入
    print("\nImporting to database...")
    imported = import_to_database(announcements)
    
    print("\n" + "="*60)
    print(f"DONE! Imported: {imported}")
    print("="*60)
    
    # 统计
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM announcements')
    total = cursor.fetchone()[0]
    cursor.execute('SELECT category, COUNT(*) FROM announcements GROUP BY category')
    categories = cursor.fetchall()
    conn.close()
    
    print(f"\nDatabase stats:")
    print(f"  Total: {total}")
    for cat, count in categories:
        print(f"    {cat}: {count}")

if __name__ == '__main__':
    main()
