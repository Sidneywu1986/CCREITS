#!/usr/bin/env python3
"""从 dividend_correction.json 导入分红数据到 dividends 表"""
import json
import sqlite3
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'database', 'reits.db')
JSON_PATH = os.path.join(BASE_DIR, 'dividend_correction.json')

def import_dividends():
    if not os.path.exists(JSON_PATH):
        print(f"找不到文件: {JSON_PATH}")
        return 0
    
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        funds = json.load(f)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    inserted = 0
    for fund in funds:
        code = fund.get('code')
        for div in fund.get('dividends', []):
            date_str = div.get('date')
            amount = div.get('amount')
            if not date_str or amount is None:
                continue
            # 转换日期格式 20250909 -> 2025-09-09
            if len(date_str) == 8 and date_str.isdigit():
                formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
            else:
                formatted_date = date_str
            
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO dividends 
                    (fund_code, dividend_date, dividend_amount, record_date, ex_dividend_date, created_at)
                    VALUES (?, ?, ?, ?, ?, datetime('now'))
                """, (code, formatted_date, amount, formatted_date, formatted_date))
                if cursor.rowcount > 0:
                    inserted += 1
            except Exception as e:
                print(f"插入失败 {code} {formatted_date}: {e}")
    
    conn.commit()
    conn.close()
    print(f"导入完成: {inserted} 条分红记录")
    return inserted

if __name__ == '__main__':
    import_dividends()
