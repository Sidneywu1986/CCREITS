#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
巨潮资讯网公告爬虫
官方信息披露平台：http://www.cninfo.com.cn
"""

import requests
import json
import sqlite3
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# REITs基金代码列表
REITS_CODES = [
    # 上交所
    '508000', '508001', '508002', '508003', '508005', '508006', '508007', '508008', '508009',
    '508010', '508011', '508012', '508013', '508015', '508016', '508017', '508018', '508019',
    '508021', '508022', '508023', '508025', '508026', '508027', '508028', '508029', '508030',
    '508031', '508032', '508033', '508035', '508036', '508037', '508038', '508039', '508056',
    '508058', '508066', '508077', '508088', '508096', '508098', '508099',
    # 深交所
    '180101', '180102', '180103', '180201', '180202', '180203', '180301', '180302', '180401',
    '180501', '180502', '180503', '180601', '180602', '180701', '180801', '180901', '180902'
]

# 公告分类关键词
CATEGORY_KEYWORDS = {
    'operation': ['运营', '管理', '租赁', '出租率', '车流量', '收入', '物业', '经营'],
    'dividend': ['分红', '派息', '收益分配', '权益分派', '红利'],
    'inquiry': ['问询函', '关注函', '回复', '说明', '问询'],
    'financial': ['年报', '季报', '半年报', '审计', '财务报告', '业绩预告', '报告书'],
    'listing': ['上市', '发售', '认购', '招募说明书'],
    'disclosure': ['信息披露', '澄清', '风险提示']
}


def classify_announcement(title: str) -> str:
    """AI分类（关键词匹配）"""
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in title:
                return category
    return 'other'


def generate_summary(title: str, category: str) -> str:
    """生成摘要"""
    summaries = {
        'operation': '本基金发布运营相关公告，涉及物业经营、租赁收入等内容。',
        'dividend': '本基金发布分红派息相关公告，请关注权益登记日和除息日安排。',
        'inquiry': '本基金收到交易所问询函或发布相关回复公告。',
        'financial': '本基金发布定期财务报告，包含营收、利润等核心财务指标。',
        'listing': '本基金发布上市发行相关公告，涉及发售、认购等事项。',
        'disclosure': '本基金发布信息披露或重大事项澄清公告。',
        'other': '本基金发布重要公告，请关注具体内容。'
    }
    return summaries.get(category, summaries['other'])


def get_stock_announcements(stock_code: str, page_size: int = 20) -> List[Dict]:
    """
    获取单个股票的公告列表
    """
    url = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    # 确定市场类型
    if stock_code.startswith('5'):
        stock_code = f"{stock_code}.SH"
    else:
        stock_code = f"{stock_code}.SZ"
    
    data = {
        'stock': stock_code,
        'tabName': 'fulltext',
        'pageSize': str(page_size),
        'pageNum': '1',
        'column': 'fund' if stock_code.startswith('5') else 'fund',
        'category': 'category_reits_gszg_szjg',  # REITs公告分类
        'seDate': '',
        'isHLtitle': 'true'
    }
    
    try:
        response = requests.post(url, data=data, headers=headers, timeout=30)
        result = response.json()
        
        announcements = []
        if result.get('announcements'):
            for item in result['announcements']:
                title = item.get('announcementTitle', '')
                category = classify_announcement(title)
                
                # 提取基金代码（从标题中匹配6位数字）
                code_match = re.search(r'(\d{6})', title)
                fund_code = code_match.group(1) if code_match else stock_code.split('.')[0]
                
                # 构建PDF链接
                adjunct_url = item.get('adjunctUrl', '')
                pdf_url = f"http://static.cninfo.com.cn/{adjunct_url}" if adjunct_url else ''
                
                announcements.append({
                    'fund_code': fund_code,
                    'title': title,
                    'category': category,
                    'summary': generate_summary(title, category),
                    'publish_date': item.get('announcementTime', '').split()[0] if item.get('announcementTime') else '',
                    'source_url': f"http://www.cninfo.com.cn/new/disclosure/detail?stockCode={fund_code}&announcementId={item.get('announcementId', '')}",
                    'pdf_url': pdf_url,
                    'exchange': 'SSE' if stock_code.endswith('.SH') else 'SZSE',
                    'confidence': 0.9
                })
        
        return announcements
        
    except Exception as e:
        print(f"获取 {stock_code} 公告失败: {e}")
        return []


def crawl_all_announcements(limit_per_stock: int = 5) -> List[Dict]:
    """
    爬取所有REITs基金的公告
    """
    all_announcements = []
    print(f"开始爬取 {len(REITS_CODES)} 只REITs基金的公告...")
    
    for i, code in enumerate(REITS_CODES):
        try:
            announcements = get_stock_announcements(code, limit_per_stock)
            all_announcements.extend(announcements)
            print(f"  [{i+1}/{len(REITS_CODES)}] {code}: {len(announcements)} 条")
        except Exception as e:
            print(f"  [{i+1}/{len(REITS_CODES)}] {code}: 失败")
    
    # 去重并按日期排序
    seen = set()
    unique_announcements = []
    for ann in sorted(all_announcements, key=lambda x: x['publish_date'], reverse=True):
        key = (ann['fund_code'], ann['title'], ann['publish_date'])
        if key not in seen:
            seen.add(key)
            unique_announcements.append(ann)
    
    print(f"共获取 {len(unique_announcements)} 条 unique 公告")
    return unique_announcements


def save_to_database(announcements: List[Dict]):
    """保存公告到SQLite数据库"""
    db_path = '../database/reits.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        inserted = 0
        for ann in announcements:
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO announcements 
                    (fund_code, title, category, summary, publish_date, source_url, pdf_url, exchange, confidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    ann['fund_code'],
                    ann['title'],
                    ann['category'],
                    ann['summary'],
                    ann['publish_date'],
                    ann['source_url'],
                    ann['pdf_url'],
                    ann['exchange'],
                    ann['confidence']
                ))
                if cursor.rowcount > 0:
                    inserted += 1
            except Exception as e:
                print(f"插入失败: {e}")
        
        conn.commit()
        conn.close()
        print(f"保存到数据库: {inserted} 条新公告")
        return inserted
        
    except Exception as e:
        print(f"数据库保存失败: {e}")
        return 0


if __name__ == '__main__':
    announcements = crawl_all_announcements(limit_per_stock=3)
    if announcements:
        save_to_database(announcements)
        print("\n前5条公告:")
        for ann in announcements[:5]:
            print(f"  [{ann['exchange']}] {ann['publish_date']} {ann['fund_code']}: {ann['title'][:50]}...")
