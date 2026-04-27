#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时行情服务 - 新浪财经API
获取REITs基金实时价格数据
"""

import requests
import json
import re
import datetime
import os
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.db import get_conn

# 板块映射表路径
SECTOR_MAPPING_PATH = os.path.join(os.path.dirname(__file__), '..', 'sector_mapping.json')

def _load_sector_mapping() -> Dict[str, str]:
    """加载板块映射表"""
    try:
        path = os.path.normpath(SECTOR_MAPPING_PATH)
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载板块映射失败: {e}")
        return {}

# 延迟加载板块映射
SECTOR_MAPPING = None

# 市值计算份额（亿份）
SHARES_CACHE = None
SCALE_MAPPING_PATH = os.path.join(os.path.dirname(__file__), '..', 'scale_mapping.json')

def _load_shares_mapping() -> Dict[str, float]:
    """从数据库和scale_mapping.json加载份额数据"""
    shares = {}
    # 首先从数据库加载
    try:
        with get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT fund_code, total_shares FROM business.funds')
            for row in cursor.fetchall():
                if row[1]:
                    shares[row[0]] = row[1]
    except Exception as e:
        print(f"加载数据库份额失败: {e}")
    # 用scale_mapping.json补充缺失数据
    try:
        path = os.path.normpath(SCALE_MAPPING_PATH)
        with open(path, 'r', encoding='utf-8') as f:
            scale_data = json.load(f)
            for code, scale in scale_data.items():
                if code not in shares and scale:
                    shares[code] = scale
    except Exception as e:
        print(f"加载scale_mapping失败: {e}")
    return shares

def get_sector(fund_code: str) -> str:
    """根据基金代码获取板块"""
    global SECTOR_MAPPING
    if SECTOR_MAPPING is None:
        SECTOR_MAPPING = _load_sector_mapping()
    return SECTOR_MAPPING.get(fund_code, 'other')

def get_shares(fund_code: str) -> float:
    """根据基金代码获取份额"""
    global SHARES_CACHE
    if SHARES_CACHE is None:
        SHARES_CACHE = _load_shares_mapping()
    return SHARES_CACHE.get(fund_code, 0)

# K线数据缓存：{fund_code: (timestamp, data)}
KLINE_CACHE = {}
KLINE_CACHE_TTL = 300  # 5分钟缓存

def calculate_period_change(fund_code: str, current_price: float) -> tuple:
    """计算5日和20日涨跌幅（使用新浪财经K线数据，带缓存）"""
    global KLINE_CACHE

    # 检查缓存
    now = datetime.datetime.now().timestamp()
    if fund_code in KLINE_CACHE:
        cached_time, klines = KLINE_CACHE[fund_code]
        if now - cached_time < KLINE_CACHE_TTL:
            # 使用缓存数据
            return _calc_change_from_klines(klines, current_price)

    try:
        # 构建新浪代码
        mkt = 'sh' if fund_code.startswith('5') else 'sz'
        url = 'http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData'
        params = {
            'symbol': f'{mkt}{fund_code}',
            'scale': '240',
            'ma': 'no',
            'datalen': '30'
        }
        headers = {'Referer': 'http://finance.sina.com.cn'}
        r = requests.get(url, params=params, headers=headers, timeout=10)
        klines = r.json()

        if not isinstance(klines, list) or len(klines) < 2:
            return (None, None)

        # 更新缓存
        KLINE_CACHE[fund_code] = (now, klines)

        return _calc_change_from_klines(klines, current_price)
    except Exception as e:
        print(f"计算周期涨跌幅失败 {fund_code}: {e}")
        return (None, None)


def _calc_change_from_klines(klines: list, current_price: float) -> tuple:
    """从K线数据计算涨跌幅"""
    if not isinstance(klines, list) or len(klines) < 2:
        return (None, None)

    recent = klines[-20:] if len(klines) >= 20 else klines

    change_5d = None
    if len(recent) >= 5:
        price_5d_ago = float(recent[-5]['close'])
        if price_5d_ago > 0:
            change_5d = round((current_price - price_5d_ago) / price_5d_ago * 100, 2)

    change_20d = None
    if len(recent) >= 20:
        price_20d_ago = float(recent[-20]['close'])
        if price_20d_ago > 0:
            change_20d = round((current_price - price_20d_ago) / price_20d_ago * 100, 2)

    return (change_5d, change_20d)

# REITs基金代码集合
REITS_CODES = {
    # 上交所 - sh
    '508000', '508001', '508002', '508003', '508005', '508006', '508007', '508008',
    '508009', '508010', '508011', '508012', '508015', '508016', '508017', '508018',
    '508019', '508020', '508021', '508022', '508026', '508027', '508028', '508029',
    '508031', '508032', '508033', '508035', '508036', '508037', '508038', '508039',
    '508048', '508050', '508055', '508056', '508058', '508060', '508066', '508068',
    '508069', '508077', '508078', '508080', '508082', '508084', '508085', '508086',
    '508087', '508088', '508089', '508090', '508091', '508092', '508096', '508097',
    '508098', '508099',
    # 深交所 - sz
    '180101', '180102', '180103', '180105', '180106', '180201', '180202', '180203',
    '180301', '180302', '180303', '180305', '180306', '180401', '180402', '180501',
    '180502', '180503', '180601', '180602', '180603', '180605', '180606', '180607',
    '180701', '180801', '180901'
}

# 上交所代码（以5开头）
SSE_CODES = [code for code in REITS_CODES if code.startswith('5')]
# 深交所代码（以1或18开头）
SZSE_CODES = [code for code in REITS_CODES if not code.startswith('5')]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'http://finance.sina.com.cn'
}


def get_sina_code(fund_code: str) -> str:
    """转换基金代码为新浪格式"""
    if fund_code.startswith('5'):
        return f"sh{fund_code}"  # 上交所
    else:
        return f"sz{fund_code}"  # 深交所


def parse_sina_data(code: str, data: str) -> Optional[Dict]:
    """
    解析新浪财经返回的数据
    格式: var hq_str_xxx="名称,今开,昨收,当前价,最高,最低,...",...;
    """
    try:
        # 提取数据部分
        match = re.search(r'"([^"]+)"', data)
        if not match:
            return None

        fields = match.group(1).split(',')
        if len(fields) < 32:
            return None

        name = fields[0]
        open_price = float(fields[1]) if fields[1] else 0
        prev_close = float(fields[2]) if fields[2] else 0
        current_price = float(fields[3]) if fields[3] else 0
        high_price = float(fields[4]) if fields[4] else 0
        low_price = float(fields[5]) if fields[5] else 0
        volume = int(fields[8]) if fields[8] else 0  # 成交量（股）
        amount = float(fields[9]) if fields[9] else 0  # 成交额
        date_str = fields[30] if len(fields) > 30 else ''
        time_str = fields[31] if len(fields) > 31 else ''

        # 盘前/盘后/停牌时 current_price 为 0，回退使用 prev_close 展示
        is_pre_market = (current_price == 0 and prev_close > 0)
        display_price = prev_close if is_pre_market else current_price

        # 计算涨跌（盘前/停牌时设为 0，避免 -100% 误导）
        change = 0.0 if is_pre_market else (current_price - prev_close)
        change_pct = 0.0 if is_pre_market else ((change / prev_close * 100) if prev_close > 0 else 0)

        # 去掉交易所前缀还原代码
        fund_code = code[2:] if code.startswith(('sh', 'sz')) else code

        # 根据代码获取板块
        sector = get_sector(fund_code)

        # 计算市值（亿元）：价格 × 份额（盘前用 prev_close）
        shares = get_shares(fund_code)
        market_cap = round(display_price * shares, 2) if shares > 0 else 0

        return {
            'fund_code': fund_code,
            'name': name,
            'sector': sector,
            'current_price': display_price,
            'open_price': open_price,
            'prev_close': prev_close,
            'high_price': high_price,
            'low_price': low_price,
            'change': round(change, 3),
            'change_pct': round(change_pct, 2),
            'change_5d': None,
            'change_20d': None,
            'volume': volume,
            'amount': round(amount, 2),
            'market_cap': market_cap,
            'date': date_str,
            'time': time_str,
            'timestamp': f"{date_str} {time_str}" if date_str and time_str else ''
        }
    except Exception as e:
        print(f"解析失败 {code}: {e}")
        return None


def fetch_realtime_quote(codes: List[str]) -> List[Dict]:
    """批量获取实时行情"""
    if not codes:
        return []

    # 构建新浪代码列表
    sina_codes = [get_sina_code(code) for code in codes]
    code_str = ','.join(sina_codes)

    try:
        response = requests.get(
            f"http://hq.sinajs.cn/list={code_str}",
            headers=HEADERS,
            timeout=10
        )
        response.encoding = 'gbk'

        results = []
        # 按换行分割每个基金的数据
        lines = response.text.strip().split('\n')
        for i, line in enumerate(lines):
            if i < len(codes):
                code = codes[i]
                data = parse_sina_data(sina_codes[i], line)
                if data:
                    results.append(data)

        # 并行获取K线数据计算5日、20日涨跌幅
        if results:
            _fill_period_changes_parallel(results)

        return results
    except Exception as e:
        print(f"获取实时行情失败: {e}")
        return []


def _fill_period_changes_parallel(results: List[Dict], max_workers: int = 10):
    """并行获取所有基金的K线数据"""
    global KLINE_CACHE

    # 先从缓存填充（用实时价格计算）
    now = datetime.datetime.now().timestamp()
    for r in results:
        code = r['fund_code']
        if code in KLINE_CACHE:
            cached_time, klines = KLINE_CACHE[code]
            if now - cached_time < KLINE_CACHE_TTL:
                # 用实时价格计算
                r['change_5d'], r['change_20d'] = calculate_period_change_from_klines(klines, r['current_price'])
                continue

    # 需要请求的codes
    codes_to_fetch = [r['fund_code'] for r in results
                      if r.get('change_5d') is None and r.get('change_20d') is None]

    if not codes_to_fetch:
        return

    # 并行请求K线数据
    def fetch_one(code):
        klines = calculate_period_change_no_cache(code)
        return code, klines

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_one, code): code for code in codes_to_fetch}
        for future in as_completed(futures):
            try:
                code, klines = future.result(timeout=5)
                if klines is None:
                    continue
                # 找到对应的结果，用实时价格计算
                for r in results:
                    if r['fund_code'] == code:
                        r['change_5d'], r['change_20d'] = calculate_period_change_from_klines(klines, r['current_price'])
                        break
            except Exception as e:
                pass


def calculate_period_change_no_cache(fund_code: str) -> list:
    """获取K线数据（不带缓存）"""
    try:
        mkt = 'sh' if fund_code.startswith('5') else 'sz'
        url = 'http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData'
        params = {
            'symbol': f'{mkt}{fund_code}',
            'scale': '240',
            'ma': 'no',
            'datalen': '30'
        }
        headers = {'Referer': 'http://finance.sina.com.cn'}
        r = requests.get(url, params=params, headers=headers, timeout=10)
        klines = r.json()

        if not isinstance(klines, list) or len(klines) < 2:
            return None

        # 更新缓存
        global KLINE_CACHE
        KLINE_CACHE[fund_code] = (datetime.datetime.now().timestamp(), klines)

        return klines
    except Exception as e:
        print(f"获取K线失败 {fund_code}: {e}")
        return None


def calculate_period_change_from_klines(klines: list, current_price: float) -> tuple:
    """用K线数据和实时价格计算5日、20日涨跌幅"""
    if not isinstance(klines, list) or len(klines) < 2:
        return (None, None)

    recent = klines[-20:] if len(klines) >= 20 else klines

    change_5d = None
    if len(recent) >= 5:
        price_5d_ago = float(recent[-5]['close'])
        if price_5d_ago > 0:
            change_5d = round((current_price - price_5d_ago) / price_5d_ago * 100, 2)

    change_20d = None
    if len(recent) >= 20:
        price_20d_ago = float(recent[-20]['close'])
        if price_20d_ago > 0:
            change_20d = round((current_price - price_20d_ago) / price_20d_ago * 100, 2)

    return (change_5d, change_20d)


def fetch_all_reits_quotes() -> List[Dict]:
    """获取所有REITs基金的实时行情"""
    return fetch_realtime_quote(list(REITS_CODES))


def save_to_database(quotes: List[Dict], db_path: str = None):
    """保存行情数据到数据库"""
    if not quotes:
        return 0

    try:
        with get_conn() as conn:
            cursor = conn.cursor()

            inserted = 0
            for quote in quotes:
                trade_date = quote.get('date', datetime.date.today().strftime('%Y-%m-%d'))
                trade_time = quote.get('time', '')

                cursor.execute('''
                    INSERT INTO business.fund_prices
                    (fund_code, trade_date, open_price, high_price, low_price,
                     close_price, volume, amount, change_pct, update_time)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (fund_code, trade_date) DO UPDATE SET
                        open_price = EXCLUDED.open_price,
                        high_price = EXCLUDED.high_price,
                        low_price = EXCLUDED.low_price,
                        close_price = EXCLUDED.close_price,
                        volume = EXCLUDED.volume,
                        amount = EXCLUDED.amount,
                        change_pct = EXCLUDED.change_pct,
                        update_time = EXCLUDED.update_time
                ''', (
                    quote['fund_code'],
                    trade_date,
                    quote.get('open_price', 0),
                    quote.get('high_price', 0),
                    quote.get('low_price', 0),
                    quote.get('current_price', 0),
                    quote.get('volume', 0),
                    quote.get('amount', 0),
                    quote.get('change_pct', 0),
                    quote.get('timestamp', '')
                ))
                inserted += 1

            conn.commit()
        return inserted
    except Exception as e:
        print(f"保存失败: {e}")
        return 0


if __name__ == '__main__':
    print("=" * 60)
    print("REITs实时行情获取")
    print("=" * 60)

    # 获取所有REITs行情
    quotes = fetch_all_reits_quotes()
    print(f"\n获取到 {len(quotes)} 只基金的行情数据\n")

    # 显示前10只
    print(f"{'代码':<10} {'名称':<15} {'现价':<10} {'涨跌':<10} {'涨跌幅':<10} {'时间'}")
    print("-" * 70)
    for q in quotes[:10]:
        print(f"{q['fund_code']:<10} {q['name'][:12]:<15} {q['current_price']:<10} "
              f"{q['change']:<+10.3f} {q['change_pct']:>+8.2f}% {q['time']}")

    # 保存到数据库
    saved = save_to_database(quotes)
    print(f"\n已保存 {saved} 条行情数据到数据库")
