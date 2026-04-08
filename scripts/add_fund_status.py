#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
添加基金状态字段并标记基金
"""

import sqlite3
import sys

DB_PATH = r'D:\tools\消费看板5（前端）\backend\database\reits.db'

def main():
    print('='*60)
    print('添加基金状态字段')
    print('='*60)
    print()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. 检查是否已有status字段
    cursor.execute('PRAGMA table_info(funds)')
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'status' not in columns:
        print('[*] 添加 status 字段...')
        cursor.execute("ALTER TABLE funds ADD COLUMN status TEXT DEFAULT 'listed'")
        conn.commit()
        print('[OK] 字段已添加')
    else:
        print('[*] status 字段已存在')
    
    print()
    
    # 2. 标记已获批待上市的基金
    approved_funds = ['508020', '180503']
    print('[*] 标记刚获批基金...')
    for code in approved_funds:
        cursor.execute("UPDATE funds SET status = 'approved' WHERE code = ?", (code,))
        print(f'  {code} -> approved (已获批待上市)')
    
    conn.commit()
    
    # 3. 统计
    print()
    print('[*] 统计结果:')
    cursor.execute("SELECT status, COUNT(*) FROM funds GROUP BY status")
    for row in cursor.fetchall():
        status, count = row
        status_name = '已上市' if status == 'listed' else '已获批待上市'
        print(f'  {status} ({status_name}): {count}只')
    
    # 4. 显示刚获批的基金详情
    print()
    print('刚获批基金详情:')
    cursor.execute("SELECT code, name, sector_name FROM funds WHERE status = 'approved'")
    for row in cursor.fetchall():
        print(f'  {row[0]} | {row[1]} | {row[2]}')
    
    conn.close()
    print()
    print('='*60)
    print('完成')
    print('='*60)

if __name__ == '__main__':
    main()
