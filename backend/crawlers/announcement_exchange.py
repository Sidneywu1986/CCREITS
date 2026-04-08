# -*- coding: utf-8 -*-
"""
REITs公告爬虫 v5 - 从官方交易所公告页面爬取
上交所: https://www.sse.com.cn/disclosure/fund/reits/
深交所: https://www.szse.cn/sustainablefinance/products/disclosure/reits/index.html
"""

import requests
from bs4 import BeautifulSoup
import sqlite3
import pandas as pd
from datetime import datetime
import time
import re
import os
import sys

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'reits.db')


class SSEAnnouncementCrawler:
    """上交所REITs公告爬虫"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
        self.base_url = "https://www.sse.com.cn/disclosure/fund/reits/"
    
    def fetch(self, page=1):
        """爬取上交所REITs公告"""
        try:
            # 尝试不同参数
            params = {'page': page}
            resp = self.session.get(self.base_url, params=params, timeout=15)
            resp.encoding = 'utf-8'
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            items = []
            # 查找公告表格或列表
            # 上交所公告通常在 .table-list 或 table 中
            rows = soup.select('table tr') or soup.select('.table-list tr')
            
            for row in rows[1:]:  # 跳过表头
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 3:
                    code_elem = cells[0].find('a') or cells[0]
                    title_elem = cells[2].find('a') or cells[2]
                    date_elem = cells[-1]
                    
                    code = code_elem.get_text(strip=True)
                    title = title_elem.get_text(strip=True)
                    date = date_elem.get_text(strip=True)
                    
                    # 提取PDF链接
                    pdf_url = None
                    if title_elem.name == 'a' and title_elem.get('href'):
                        href = title_elem['href']
                        # 上交所PDF链接
                        if href.startswith('/'):
                            pdf_url = f"https://www.sse.com.cn{href}"
                        elif href.startswith('http'):
                            pdf_url = href
                    
                    # 检查是否有下载按钮链接
                    download_link = row.find('a', class_=re.compile('download|pdf'))
                    if download_link and download_link.get('href'):
                        pdf_url = download_link['href']
                        if pdf_url.startswith('/'):
                            pdf_url = f"https://www.sse.com.cn{pdf_url}"
                    
                    # 分类
                    category = 'dividend' if any(kw in title for kw in ['收益分配', '分红', '权益分派', '现金红利']) else 'other'
                    
                    items.append({
                        'fund_code': code if re.match(r'^508\d{3}$', code) else None,
                        'exchange': 'SSE',
                        'title': title,
                        'category': category,
                        'publish_date': date,
                        'url': pdf_url,
                    })
            
            return items
        except Exception as e:
            print(f"[ERROR] SSE fetch: {e}")
            import traceback
            traceback.print_exc()
            return []


class SZSEAnnouncementCrawler:
    """深交所REITs公告爬虫"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
        self.base_url = "https://www.szse.cn/sustainablefinance/products/disclosure/reits/index.html"
    
    def fetch(self):
        """爬取深交所REITs公告"""
        try:
            resp = self.session.get(self.base_url, timeout=15)
            resp.encoding = 'utf-8'
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            items = []
            # 深交所公告在表格中
            rows = soup.select('table tr') or soup.select('.table-list tr')
            
            for row in rows[1:]:  # 跳过表头
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 4:
                    code_elem = cells[0].find('a') or cells[0]
                    name_elem = cells[1].find('a') or cells[1]
                    title_elem = cells[2].find('a') or cells[2]
                    date_elem = cells[-1]
                    
                    code = code_elem.get_text(strip=True)
                    title = title_elem.get_text(strip=True)
                    date = date_elem.get_text(strip=True)
                    
                    # 提取PDF链接（从下载按钮）
                    pdf_url = None
                    download_btn = row.find('a', href=re.compile('\.pdf'))
                    if download_btn and download_btn.get('href'):
                        pdf_url = download_btn['href']
                        if pdf_url.startswith('/'):
                            pdf_url = f"https://www.szse.cn{pdf_url}"
                    
                    # 分类
                    category = 'dividend' if any(kw in title for kw in ['收益分配', '分红', '权益分派', '现金红利']) else 'other'
                    
                    items.append({
                        'fund_code': code if re.match(r'^180\d{3}$', code) else None,
                        'exchange': 'SZSE',
                        'title': title,
                        'category': category,
                        'publish_date': date,
                        'url': pdf_url,
                    })
            
            return items
        except Exception as e:
            print(f"[ERROR] SZSE fetch: {e}")
            import traceback
            traceback.print_exc()
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
    print("测试上交所公告爬虫...")
    print(f"URL: https://www.sse.com.cn/disclosure/fund/reits/")
    
    sse_crawler = SSEAnnouncementCrawler()
    sse_items = sse_crawler.fetch(page=1)
    print(f"获取到 {len(sse_items)} 条公告")
    for item in sse_items[:5]:
        print(f"  [{item['fund_code'] or 'N/A'}] {item['publish_date']} | {item['title'][:50]}...")
        print(f"      PDF: {item['url']}")
    
    print("\n" + "="*60)
    print("测试深交所公告爬虫...")
    print(f"URL: https://www.szse.cn/sustainablefinance/products/disclosure/reits/index.html")
    
    szse_crawler = SZSEAnnouncementCrawler()
    szse_items = szse_crawler.fetch()
    print(f"获取到 {len(szse_items)} 条公告")
    for item in szse_items[:5]:
        print(f"  [{item['fund_code'] or 'N/A'}] {item['publish_date']} | {item['title'][:50]}...")
        print(f"      PDF: {item['url']}")
    
    # 保存
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
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("请先安装 beautifulsoup4: pip install beautifulsoup4")
        sys.exit(1)
    
    test_crawlers()
