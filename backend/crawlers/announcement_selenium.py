# -*- coding: utf-8 -*-
"""
REITs公告完整爬虫 - 使用Selenium抓取交易所公告
适用于：生产环境部署后
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import sqlite3
import time
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'reits.db')


def init_driver():
    """初始化无头浏览器"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # 无头模式
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver


def crawl_sse_announcements(driver, pages=5):
    """
    爬取上交所公告
    URL: https://www.sse.com.cn/disclosure/fund/reits/
    """
    announcements = []
    
    for page in range(1, pages + 1):
        try:
            url = f"https://www.sse.com.cn/disclosure/fund/reits/"
            driver.get(url)
            
            # 等待表格加载
            wait = WebDriverWait(driver, 10)
            table = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table")))
            
            # 解析表格
            rows = table.find_elements(By.TAG_NAME, "tr")
            for row in rows[1:]:  # 跳过表头
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 4:
                    code = cells[0].text.strip()
                    title = cells[2].text.strip()
                    date = cells[-1].text.strip()
                    
                    # 提取PDF链接
                    pdf_link = None
                    try:
                        pdf_btn = row.find_element(By.CSS_SELECTOR, "a[href*='.pdf']")
                        pdf_link = pdf_btn.get_attribute('href')
                    except:
                        pass
                    
                    if code and title:
                        announcements.append({
                            'fund_code': code if code.startswith('508') else None,
                            'exchange': 'SSE',
                            'title': title,
                            'category': 'dividend' if '收益分配' in title else 'other',
                            'publish_date': date,
                            'url': pdf_link,
                        })
            
            print(f"[SSE] 第{page}页完成，获取{len(rows)-1}条")
            time.sleep(2)
            
        except Exception as e:
            print(f"[ERROR] SSE page {page}: {e}")
    
    return announcements


def crawl_szse_announcements(driver, pages=5):
    """
    爬取深交所公告
    URL: https://www.szse.cn/sustainablefinance/products/disclosure/reits/index.html
    """
    announcements = []
    
    try:
        url = "https://www.szse.cn/sustainablefinance/products/disclosure/reits/index.html"
        driver.get(url)
        
        # 等待表格加载
        wait = WebDriverWait(driver, 10)
        table = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table")))
        
        # 解析表格
        rows = table.find_elements(By.TAG_NAME, "tr")
        for row in rows[1:]:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) >= 4:
                code = cells[0].text.strip()
                title = cells[2].text.strip()
                date = cells[-1].text.strip()
                
                # 提取PDF链接
                pdf_link = None
                try:
                    pdf_btn = row.find_element(By.CSS_SELECTOR, "a.download, a[href*='.pdf']")
                    pdf_link = pdf_btn.get_attribute('href')
                except:
                    pass
                
                if code and title:
                    announcements.append({
                        'fund_code': code if code.startswith('180') else None,
                        'exchange': 'SZSE',
                        'title': title,
                        'category': 'dividend' if '收益分配' in title else 'other',
                        'publish_date': date,
                        'url': pdf_link,
                    })
        
        print(f"[SZSE] 获取{len(rows)-1}条公告")
        
    except Exception as e:
        print(f"[ERROR] SZSE: {e}")
    
    return announcements


def save_to_db(items):
    """保存到数据库"""
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


if __name__ == '__main__':
    print("="*60)
    print("REITs公告完整爬虫 (Selenium)")
    print("="*60)
    
    driver = init_driver()
    
    try:
        # 爬取上交所
        print("\n1. 爬取上交所公告...")
        sse_items = crawl_sse_announcements(driver, pages=10)
        sse_saved = save_to_db(sse_items)
        print(f"上交所: 获取{len(sse_items)}条, 新增{sse_saved}条")
        
        # 爬取深交所
        print("\n2. 爬取深交所公告...")
        szse_items = crawl_szse_announcements(driver, pages=10)
        szse_saved = save_to_db(szse_items)
        print(f"深交所: 获取{len(szse_items)}条, 新增{szse_saved}条")
        
        print(f"\n总计新增: {sse_saved + szse_saved}条公告")
        
    finally:
        driver.quit()
