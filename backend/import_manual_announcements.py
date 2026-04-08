# -*- coding: utf-8 -*-
"""
手动导入公告模板
用于人工维护重要公告（分红、扩募、重大事件）
"""

import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = 'database/reits.db'

# 示例：手动维护的重要公告
MANUAL_ANNOUNCEMENTS = [
    # 分红公告示例
    {
        'fund_code': '508056',
        'exchange': 'SSE',
        'title': '中金普洛斯REIT 2025年第1次收益分配公告',
        'category': 'dividend',
        'publish_date': '2025-04-08',
        'source_url': 'https://www.sse.com.cn/...pdf',
        'dividend_per_share': 0.0852,  # 每份分红金额
        'record_date': '2025-04-15',    # 权益登记日
        'ex_dividend_date': '2025-04-16',  # 除息日
    },
    # 可以继续添加...
]

def import_manual_data():
    """导入人工维护的公告"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    imported = 0
    for item in MANUAL_ANNOUNCEMENTS:
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO announcements 
                (fund_code, title, category, publish_date, source_url, exchange, created_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                item['fund_code'],
                item['title'],
                item['category'],
                item['publish_date'],
                item.get('source_url', ''),
                item['exchange']
            ))
            imported += 1
        except Exception as e:
            print(f"导入失败: {e}")
    
    conn.commit()
    conn.close()
    print(f"成功导入 {imported} 条公告")

if __name__ == '__main__':
    import_manual_data()
