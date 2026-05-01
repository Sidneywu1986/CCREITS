import sys
from core.db import get_conn
import logging
logger = logging.getLogger(__name__)
sys.stdout.reconfigure(encoding='utf-8')

BATCH_SIZE = 1000

def classify_fund_type(sector):
    """根据 sector 判断产权类/经营权类"""
    concession_sectors = {'transport', 'energy', 'eco', 'water'}
    return '经营权类' if sector in concession_sectors else '产权类'

def main():
    with get_conn() as conn:
            cursor = conn.cursor()
            
            # 1. 给 funds 表添加 fund_type 字段（如果不存在）
            cursor.execute("""SELECT column_name FROM information_schema.columns WHERE table_schema = 'business' AND table_name = 'funds'""")
            cols = {c[0] for c in cursor.fetchall()}
            if 'fund_type' not in cols:
                cursor.execute("ALTER TABLE business.funds ADD COLUMN IF NOT EXISTS fund_type VARCHAR(20)")
                logger.info("Added column: funds.fund_type")
            
            # 2. 根据 sector 更新 fund_type
            cursor.execute("SELECT fund_code, sector FROM business.funds")
            updates = []
            for code, sector in cursor.fetchall():
                ft = classify_fund_type(sector or '')
                updates.append((ft, code))
            
            cursor.executemany("UPDATE business.funds SET fund_type = %s WHERE fund_code = %s", updates)
            conn.commit()
            logger.info(f"Updated {len(updates)} funds with fund_type")
            
            # 验证分类结果
            cursor.execute("SELECT fund_type, COUNT(*) FROM business.funds GROUP BY fund_type")
            logger.info("Fund type distribution:")
            for row in cursor.fetchall():
                logger.info(f"  {row[0]}: {row[1]}")
            
            # 3. 获取基金信息缓存（fund_type, market_cap, remaining_years, total_shares）
            cursor.execute("""
                SELECT fund_code, fund_type, market_cap, remaining_years, total_shares, nav
                FROM business.funds
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
            cursor.execute("DELETE FROM business.reit_market_performance")
            cursor.execute("DELETE FROM business.reits_market_anomaly")
            conn.commit()
            logger.info("\nCleared target tables.")
            
            # 5. 读取 fund_prices 数据
            cursor.execute("""
                SELECT fund_code, trade_date, open_price, close_price, high_price, low_price,
                       volume, amount, change_pct, premium_rate
                FROM business.fund_prices
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
                    logger.info(f"  Processed {count} rows...")
            
            logger.info(f"\nTotal price rows: {count}")
            logger.info(f"  Property REITs rows: {len(property_rows)}")
            logger.info(f"  Concession REITs rows: {len(concession_rows)}")
            
            # 6. 批量插入产权类市场表现表
            if property_rows:
                cursor.executemany("""
                    INSERT INTO business.reit_market_performance (
                        fund_code, trade_date, opening_price, closing_price,
                        highest_price, lowest_price, turnover, volume,
                        turnover_rate, market_cap, daily_return, nav_premium_rate
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, property_rows)
                conn.commit()
                logger.info(f"Inserted {len(property_rows)} rows into reit_market_performance")
            
            # 7. 批量插入经营权类市场表现表
            if concession_rows:
                cursor.executemany("""
                    INSERT INTO business.reits_market_anomaly (
                        project_code, trade_date, opening_price, closing_price,
                        highest_price, lowest_price, turnover, volume,
                        turnover_rate, market_cap, nav_per_share, premium_rate,
                        remaining_years_at_trade, implied_discount_rate,
                        abnormal_volatility_flag, price_deviation_from_sector
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, concession_rows)
                conn.commit()
                logger.info(f"Inserted {len(concession_rows)} rows into reits_market_anomaly")
            
            # 8. 验证
            cursor.execute("SELECT COUNT(*) FROM business.reit_market_performance")
            prop_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM business.reits_market_anomaly")
            conc_count = cursor.fetchone()[0]
            logger.info(f"\nVerification:")
            logger.info(f"  reit_market_performance: {prop_count} rows")
            logger.info(f"  reits_market_anomaly: {conc_count} rows")
            
            # 样例数据检查
            cursor.execute("""
                SELECT fund_code, trade_date, closing_price, turnover_rate, market_cap, daily_return, nav_premium_rate
                FROM business.reit_market_performance LIMIT 3
            """)
            logger.info("\nSample property data:")
            for row in cursor.fetchall():
                logger.info(f"  {row}")
            
            cursor.execute("""
                SELECT project_code, trade_date, closing_price, turnover_rate, premium_rate, abnormal_volatility_flag
                FROM business.reits_market_anomaly LIMIT 3
            """)
            logger.info("\nSample concession data:")
            for row in cursor.fetchall():
                logger.info(f"  {row}")
            
    logger.info("\nSync completed.")

if __name__ == '__main__':
    main()
