#!/usr/bin/env python3
"""
REIT成立日期和剩余期限爬虫
"""

import requests
import sqlite3
import re
import time
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'reits.db')

def fetch_fund_info(code):
    """获取基金详细信息"""
    try:
        url = f'https://fundf10.eastmoney.com/jbgk_{code}.html'
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = 'utf-8'
        html = resp.text
        
        result = {}
        
        # 成立日期 - 使用中文字符的通用匹配
        date_match = re.search(r'成立日期.*?(\d{4}-\d{2}-\d{2})', html)
        if date_match:
            result['listing_date'] = date_match.group(1)
        
        # 存续期限
        duration_match = re.search(r'存续期限.*?(\d+)', html)
        if duration_match:
            result['total_years'] = int(duration_match.group(1))
        
        # 基金规模
        scale_match = re.search(r'资产规模[\s\S]*?<td[^>]*>([\d.]+)\s*亿元', html)
        if scale_match:
            result['scale'] = float(scale_match.group(1))
        
        return result
    except Exception as e:
        print(f'  [Error] {code}: {e}')
        return {}

def calculate_remaining_years(listing_date, total_years):
    """计算剩余期限"""
    try:
        start = datetime.strptime(listing_date, '%Y-%m-%d')
        now = datetime.now()
        elapsed_days = (now - start).days
        elapsed_years = elapsed_days / 365.25
        remaining = total_years - elapsed_years
        if remaining > 0:
            return f'{remaining:.1f}年'
        return '即将到期'
    except:
        return None

def update_fund(code, data):
    """更新数据库"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        fields = []
        values = []
        
        if 'listing_date' in data:
            fields.append('listing_date = ?')
            values.append(data['listing_date'])
        
        if 'scale' in data:
            fields.append('scale = ?')
            values.append(data['scale'])
        
        if 'total_years' in data and 'listing_date' in data:
            remaining = calculate_remaining_years(data['listing_date'], data['total_years'])
            if remaining:
                fields.append('remaining_years = ?')
                values.append(remaining)
        
        if not fields:
            return False
        
        fields.append('updated_at = ?')
        values.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        values.append(code)
        
        sql = f'UPDATE funds SET {", ".join(fields)} WHERE code = ?'
        cursor.execute(sql, values)
        conn.commit()
        conn.close()
        return cursor.rowcount > 0
    except Exception as e:
        print(f'  [DB Error] {code}: {e}')
        return False

def crawl_all():
    """爬取所有缺失的基金"""
    # 获取列表
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT code, name FROM funds WHERE listing_date IS NULL ORDER BY code')
    funds = cursor.fetchall()
    conn.close()
    
    print(f'开始爬取 {len(funds)} 只REIT的成立日期...\n')
    
    success = 0
    for i, (code, name) in enumerate(funds):
        print(f'[{i+1}/{len(funds)}] {code} {name}')
        
        data = fetch_fund_info(code)
        if data:
            print(f"  成立: {data.get('listing_date', '--')} | 期限: {data.get('total_years', '--')}年 | 规模: {data.get('scale', '--')}亿")
            
            if update_fund(code, data):
                print(f'  [OK] 已更新')
                success += 1
            else:
                print(f'  [SKIP] 无更新')
        else:
            print(f'  [FAIL] 未获取数据')
        
        time.sleep(0.3)  # 避免请求过快
    
    print(f'\n完成: 成功 {success}/{len(funds)}')

if __name__ == '__main__':
    crawl_all()
