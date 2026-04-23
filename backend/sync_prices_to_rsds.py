import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = 'database/reits.db'
BATCH_SIZE = 1000

def classify_fund_type(sector):
    """根据 sector 判断产权类/经营权类"""
    concession_sectors = {'transport', 'energy', 'eco', 'water'}
    return '经营权类' if sector in concession_sectors else '产权类'

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. 给 funds 表添加 fund_type 字段（如果不存在）
    cursor.execute("PRAGMA table_info(funds)")
    cols = {c[1] for c in cursor.fetchall()}
    if 'fund_type' not in cols:
        cursor.execute("ALTER TABLE funds ADD COLUMN fund_type VARCHAR(20)")
        print("Added column: funds.fund_type")
    
    # 2. 根据 sector 更新 fund_type
    cursor.execute("SELECT fund_code, sector FROM funds")
    updates = []
    for code, sector in cursor.fetchall():
        ft = classify_fund_type(sector or '')
        updates.append((ft, code))
    
    cursor.executemany("UPDATE funds SET fund_type = ? WHERE fund_code = ?", updates)
    conn.commit()
    print(f"Updated {len(updates)} funds with fund_type")
    
    # 验证分类结果
    cursor.execute("SELECT fund_type, COUNT(*) FROM funds GROUP BY fund_type")
    print("Fund type distribution:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    # 3. 获取基金信息缓存（fund_type, market_cap, remaining_years, total_shares）
    cursor.execute("""
        SELECT fund_code, fund_type, market_cap, remaining_years, total_shares, nav
        FROM funds
    """)
    fund_info = {}
    for row in cursor.fetchall():
        fund_info[row[0]] = {
            'fund_type': row[1],
            'market_cap': row[2] or 0,
            'remaining_years': row[3] or '',
            'total_shares': row[4] or 0,
            'nav': row[5] or 0
        }
    
    # 4. 清空目标表（如需增量同步请注释掉）
    cursor.execute("DELETE FROM reit_market_performance")
    cursor.execute("DELETE FROM reits_market_anomaly")
    conn.commit()
    print("\nCleared target tables.")
    
    # 5. 读取 fund_prices 数据
    cursor.execute("""
        SELECT fund_code, trade_date, open_price, close_price, high_price, low_price,
               volume, amount, change_pct, premium_rate
        FROM fund_prices
        ORDER BY fund_code, trade_date
    """)
    
    property_rows = []
    concession_rows = []
    
    count = 0
    for row in cursor.fetchall():
        code, trade_date, open_p, close_p, high_p, low_p, vol, amount, change_pct, premium = row
        info = fund_info.get(code, {})
        ft = info.get('fund_type', '产权类')
        
        # 计算换手率（volume / total_shares * 100）
        total_shares = info.get('total_shares', 0)
        turnover_rate = (vol / total_shares * 100) if total_shares and total_shares > 0 else None
        
        # 市值估算（close_price * total_shares）
        market_cap = (close_p * total_shares) if close_p and total_shares and total_shares > 0 else info.get('market_cap', 0)
        
        # 异常波动标记：日涨跌幅绝对值 > 5%
        abnormal = 1 if (change_pct and abs(change_pct) > 5) else 0
        
        if ft == '经营权类':
            concession_rows.append((
                code, trade_date, open_p, close_p, high_p, low_p,
                amount, vol, turnover_rate, market_cap,
                info.get('nav', 0), premium,
                info.get('remaining_years', ''),
                None,  # implied_discount_rate 暂无法计算
                abnormal,
                None   # price_deviation_from_sector 暂无法计算
            ))
        else:
            property_rows.append((
                code, trade_date, open_p, close_p, high_p, low_p,
                amount, vol, turnover_rate, market_cap,
                change_pct, premium
            ))
        
        count += 1
        if count % 5000 == 0:
            print(f"  Processed {count} rows...")
    
    print(f"\nTotal price rows: {count}")
    print(f"  Property REITs rows: {len(property_rows)}")
    print(f"  Concession REITs rows: {len(concession_rows)}")
    
    # 6. 批量插入产权类市场表现表
    if property_rows:
        cursor.executemany("""
            INSERT OR IGNORE INTO reit_market_performance (
                fund_code, trade_date, opening_price, closing_price,
                highest_price, lowest_price, turnover, volume,
                turnover_rate, market_cap, daily_return, nav_premium_rate
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, property_rows)
        conn.commit()
        print(f"Inserted {len(property_rows)} rows into reit_market_performance")
    
    # 7. 批量插入经营权类市场表现表
    if concession_rows:
        cursor.executemany("""
            INSERT OR IGNORE INTO reits_market_anomaly (
                project_code, trade_date, opening_price, closing_price,
                highest_price, lowest_price, turnover, volume,
                turnover_rate, market_cap, nav_per_share, premium_rate,
                remaining_years_at_trade, implied_discount_rate,
                abnormal_volatility_flag, price_deviation_from_sector
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, concession_rows)
        conn.commit()
        print(f"Inserted {len(concession_rows)} rows into reits_market_anomaly")
    
    # 8. 验证
    cursor.execute("SELECT COUNT(*) FROM reit_market_performance")
    prop_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM reits_market_anomaly")
    conc_count = cursor.fetchone()[0]
    print(f"\nVerification:")
    print(f"  reit_market_performance: {prop_count} rows")
    print(f"  reits_market_anomaly: {conc_count} rows")
    
    # 样例数据检查
    cursor.execute("""
        SELECT fund_code, trade_date, closing_price, turnover_rate, market_cap, daily_return, nav_premium_rate
        FROM reit_market_performance LIMIT 3
    """)
    print("\nSample property data:")
    for row in cursor.fetchall():
        print(f"  {row}")
    
    cursor.execute("""
        SELECT project_code, trade_date, closing_price, turnover_rate, premium_rate, abnormal_volatility_flag
        FROM reits_market_anomaly LIMIT 3
    """)
    print("\nSample concession data:")
    for row in cursor.fetchall():
        print(f"  {row}")
    
    conn.close()
    print("\nSync completed.")

if __name__ == '__main__':
    main()
