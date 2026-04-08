#!/usr/bin/env python3
"""
CNInfo公告数据自动同步到数据库
"""

import sqlite3
import re
import os
from datetime import datetime

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'reits.db')

def classify_announcement(title):
    """自动分类公告"""
    title_lower = title.lower()
    
    # 分红类
    if any(kw in title for kw in ['分红', '收益分配', '红利', '派息', '分红公告书']):
        return 'dividend'
    
    # 运营类
    if any(kw in title for kw in ['运营', '经营', '现金流', '出租率', ' occupancy', '招募说明书更新']):
        return 'operation'
    
    # 财务类
    if any(kw in title for kw in ['年报', '中报', '季报', '年度报告', '中期报告', '季度报告', '审计']):
        return 'financial'
    
    # 询价类
    if any(kw in title for kw in ['询价', '定价', '发售', '认购', '扩募']):
        return 'inquiry'
    
    return 'other'

def get_exchange(code):
    """根据代码判断交易所"""
    if code.startswith('508'):
        return 'SSE'  # 上交所
    elif code.startswith('180'):
        return 'SZSE'  # 深交所
    return None

def save_announcements_to_db(announcements, fund_code):
    """
    将公告保存到数据库
    
    Args:
        announcements: 公告列表，每项包含title, time, pdf_url, adjunctUrl
        fund_code: 基金代码
    
    Returns:
        dict: 保存统计信息
    """
    if not announcements:
        return {'inserted': 0, 'skipped': 0, 'error': None}
    
    result = {'inserted': 0, 'skipped': 0, 'error': None}
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        exchange = get_exchange(fund_code)
        cninfo_search_url = f'http://www.cninfo.com.cn/new/information/topSearch/query?keyWord={fund_code}'
        
        for ann in announcements:
            try:
                title = ann.get('title', '')
                publish_time = ann.get('time', '')
                pdf_url = ann.get('pdf_url', '')
                
                # 处理日期格式
                if isinstance(publish_time, int):
                    # 时间戳格式
                    publish_date = datetime.fromtimestamp(publish_time/1000).strftime('%Y-%m-%d')
                elif isinstance(publish_time, str) and len(publish_time) >= 10:
                    publish_date = publish_time[:10]
                else:
                    publish_date = datetime.now().strftime('%Y-%m-%d')
                
                # 分类
                category = classify_announcement(title)
                
                # 检查是否已存在（根据fund_code + title + publish_date去重）
                cursor.execute('''
                    SELECT id FROM announcements 
                    WHERE fund_code = ? AND title = ? AND publish_date = ?
                ''', (fund_code, title, publish_date))
                
                if cursor.fetchone():
                    result['skipped'] += 1
                    continue
                
                # 插入数据
                cursor.execute('''
                    INSERT INTO announcements 
                    (fund_code, title, category, publish_date, source_url, pdf_url, exchange, confidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    fund_code,
                    title,
                    category,
                    publish_date,
                    cninfo_search_url,  # source_url使用巨潮搜索链接
                    pdf_url,  # 直接PDF链接
                    exchange,
                    90  # 爬虫数据置信度较高
                ))
                
                result['inserted'] += 1
                
            except Exception as e:
                print(f'[DB] 保存单条公告失败: {e}')
                continue
        
        conn.commit()
        conn.close()
        
        print(f'[DB] 同步完成: 新增{result["inserted"]}条, 跳过{result["skipped"]}条重复')
        
    except Exception as e:
        result['error'] = str(e)
        print(f'[DB] 数据库操作失败: {e}')
    
    return result

def sync_single_fund(fund_code, max_count=30):
    """
    同步单只REIT的公告到数据库
    
    Args:
        fund_code: 基金代码
        max_count: 最大获取数量
    
    Returns:
        dict: 同步结果
    """
    from cninfo_crawler import CNInfoCrawler
    
    print(f'[SYNC] 开始同步 {fund_code} 的公告...')
    
    crawler = CNInfoCrawler()
    
    # 获取基金信息
    fund_info = crawler.search_fund(fund_code)
    if not fund_info and fund_code.startswith('508'):
        fund_info = {
            'code': fund_code,
            'name': f'上海REIT-{fund_code}',
            'orgId': '',
            'market': 'sh'
        }
    
    if not fund_info:
        return {'success': False, 'error': '未找到基金信息'}
    
    # 获取公告列表（最近30天）
    from datetime import datetime, timedelta
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    
    announcements = crawler.get_announcements(
        fund_code,
        fund_info.get('orgId', ''),
        start_date,
        end_date,
        page_size=min(max_count, 100)
    )
    
    # 保存到数据库
    db_result = save_announcements_to_db(announcements[:max_count], fund_code)
    
    return {
        'success': True,
        'fund_code': fund_code,
        'total_found': len(announcements),
        'inserted': db_result['inserted'],
        'skipped': db_result['skipped']
    }

def sync_all_reits(max_count=30):
    """
    同步所有REIT的公告到数据库
    
    Args:
        max_count: 每只REIT最大获取数量
    
    Returns:
        dict: 同步统计
    """
    from cninfo_crawler import REIT_CODE_MAPPING
    
    print(f'[SYNC] 开始同步所有REIT公告，每只最多{max_count}条...')
    
    stats = {
        'total': len(REIT_CODE_MAPPING),
        'success': 0,
        'failed': 0,
        'total_inserted': 0,
        'total_skipped': 0
    }
    
    for code in REIT_CODE_MAPPING.keys():
        try:
            result = sync_single_fund(code, max_count)
            if result['success']:
                stats['success'] += 1
                stats['total_inserted'] += result['inserted']
                stats['total_skipped'] += result['skipped']
            else:
                stats['failed'] += 1
                print(f'[SYNC] {code} 同步失败: {result.get("error")}')
        except Exception as e:
            stats['failed'] += 1
            print(f'[SYNC] {code} 同步异常: {e}')
    
    print(f'[SYNC] 全部同步完成: 成功{stats["success"]}/{stats["total"]}, 新增{stats["total_inserted"]}条')
    return stats

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='CNInfo公告数据库同步')
    parser.add_argument('--code', help='单个REIT代码')
    parser.add_argument('--max-count', type=int, default=30, help='每只最大数量')
    parser.add_argument('--all', action='store_true', help='同步全部')
    
    args = parser.parse_args()
    
    if args.all:
        sync_all_reits(args.max_count)
    elif args.code:
        result = sync_single_fund(args.code, args.max_count)
        print(result)
    else:
        print('请指定 --code 或 --all')
