# -*- coding: utf-8 -*-
"""
REITs公告爬虫 v4 - 从官方HTML页面爬取
上交所：https://www.sse.com.cn/reits/announcements/info
深交所：https://www.szse.cn/sustainablefinance/products/disclosure/reits/index.html
"""

import requests
from bs4 import BeautifulSoup
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import time
import re
import os
import sys

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'reits.db')


class SSEHtmlCrawler:
    """上交所REITs公告HTML爬虫"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
        self.base_url = "https://www.sse.com.cn/reits/announcements/info"
    
    def fetch(self, page=1):
        """从HTML页面爬取公告列表"""
        try:
            url = f"{self.base_url}?page={page}"
            resp = self.session.get(url, timeout=15)
            resp.encoding = 'utf-8'
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            items = []
            # 查找公告列表 - 根据页面结构调整选择器
            # 上交所公告通常在 .table-list 或类似结构中
            rows = soup.select('.table-list tr') or soup.select('table tr')
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    # 提取标题和日期
                    title_elem = cells[0].find('a') or cells[0]
                    title = title_elem.get_text(strip=True)
                    
                    date_elem = cells[-1] if len(cells) > 1 else None
                    date = date_elem.get_text(strip=True) if date_elem else None
                    
                    # 提取链接
                    link = None
                    if title_elem.name == 'a' and title_elem.get('href'):
                        link = title_elem['href']
                        if link.startswith('/'):
                            link = f"https://www.sse.com.cn{link}"
                    
                    # 从标题提取基金代码 (如 508XXX)
                    code_match = re.search(r'(508\d{3})', title)
                    fund_code = code_match.group(1) if code_match else None
                    
                    # 分类
                    category = 'dividend' if any(kw in title for kw in ['收益分配', '分红', '权益分派']) else 'other'
                    
                    if title and date:
                        items.append({
                            'fund_code': fund_code,
                            'exchange': 'SSE',
                            'title': title,
                            'category': category,
                            'publish_date': date,
                            'url': link,
                        })
            
            return items
        except Exception as e:
            print(f"[ERROR] SSE HTML fetch: {e}")
            return []


class SZSEHtmlCrawler:
    """深交所REITs公告HTML爬虫"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
        self.base_url = "https://www.szse.cn/sustainablefinance/products/disclosure/reits/index.html"
    
    def fetch(self):
        """从HTML页面爬取公告列表"""
        try:
            resp = self.session.get(self.base_url, timeout=15)
            resp.encoding = 'utf-8'
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            items = []
            # 深交所公告列表选择器
            rows = soup.select('.table-list tr') or soup.select('.news-list li') or soup.select('table tr')
            
            for row in rows:
                # 尝试提取标题和日期
                title_elem = row.find('a') or row.find(class_=re.compile('title|name'))
                date_elem = row.find(class_=re.compile('date|time'))
                
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    date = date_elem.get_text(strip=True) if date_elem else None
                    
                    # 提取链接
                    link = None
                    if title_elem.name == 'a' and title_elem.get('href'):
                        link = title_elem['href']
                        if link.startswith('/'):
                            link = f"https://www.szse.cn{link}"
                    
                    # 从标题提取基金代码 (如 180XXX)
                    code_match = re.search(r'(180\d{3})', title)
                    fund_code = code_match.group(1) if code_match else None
                    
                    category = 'dividend' if any(kw in title for kw in ['收益分配', '分红', '权益分派']) else 'other'
                    
                    items.append({
                        'fund_code': fund_code,
                        'exchange': 'SZSE',
                        'title': title,
                        'category': category,
                        'publish_date': date,
                        'url': link,
                    })
            
            return items
        except Exception as e:
            print(f"[ERROR] SZSE HTML fetch: {e}")
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
            print(f"[ERROR] DB save: {e}")
    
    conn.commit()
    conn.close()
    return saved


def test_crawlers():
    """测试爬虫"""
    print("="*60)
    print("测试上交所HTML爬虫...")
    print(f"URL: https://www.sse.com.cn/reits/announcements/info")
    
    sse_crawler = SSEHtmlCrawler()
    sse_items = sse_crawler.fetch(page=1)
    print(f"获取到 {len(sse_items)} 条公告")
    for item in sse_items[:5]:
        print(f"  [{item['fund_code'] or 'N/A'}] {item['publish_date']} | {item['title'][:50]}...")
    
    print("\n" + "="*60)
    print("测试深交所HTML爬虫...")
    print(f"URL: https://www.szse.cn/sustainablefinance/products/disclosure/reits/index.html")
    
    szse_crawler = SZSEHtmlCrawler()
    szse_items = szse_crawler.fetch()
    print(f"获取到 {len(szse_items)} 条公告")
    for item in szse_items[:5]:
        print(f"  [{item['fund_code'] or 'N/A'}] {item['publish_date']} | {item['title'][:50]}...")
    
    # 保存到数据库
    total_saved = 0
    if sse_items:
        saved = save_to_db(sse_items)
        total_saved += saved
        print(f"\n上交所: 新增 {saved} 条公告到数据库")
    
    if szse_items:
        saved = save_to_db(szse_items)
        total_saved += saved
        print(f"深交所: 新增 {saved} 条公告到数据库")
    
    print(f"\n总计新增: {total_saved} 条公告")
    return total_saved


if __name__ == '__main__':
    # 检查是否安装了beautifulsoup4
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("请先安装 beautifulsoup4: pip install beautifulsoup4")
        sys.exit(1)
    
    test_crawlers()
