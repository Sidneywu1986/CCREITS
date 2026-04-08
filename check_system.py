#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REITs数据平台 - 系统检查脚本
"""

import sqlite3
import requests
import sys

DB_PATH = 'backend/database/reits.db'
BASE_URL = 'http://localhost:3001'

def check_database():
    """检查数据库状态"""
    print("=" * 60)
    print("数据库检查")
    print("=" * 60)
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 基金数量
        cursor.execute('SELECT COUNT(*) FROM funds')
        fund_count = cursor.fetchone()[0]
        print(f"OK 基金总数: {fund_count}")
        
        # 实时行情数量
        cursor.execute('SELECT COUNT(DISTINCT fund_code) FROM quotes')
        quote_count = cursor.fetchone()[0]
        print(f"OK 实时行情覆盖: {quote_count} 只基金")
        
        # 最新行情时间
        cursor.execute('SELECT MAX(updated_at) FROM quotes')
        last_update = cursor.fetchone()[0]
        print(f"OK 最新行情时间: {last_update}")
        
        # 历史数据数量
        cursor.execute('SELECT COUNT(*) FROM price_history')
        history_count = cursor.fetchone()[0]
        print(f"OK 历史数据记录: {history_count}")
        
        # 公告数量
        cursor.execute('SELECT COUNT(*) FROM announcements')
        announcement_count = cursor.fetchone()[0]
        print(f"OK 公告数量: {announcement_count}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"ERR 数据库检查失败: {e}")
        return False

def check_api():
    """检查API服务"""
    print("\n" + "=" * 60)
    print("API服务检查")
    print("=" * 60)
    
    try:
        # 健康检查
        resp = requests.get(f'{BASE_URL}/api/health', timeout=5)
        if resp.status_code == 200:
            print(f"OK 健康检查")
        else:
            print(f"ERR 健康检查: 失败 ({resp.status_code})")
            return False
        
        # 基金列表
        resp = requests.get(f'{BASE_URL}/api/funds', timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            print(f"OK 基金列表API: {data.get('count', 0)} 只基金")
        else:
            print(f"ERR 基金列表API: 失败")
            return False
        
        # 单只基金
        resp = requests.get(f'{BASE_URL}/api/funds/508000', timeout=10)
        if resp.status_code == 200:
            print(f"OK 基金详情API")
        else:
            print(f"ERR 基金详情API: 失败")
            return False
        
        # 系统状态
        resp = requests.get(f'{BASE_URL}/api/system/status', timeout=10)
        if resp.status_code == 200:
            print(f"OK 系统状态API")
        else:
            print(f"ERR 系统状态API: 失败")
            return False
        
        return True
        
    except requests.exceptions.ConnectionError:
        print(f"ERR API服务未启动: 请运行 `node backend/server.js`")
        return False
    except Exception as e:
        print(f"ERR API检查失败: {e}")
        return False

def main():
    print("REITs数据平台 - 系统检查")
    
    db_ok = check_database()
    api_ok = check_api()
    
    print("\n" + "=" * 60)
    if db_ok and api_ok:
        print("OK 系统检查通过！可以开盘交易。")
        print("=" * 60)
        return 0
    else:
        print("ERR 系统检查未通过，请查看上述错误信息。")
        print("=" * 60)
        return 1

if __name__ == '__main__':
    sys.exit(main())
