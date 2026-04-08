#!/usr/bin/env python3
"""
AKShare API 服务 - REITs专用
为 Node.js 后端提供 REITs 数据接口
"""

import akshare as ak
from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
from datetime import datetime

app = Flask(__name__)
CORS(app)

# 全局缓存
_cache = {
    'spot': None,
    'spot_time': None
}

def get_spot_data():
    """获取实时行情（带缓存）"""
    now = datetime.now()
    # 缓存5秒
    if _cache['spot'] is not None and _cache['spot_time'] is not None:
        if (now - _cache['spot_time']).seconds < 5:
            return _cache['spot']
    
    try:
        df = ak.fund_etf_spot_em()
        # 筛选REITs（代码以508或180开头，或名称包含REIT）
        reits_mask = (
            df['代码'].astype(str).str.match(r'^(508|180)') |
            df['名称'].str.contains('REIT', na=False)
        )
        df = df[reits_mask]
        
        _cache['spot'] = df
        _cache['spot_time'] = now
        return df
    except Exception as e:
        print(f"[AKShare] 获取数据失败: {e}")
        return _cache['spot']  # 返回旧缓存

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'akshare-reits'})

@app.route('/reit_realtime')
def reit_realtime():
    """REITs 实时行情 - 单只或全部"""
    symbol = request.args.get('symbol')
    
    try:
        df = get_spot_data()
        if df is None or len(df) == 0:
            return jsonify({'error': 'No data available'}), 500
        
        if symbol:
            row = df[df['代码'] == symbol]
            if len(row) == 0:
                return jsonify({'error': 'Fund not found'}), 404
            
            data = row.iloc[0]
            # 标准化输出
            result = {
                'fund_code': str(data['代码']),
                'name': str(data['名称']),
                'price': float(data.get('最新价', 0)),
                'change_percent': float(data.get('涨跌幅', 0)),
                'change_amount': float(data.get('涨跌额', 0)),
                'volume': int(data.get('成交量', 0)),
                'amount': float(data.get('成交额', 0)),
                'open': float(data.get('开盘价', 0)),
                'high': float(data.get('最高价', 0)),
                'low': float(data.get('最低价', 0)),
                'pre_close': float(data.get('昨收', 0)),
                # REITs特有（如果有的话）
                'nav': None,
                'premium': None,
                'yield': None,
            }
            return jsonify(result)
        
        # 返回全部
        return jsonify(df.to_dict('records'))
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/reit_hist')
def reit_hist():
    """REITs 历史K线数据"""
    symbol = request.args.get('symbol')
    period = request.args.get('period', 'daily')  # daily/weekly/monthly
    
    if not symbol:
        return jsonify({'error': 'Missing symbol'}), 400
    
    try:
        # 转换period
        period_map = {'daily': 'daily', 'weekly': 'weekly', 'monthly': 'monthly'}
        ak_period = period_map.get(period, 'daily')
        
        df = ak.fund_etf_hist_em(
            symbol=symbol,
            period=ak_period,
            adjust="qfq"
        )
        
        if df is None or len(df) == 0:
            return jsonify([])
        
        # 转换列名
        df = df.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume',
            '成交额': 'amount',
            '振幅': 'amplitude',
            '涨跌幅': 'change_percent',
            '涨跌额': 'change_amount',
            '换手率': 'turnover'
        })
        
        return jsonify(df.to_dict('records'))
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/reit_dividend')
def reit_dividend():
    """REITs 分红数据"""
    symbol = request.args.get('symbol')
    
    if not symbol:
        return jsonify({'error': 'Missing symbol'}), 400
    
    try:
        df = ak.fund_etf_dividend_sina(symbol=symbol)
        return jsonify(df.to_dict('records'))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/reit_list')
def reit_list():
    """REITs 列表"""
    try:
        df = get_spot_data()
        if df is None:
            return jsonify([])
        
        # 简化字段
        result = df[['代码', '名称', '最新价', '涨跌幅']].to_dict('records')
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("AKShare REITs API 服务启动")
    print("=" * 60)
    print("接口列表:")
    print("  GET /health           - 健康检查")
    print("  GET /reit_realtime    - REITs 实时行情 (?symbol=508056)")
    print("  GET /reit_hist        - REITs 历史K线 (?symbol=508056&period=daily)")
    print("  GET /reit_dividend    - REITs 分红数据 (?symbol=508056)")
    print("  GET /reit_list        - REITs 列表")
    print("=" * 60)
    print("服务地址: http://127.0.0.1:5000")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
