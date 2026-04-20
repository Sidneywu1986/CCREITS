#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKShare REITs 数据爬虫 V2
从本地数据库读取81只基金，获取AKShare行情数据
"""

import sys
import json
import sqlite3
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# 数据库路径
DB_PATH = Path(__file__).parent.parent / 'database' / 'reits.db'

def get_db_funds():
    """从数据库获取81只基金列表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT fund_code, fund_name FROM funds ORDER BY fund_code')
    funds = [{'code': row[0], 'name': row[1]} for row in cursor.fetchall()]
    conn.close()
    return funds

def init_akshare():
    """初始化 AKShare"""
    try:
        import akshare as ak
        return ak
    except ImportError:
        print(json.dumps({
            "success": False,
            "error": "AKShare 未安装，请运行: pip install akshare pandas"
        }, ensure_ascii=False))
        sys.exit(1)

def get_fund_spot(code):
    """获取单只基金实时行情"""
    ak = init_akshare()
    
    try:
        # 获取场内基金实时行情
        df = ak.fund_etf_spot_em()
        
        # 查找指定代码
        fund_df = df[df['代码'].astype(str) == code]
        
        if fund_df.empty:
            return None
            
        row = fund_df.iloc[0]
        return {
            "code": str(code),
            "name": row['名称'],
            "price": float(row['最新价']) if pd.notna(row['最新价']) else 0,
            "change_percent": float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else 0,
            "change_amount": float(row['涨跌额']) if pd.notna(row['涨跌额']) else 0,
            "volume": int(row['成交量']) if pd.notna(row['成交量']) else 0,
            "amount": float(row['成交额']) if pd.notna(row['成交额']) else 0,
            "open": float(row['开盘价']) if pd.notna(row['开盘价']) else 0,
            "high": float(row['最高价']) if pd.notna(row['最高价']) else 0,
            "low": float(row['最低价']) if pd.notna(row['最低价']) else 0,
            "pre_close": float(row['昨收']) if pd.notna(row['昨收']) else 0,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"获取 {code} 行情失败: {e}", file=sys.stderr)
        return None

def get_fund_history(code, start_date=None, end_date=None):
    """获取单只基金历史数据"""
    ak = init_akshare()
    
    try:
        # 默认获取最近1年
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        
        # 使用AKShare获取历史数据
        df = ak.fund_etf_hist_em(
            symbol=code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"
        )
        
        result = []
        for _, row in df.iterrows():
            result.append({
                "date": row['日期'],
                "open": float(row['开盘']),
                "close": float(row['收盘']),
                "high": float(row['最高']),
                "low": float(row['最低']),
                "volume": int(row['成交量']),
                "amount": float(row['成交额']),
                "change_percent": float(row['涨跌幅']) if '涨跌幅' in row else 0,
            })
        
        return result
    except Exception as e:
        print(f"获取 {code} 历史数据失败: {e}", file=sys.stderr)
        return []

def crawl_all_spot():
    """爬取所有81只基金实时行情"""
    print(f"[{datetime.now()}] 开始爬取81只基金实时行情...", file=sys.stderr)
    
    funds = get_db_funds()
    results = []
    success_count = 0
    
    for fund in funds:
        spot = get_fund_spot(fund['code'])
        if spot:
            results.append(spot)
            success_count += 1
            print(f"  ✓ {fund['code']} {fund['name']}", file=sys.stderr)
        else:
            print(f"  ✗ {fund['code']} {fund['name']} - 获取失败", file=sys.stderr)
    
    output = {
        "success": True,
        "count": len(results),
        "success_count": success_count,
        "total": len(funds),
        "data": results,
        "timestamp": datetime.now().isoformat()
    }
    
    print(json.dumps(output, ensure_ascii=False, default=str))
    return output

def crawl_all_history(days=365):
    """爬取所有81只基金历史数据"""
    print(f"[{datetime.now()}] 开始爬取81只基金历史数据（{days}天）...", file=sys.stderr)
    
    funds = get_db_funds()
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
    
    all_data = {}
    total_records = 0
    
    for fund in funds:
        history = get_fund_history(fund['code'], start_date, end_date)
        if history:
            all_data[fund['code']] = {
                "name": fund['name'],
                "history": history
            }
            total_records += len(history)
            print(f"  ✓ {fund['code']} {fund['name']}: {len(history)}条", file=sys.stderr)
        else:
            print(f"  ✗ {fund['code']} {fund['name']} - 无数据", file=sys.stderr)
    
    output = {
        "success": True,
        "count": len(all_data),
        "total_records": total_records,
        "data": all_data,
        "timestamp": datetime.now().isoformat()
    }
    
    print(json.dumps(output, ensure_ascii=False, default=str))
    return output

def main():
    parser = argparse.ArgumentParser(description='AKShare REITs数据爬虫V2')
    parser.add_argument('command', choices=['list', 'spot', 'history'], help='命令')
    parser.add_argument('--code', '-c', help='基金代码（单个查询）')
    parser.add_argument('--days', '-d', type=int, default=365, help='历史数据天数')
    
    args = parser.parse_args()
    
    global pd
    import pandas as pd
    
    if args.command == 'list':
        # 从数据库获取列表
        funds = get_db_funds()
        print(json.dumps({
            "success": True,
            "count": len(funds),
            "data": funds,
            "source": "database"
        }, ensure_ascii=False))
        
    elif args.command == 'spot':
        if args.code:
            # 单只查询
            spot = get_fund_spot(args.code)
            print(json.dumps({
                "success": spot is not None,
                "data": spot
            }, ensure_ascii=False, default=str))
        else:
            # 全部查询
            crawl_all_spot()
            
    elif args.command == 'history':
        if args.code:
            # 单只查询
            history = get_fund_history(args.code, days=args.days)
            print(json.dumps({
                "success": len(history) > 0,
                "code": args.code,
                "count": len(history),
                "data": history
            }, ensure_ascii=False, default=str))
        else:
            # 全部查询
            crawl_all_history(args.days)

if __name__ == '__main__':
    main()
