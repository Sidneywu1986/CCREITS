#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKShare REITs公告/新闻爬虫
数据源：东方财富
"""

import akshare as ak
import re
import sys
import os
import hashlib
from datetime import datetime
from typing import List, Dict

# 添加数据库路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.db import get_conn
import logging
logger = logging.getLogger(__name__)

# REITs基金代码列表 (精简版，主要活跃的REITs)
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
    'operation': ['运营', '管理', '租赁', '出租率', '车流量', '收入', '物业', '经营', '项目'],
    'dividend': ['分红', '派息', '收益分配', '权益分派', '红利', '分配'],
    'inquiry': ['问询函', '关注函', '回复', '说明', '问询', '关注'],
    'financial': ['年报', '季报', '半年报', '审计', '财务报告', '业绩预告', '报告书', '报告期'],
    'listing': ['上市', '发售', '认购', '招募说明书', '扩募', '扩募'],
    'disclosure': ['信息披露', '澄清', '风险提示', '停牌', '复牌']
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


def get_stock_news(symbol: str) -> List[Dict]:
    """
    获取单个股票的新闻/公告
    """
    announcements = []
    
    try:
        # 获取东财个股新闻
        df = ak.stock_news_em(symbol=symbol)
        
        if df is not None and len(df) > 0:
            for _, row in df.iterrows():
                # 修复：'新闻标题'是真正的标题，'关键词'是基金代码
                title = str(row.get('新闻标题', ''))
                keyword = str(row.get('关键词', ''))  # 基金代码
                content = str(row.get('新闻内容', ''))
                pub_time = str(row.get('发布时间', ''))
                source = str(row.get('新闻来源', ''))
                url = str(row.get('新闻链接', ''))
                
                # 提取日期
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', pub_time)
                publish_date = date_match.group(1) if date_match else datetime.now().strftime('%Y-%m-%d')
                
                # 分类
                category = classify_announcement(title)
                
                # 确定交易所
                exchange = 'SSE' if symbol.startswith('5') else 'SZSE'
                
                announcements.append({
                    'fund_code': symbol,
                    'title': title[:200],  # 限制长度
                    'category': category,
                    'summary': content[:500] if content else generate_summary(title, category),
                    'publish_date': publish_date,
                    'source_url': url,
                    'pdf_url': '',
                    'exchange': exchange,
                    'confidence': 0.85
                })
                
    except Exception as e:
        logger.error(f"  获取 {symbol} 新闻失败: {e}")
    
    return announcements


def crawl_all_announcements(limit_per_stock: int = 5, max_stocks: int = 20) -> List[Dict]:
    """
    爬取REITs基金的新闻/公告
    """
    all_announcements = []
    stocks_to_crawl = REITS_CODES[:max_stocks]  # 限制数量避免请求过多
    
    logger.info(f"开始爬取 {len(stocks_to_crawl)} 只REITs基金的新闻...")
    
    for i, code in enumerate(stocks_to_crawl):
        try:
            news = get_stock_news(code)
            # 限制每个股票的新闻数量
            news = news[:limit_per_stock]
            all_announcements.extend(news)
            logger.info(f"  [{i+1}/{len(stocks_to_crawl)}] {code}: {len(news)} 条")
        except Exception as e:
            logger.error(f"  [{i+1}/{len(stocks_to_crawl)}] {code}: 失败")
    
    # 去重并按日期排序
    seen = set()
    unique_announcements = []
    for ann in sorted(all_announcements, key=lambda x: x['publish_date'], reverse=True):
        key = (ann['fund_code'], ann['title'], ann['publish_date'])
        if key not in seen:
            seen.add(key)
            unique_announcements.append(ann)
    
    logger.info(f"共获取 {len(unique_announcements)} 条 unique 公告")
    return unique_announcements


def save_to_database(announcements: List[Dict]) -> int:
    """保存公告到PostgreSQL数据库"""
    
    inserted = 0
    try:
        with get_conn() as conn:
            cursor = conn.cursor()
            
            for ann in announcements:
                try:
                    content_hash = hashlib.md5(f"{ann['fund_code']}:{ann['publish_date']}:{ann['title']}".encode()).hexdigest()
                    cursor.execute('''
                        INSERT INTO business.announcements 
                        (fund_code, title, category, summary, publish_date, source_url, pdf_url, exchange, confidence, content_hash)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (content_hash) DO NOTHING
                    ''', (
                        ann['fund_code'],
                        ann['title'],
                        ann['category'],
                        ann['summary'],
                        ann['publish_date'],
                        ann['source_url'],
                        ann['pdf_url'],
                        ann['exchange'],
                        ann['confidence'],
                        content_hash
                    ))
                    if cursor.rowcount > 0:
                        inserted += 1
                except Exception as e:
                    logger.error(f"插入失败: {e}")
            
            conn.commit()
        
        logger.info(f"保存到数据库: {inserted} 条新公告")
        return inserted
        
    except Exception as e:
        logger.error(f"数据库保存失败: {e}")
        return 0


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("REITs公告爬虫 (AKShare版)")
    logger.info("=" * 60)
    
    # 爬取公告
    announcements = crawl_all_announcements(limit_per_stock=3, max_stocks=10)
    
    if announcements:
        # 保存到数据库
        inserted = save_to_database(announcements)
        
        # 显示前5条
        logger.info("\n前5条公告:")
        for ann in announcements[:5]:
            logger.info(f"  [{ann['exchange']}] {ann['publish_date']} {ann['fund_code']}: {ann['title'][:40]}...")
        
        return inserted
    else:
        logger.info("未获取到公告")
        return 0


if __name__ == '__main__':
    main()
