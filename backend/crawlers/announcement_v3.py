# -*- coding: utf-8 -*-
"""
REITs公告爬虫 v3 - 沪深交易所双通道
核心任务：T+2时效监控，分红公告必须在权益登记日前2个交易日入库
"""

import requests
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import time
import re
import sys
import os

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'reits.db')

class SSEAnnouncementCrawler:
    """上交所公告爬虫 (508XXX)"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://www.sse.com.cn/assortment/fund/reits/home/',
        })
        self.base_url = "http://query.sse.com.cn/commonQuery.do"
    
    def fetch(self, fund_code, days=30):
        """获取上交所REITs公告"""
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
        end_date = datetime.now().strftime('%Y%m%d')
        
        params = {
            'sqlId': 'COMMON_SSE_SCSJ_CJGK_ZQSL',
            'productId': fund_code,
            'startDate': start_date,
            'endDate': end_date,
            'pageHelp.pageSize': 25,
            'pageHelp.pageNo': 1,
        }
        
        try:
            resp = self.session.get(self.base_url, params=params, timeout=15)
            data = resp.json()
            
            items = []
            if data.get('result'):
                for item in data['result']:
                    title = item.get('bulletin_TITLE', '')
                    # 分类：分红公告关键词
                    category = 'dividend' if any(kw in title for kw in ['收益分配', '分红', '权益分派']) else 'other'
                    
                    items.append({
                        'fund_code': fund_code,
                        'exchange': 'SSE',
                        'announcement_id': item.get('bulletin_ID'),
                        'title': title,
                        'category': category,
                        'publish_date': item.get('bulletin_YMD'),
                        'url': f"http://www.sse.com.cn{item.get('bulletin_URL', '')}" if item.get('bulletin_URL') else None,
                    })
            return items
        except Exception as e:
            print(f"[ERROR] SSE {fund_code}: {e}")
            return []


class SZSEAnnouncementCrawler:
    """深交所公告爬虫 (180XXX)"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://www.szse.cn/market/fund/reits/bulletin/',
        })
        self.base_url = "http://www.szse.cn/api/disc/announcement/list"
    
    def fetch(self, fund_code, days=30):
        """获取深交所REITs公告"""
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        params = {
            'channelCode': 'fund',
            'pageSize': 30,
            'pageNum': 1,
            'keywords': fund_code,
            'startTime': start_date,
            'endTime': end_date,
        }
        
        try:
            resp = self.session.get(self.base_url, params=params, timeout=15)
            data = resp.json()
            
            items = []
            if data.get('data'):
                for item in data['data']:
                    title = item.get('title', '')
                    category = 'dividend' if any(kw in title for kw in ['收益分配', '分红', '权益分派']) else 'other'
                    
                    items.append({
                        'fund_code': fund_code,
                        'exchange': 'SZSE',
                        'announcement_id': item.get('id'),
                        'title': title,
                        'category': category,
                        'publish_date': item.get('publishTime', '').split()[0] if item.get('publishTime') else None,
                        'url': item.get('url'),
                    })
            return items
        except Exception as e:
            print(f"[ERROR] SZSE {fund_code}: {e}")
            return []


def save_to_db(items):
    """保存公告到数据库"""
    if not items:
        return 0
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    saved = 0
    for item in items:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO announcements 
                (fund_code, title, category, publish_date, source_url, exchange, created_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                item['fund_code'],
                item['title'],
                item['category'],
                item['publish_date'],
                item['url'],
                item['exchange']
            ))
            if cursor.rowcount > 0:
                saved += 1
        except Exception as e:
            print(f"[ERROR] DB: {e}")
    
    conn.commit()
    conn.close()
    return saved


def crawl_all_reits():
    """爬取全部79只REITs公告"""
    # 获取基金列表
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT code FROM funds WHERE status = 'listed' OR status IS NULL")
    fund_codes = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    sse_crawler = SSEAnnouncementCrawler()
    szse_crawler = SZSEAnnouncementCrawler()
    
    total_new = 0
    print(f"[INFO] 开始爬取 {len(fund_codes)} 只REITs公告...")
    
    for code in fund_codes:
        print(f"[{code}] ", end='', flush=True)
        
        if code.startswith('508'):
            items = sse_crawler.fetch(code)
        elif code.startswith('180'):
            items = szse_crawler.fetch(code)
        else:
            print("SKIP")
            continue
        
        saved = save_to_db(items)
        total_new += saved
        print(f"{len(items)}条/{saved}新")
        
        time.sleep(0.5)  # 礼貌延迟
    
    print(f"\n[INFO] 完成! 新增 {total_new} 条公告")
    return total_new


if __name__ == '__main__':
    crawl_all_reits()
