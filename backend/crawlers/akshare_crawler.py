#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKShare REITs 数据爬虫
支持历史日线和实时交易数据
"""

import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

def init_akshare():
    """初始化 AKShare，如果未安装则提示安装"""
    try:
        import akshare as ak
        return ak
    except ImportError:
        print(json.dumps({
            "success": False,
            "error": "AKShare 未安装，请运行: pip install akshare"
        }, ensure_ascii=False))
        sys.exit(1)

def get_reits_list():
    """获取 REITs 基金列表"""
    ak = init_akshare()
    
    try:
        # 获取场内基金列表，筛选 REITs
        df = ak.fund_etf_spot_em()
        # 筛选 REITs（通常代码以 15、16、18、50、50 开头）
        reits_codes = ['15', '16', '18', '50', '50', '508', '509', '180']
        reits_df = df[df['代码'].astype(str).str.startswith(tuple(reits_codes))]
        
        # 进一步筛选名称包含 REIT 的
        reits_df = reits_df[reits_df['名称'].str.contains('REIT|reit', na=False, case=False)]
        
        result = []
        for _, row in reits_df.iterrows():
            result.append({
                "code": str(row['代码']),
                "name": row['名称'],
                "exchange": "SH" if str(row['代码']).startswith(('5', '50')) else "SZ",
                "price": float(row['最新价']) if pd.notna(row['最新价']) else 0,
                "change_percent": float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else 0,
                "volume": int(row['成交量']) if pd.notna(row['成交量']) else 0,
                "amount": float(row['成交额']) if pd.notna(row['成交额']) else 0,
                "open": float(row['开盘价']) if pd.notna(row['开盘价']) else 0,
                "high": float(row['最高价']) if pd.notna(row['最高价']) else 0,
                "low": float(row['最低价']) if pd.notna(row['最低价']) else 0,
                "pre_close": float(row['昨收']) if pd.notna(row['昨收']) else 0,
            })
        
        return {
            "success": True,
            "count": len(result),
            "data": result,
            "source": "akshare",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "source": "akshare"
        }

def get_reits_history(code, start_date=None, end_date=None):
    """获取单只 REITs 历史日线数据"""
    ak = init_akshare()
    
    try:
        # 默认获取最近 1 年数据
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        
        # 使用基金历史行情接口
        df = ak.fund_etf_hist_em(
            symbol=code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"  # 前复权
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
                "amplitude": float(row['振幅']) if '振幅' in row else 0,
                "change_percent": float(row['涨跌幅']) if '涨跌幅' in row else 0,
                "change_amount": float(row['涨跌额']) if '涨跌额' in row else 0,
                "turnover": float(row['换手率']) if '换手率' in row else 0,
            })
        
        return {
            "success": True,
            "code": code,
            "count": len(result),
            "data": result,
            "source": "akshare",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "code": code,
            "error": str(e),
            "source": "akshare"
        }

def get_reits_spot():
    """获取 REITs 实时行情（所有）"""
    ak = init_akshare()
    
    try:
        # 获取所有场内基金实时行情
        df = ak.fund_etf_spot_em()
        
        # 筛选 REITs
        reits_df = df[df['名称'].str.contains('REIT|reit', na=False, case=False)]
        
        result = []
        for _, row in reits_df.iterrows():
            result.append({
                "code": str(row['代码']),
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
                "bid_price": float(row['买一']) if pd.notna(row['买一']) else 0,
                "ask_price": float(row['卖一']) if pd.notna(row['卖一']) else 0,
                "bid_volume": int(row['买一量']) if pd.notna(row['买一量']) else 0,
                "ask_volume": int(row['卖一量']) if pd.notna(row['卖一量']) else 0,
            })
        
        return {
            "success": True,
            "count": len(result),
            "data": result,
            "source": "akshare",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "source": "akshare"
        }

def get_all_reits_history(start_date=None, end_date=None):
    """获取所有 REITs 历史数据"""
    ak = init_akshare()
    
    try:
        # 先获取 REITs 列表
        list_result = get_reits_list()
        if not list_result['success']:
            return list_result
        
        all_data = {}
        for fund in list_result['data']:
            code = fund['code']
            print(f"正在获取 {code} {fund['name']} 的历史数据...", file=sys.stderr)
            
            history = get_reits_history(code, start_date, end_date)
            if history['success']:
                all_data[code] = {
                    "name": fund['name'],
                    "history": history['data']
                }
        
        return {
            "success": True,
            "count": len(all_data),
            "data": all_data,
            "source": "akshare",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "source": "akshare"
        }

def main():
    parser = argparse.ArgumentParser(description='AKShare REITs 数据爬虫')
    parser.add_argument('command', choices=[
        'list', 'spot', 'history', 'all-history'
    ], help='要执行的命令')
    parser.add_argument('--code', '-c', help='基金代码')
    parser.add_argument('--start', '-s', help='开始日期 (YYYYMMDD)')
    parser.add_argument('--end', '-e', help='结束日期 (YYYYMMDD)')
    
    args = parser.parse_args()
    
    # 导入 pandas
    global pd
    import pandas as pd
    
    if args.command == 'list':
        result = get_reits_list()
    elif args.command == 'spot':
        result = get_reits_spot()
    elif args.command == 'history':
        if not args.code:
            print(json.dumps({
                "success": False,
                "error": "请指定 --code 参数"
            }, ensure_ascii=False))
            sys.exit(1)
        result = get_reits_history(args.code, args.start, args.end)
    elif args.command == 'all-history':
        result = get_all_reits_history(args.start, args.end)
    else:
        result = {"success": False, "error": "未知命令"}
    
    print(json.dumps(result, ensure_ascii=False, default=str))

if __name__ == '__main__':
    main()
