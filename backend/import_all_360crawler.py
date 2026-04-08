#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从360Downloads所有子目录导入公告数据
"""

import sqlite3
import json
import os
import re

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'reits.db')
BASE_DIR = r'D:\360Downloads\crawler'

def find_all_pdf_folders(base_dir):
    """递归查找所有包含PDF的文件夹"""
    folders = []
    
    for root, dirs, files in os.walk(base_dir):
        # 检查是否有PDF文件
        pdf_files = [f for f in files if f.endswith('.pdf')]
        if pdf_files:
            # 检查文件夹名是否符合REIT格式
            folder_name = os.path.basename(root)
            match = re.match(r'^(\d{6})_(.+)$', folder_name)
            if match:
                code = match.group(1)
                name = match.group(2)
                
                pdfs = []
                for file in pdf_files:
                    file_path = os.path.join(root, file)
                    # 尝试从文件名提取日期
                    date_match = re.match(r'^(\d{8})', file)
                    if date_match:
                        date_str = date_match.group(1)
                        date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
                    else:
                        date = None
                    
                    # 提取标题（去掉.pdf和日期前缀）
                    title = re.sub(r'^\d{8}_', '', file.replace('.pdf', ''))
                    
                    pdfs.append({
                        'path': file_path,
                        'date': date,
                        'title': title
                    })
                
                folders.append({
                    'code': code,
                    'name': name,
                    'pdfs': pdfs
                })
    
    return folders

def classify_title(title):
    """分类"""
    t = title.lower()
    if any(kw in t for kw in ['分红', '收益分配', '现金红利']):
        return 'dividend'
    elif any(kw in t for kw in ['年报', '中报', '季报', '审计']):
        return 'financial'
    elif any(kw in t for kw in ['问询', '关注函']):
        return 'inquiry'
    else:
        return 'operation'

def import_to_db(folders):
    """导入数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    total = 0
    for folder in folders:
        code = folder['code']
        exchange = 'SZSE' if code.startswith('180') else 'SSE'
        
        for pdf in folder['pdfs']:
            try:
                category = classify_title(pdf['title'])
                pdf_path_norm = pdf['path'].replace('\\', '/')
                pdf_url = f"file:///{pdf_path_norm}"
                date = pdf['date'] or '2024-01-01'
                
                cursor.execute("""
                    INSERT OR IGNORE INTO announcements 
                    (fund_code, title, category, publish_date, source_url, exchange, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                """, (
                    code,
                    pdf['title'],
                    category,
                    date,
                    pdf_url,
                    exchange
                ))
                
                if cursor.rowcount > 0:
                    total += 1
                    
            except Exception as e:
                print(f"Error: {e}")
        
        print(f"OK {code}: {len(folder['pdfs'])} PDFs")
    
    conn.commit()
    conn.close()
    return total

def main():
    print("="*60)
    print("Import ALL from 360 crawler")
    print("="*60)
    
    print("\nScanning all folders...")
    folders = find_all_pdf_folders(BASE_DIR)
    print(f"Found {len(folders)} REIT folders")
    
    total_pdfs = sum(len(f['pdfs']) for f in folders)
    print(f"Total PDFs: {total_pdfs}")
    
    print("\nImporting...")
    imported = import_to_db(folders)
    
    print(f"\nDONE! Imported {imported} announcements")
    
    # 统计
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM announcements')
    total = cursor.fetchone()[0]
    print(f"Database total: {total}")
    conn.close()

if __name__ == '__main__':
    main()
