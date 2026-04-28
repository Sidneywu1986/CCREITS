#!/usr/bin/env python3
"""
批量填充 REITs 历史价格数据
来源：新浪财经 (AKShare fund_etf_hist_sina)
"""
import sys
import time
from datetime import datetime
sys.path.insert(0, '/Users/apple/Projects/CCREITS/backend')

import akshare as ak
from core.db import get_conn


def get_prefix(code: str) -> str:
    """上交所 sh，深交所 sz"""
    return 'sh' if code.startswith('5') else 'sz'


def fetch_history(code: str) -> list:
    """获取单只基金历史日线"""
    prefix = get_prefix(code)
    symbol = f"{prefix}{code}"
    try:
        df = ak.fund_etf_hist_sina(symbol=symbol)
        if df is None or len(df) == 0:
            return []
        # 只取 2025-01-01 之后的数据
        cutoff = datetime(2025, 1, 1).date()
        df = df[df['date'] >= cutoff].copy()
        records = []
        for _, row in df.iterrows():
            records.append({
                'fund_code': code,
                'trade_date': row['date'],
                'open_price': row['open'],
                'close_price': row['close'],
                'high_price': row['high'],
                'low_price': row['low'],
                'volume': int(row['volume']) if row['volume'] else 0,
                'amount': row['amount'],
            })
        return records
    except Exception as e:
        print(f"  ❌ {code} 获取失败: {e}")
        return []


def main():
    # 获取所有基金代码
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT fund_code FROM business.funds ORDER BY fund_code")
        codes = [row['fund_code'] for row in cur.fetchall()]

    print(f"=== 开始填充历史价格 === 共 {len(codes)} 只基金")

    total_records = 0
    success_count = 0

    for i, code in enumerate(codes):
        print(f"[{i+1}/{len(codes)}] {code} ...", end=' ', flush=True)
        records = fetch_history(code)
        if not records:
            print("无数据", flush=True)
            continue

        with get_conn() as conn:
            cur = conn.cursor()
            inserted = 0
            for r in records:
                cur.execute("""
                    INSERT INTO business.price_history
                    (fund_code, trade_date, open_price, close_price, high_price, low_price, volume, amount)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (fund_code, trade_date) DO NOTHING
                """, (r['fund_code'], r['trade_date'], r['open_price'], r['close_price'],
                      r['high_price'], r['low_price'], r['volume'], r['amount']))
                if cur.rowcount > 0:
                    inserted += 1
            conn.commit()

        total_records += inserted
        success_count += 1
        print(f"插入 {inserted} 条", flush=True)
        time.sleep(0.5)  # 避免请求过快

    print(f"\n=== 完成 === 成功: {success_count}/{len(codes)}, 新增: {total_records} 条")


if __name__ == '__main__':
    main()
