#!/usr/bin/env python3
"""
AKShare REITs 数据获取脚本
直接获取实时行情并保存到SQLite数据库
"""

import akshare as ak
import sqlite3
import sys
import os
from datetime import datetime

def get_db_connection():
    """获取数据库连接"""
    db_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'reits.db')
    return sqlite3.connect(db_path)

def fetch_and_save_reits_data():
    """获取REITs实时数据并保存到数据库"""
    print("[AKShare] 开始获取REITs实时数据...")
    
    try:
        # 获取实时行情
        df = ak.reits_realtime_em()
        print(f"[AKShare] 成功获取 {len(df)} 只REITs数据")
        
        # 连接数据库
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 更新每只基金的数据
        updated = 0
        for _, row in df.iterrows():
            code = str(row['代码'])
            
            # 计算流通份额 = 流通市值 / 最新价
            price = float(row['最新价']) if pd.notna(row['最新价']) else 0
            float_cap = float(row['流通市值']) if pd.notna(row['流通市值']) else 0
            
            circulating_shares = None
            if price > 0 and float_cap > 0:
                # 流通市值(亿) / 价格 = 份额(亿股) = 份额(万份) * 10000
                circulating_shares = (float_cap / price) * 10000
            
            cursor.execute("""
                UPDATE funds 
                SET nav = ?,
                    circulating_shares = ?,
                    updated_at = datetime('now')
                WHERE code = ?
            """, (
                price if price > 0 else None,
                circulating_shares,
                code
            ))
            
            if cursor.rowcount > 0:
                updated += 1
                print(f"[AKShare] ✓ {code} 价格:{price} 份额:{circulating_shares:.2f}万份" if circulating_shares else f"[AKShare] ✓ {code} 价格:{price}")
        
        conn.commit()
        conn.close()
        
        print(f"[AKShare] 完成! 更新了 {updated} 只基金")
        return updated
        
    except Exception as e:
        print(f"[AKShare] 错误: {e}")
        import traceback
        traceback.print_exc()
        return 0

if __name__ == '__main__':
    import pandas as pd  # 在这里导入避免全局导入问题
    count = fetch_and_save_reits_data()
    sys.exit(0 if count > 0 else 1)
