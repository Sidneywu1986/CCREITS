#!/usr/bin/env python3
"""
REIT公告PDF批量下载脚本
存储规范:
    /data/announcements/
        ├── SSE/
        │   ├── 508000_华安张江产业园REIT/
        │   │   ├── 20210519_招募说明书.pdf
        │   │   └── ...
        │   └── ...
        └── SZSE/
            ├── 180101_博时蛇口产园REIT/
            └── ...

用法:
    python download_announcement_pdfs.py --code 508000
    python download_announcement_pdfs.py --all --output-dir /data/announcements
    python download_announcement_pdfs.py --exchange SSE
"""

import os
import sys
import re
import argparse
import logging
import hashlib
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from core.db import get_conn

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# 基金简称缓存（从数据库获取）
_fund_name_cache = {}


def get_fund_name(fund_code):
    """获取基金简称"""
    if fund_code in _fund_name_cache:
        return _fund_name_cache[fund_code]
    
    try:
        with get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT title FROM business.announcements 
                WHERE fund_code = %s 
                ORDER BY publish_date 
                LIMIT 1
            ''', (fund_code,))
            row = cursor.fetchone()
            if row:
                title = row['title']
                # Extract fund name from title
                # e.g., "华安张江产业园封闭式基础设施证券投资基金2026年第1季度报告"
                name = re.sub(
                    r'(?:关于|召开|202\d.*|基金产品.*|招募说明书.*|基金经理.*|分红.*|'
                    r'运营数据.*|业绩说明会.*|评估报告.*|年度报告.*|审计报告.*|'
                    r'中期报告.*|季度报告.*|临时报告.*|上市.*|交易.*|募集.*|认购.*|'
                    r'扩募.*|初始.*|询价.*|定价.*|发售.*|申购.*|份额.*|收益分配.*|'
                    r'权益分派.*|停牌.*|复牌.*|公告书.*|提示性公告.*|托管协议.*|'
                    r'基金合同.*|法律意见.*|核查报告.*|投资者关系.*|持有人大会.*|'
                    r'比例配售.*|回拨.*|做市商.*|改聘.*|新增.*|变更.*|更新.*)',
                    '', title
                )
                name = name.replace('封闭式基础设施证券投资基金', '').strip()
                name = re.sub(r'^[的\s]+|[\s]+$', '', name)
                _fund_name_cache[fund_code] = name
                return name
    except Exception as e:
        logger.error(f'获取基金名称失败 {fund_code}: {e}')
    
    _fund_name_cache[fund_code] = fund_code
    return fund_code


def sanitize_filename(text, max_length=120):
    """清理文件名中的非法字符"""
    text = re.sub(r'[\\/*?:"<>|]', '_', text)
    text = text.replace('\n', ' ').replace('\r', ' ')
    text = text.strip()
    return text[:max_length]


def download_pdf(pdf_url, filepath, timeout=60):
    """下载单个PDF，支持断点续传"""
    if os.path.exists(filepath):
        # 检查文件是否完整（至少1KB）
        if os.path.getsize(filepath) > 1024:
            return {'success': True, 'skipped': True, 'size': os.path.getsize(filepath)}
    
    try:
        resp = requests.get(pdf_url, timeout=timeout, stream=True)
        resp.raise_for_status()
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        size = os.path.getsize(filepath)
        return {'success': True, 'skipped': False, 'size': size}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}


def download_fund_pdfs(fund_code, output_dir, limit=None):
    """下载单只REIT的所有PDF"""
    exchange = 'SSE' if fund_code.startswith('508') else 'SZSE'
    fund_name = get_fund_name(fund_code)
    
    # Build directory path
    fund_dir = os.path.join(output_dir, exchange, f"{fund_code}_{sanitize_filename(fund_name, 30)}")
    
    try:
        with get_conn() as conn:
            cursor = conn.cursor()
            query = '''
                SELECT id, title, publish_date, pdf_url
                FROM business.announcements 
                WHERE fund_code = %s AND pdf_url IS NOT NULL AND pdf_url != ''
                ORDER BY publish_date DESC
            '''
            if limit:
                query += f' LIMIT {limit}'
            cursor.execute(query, (fund_code,))
            rows = cursor.fetchall()
    except Exception as e:
        logger.error(f'[DB] 查询失败 {fund_code}: {e}')
        return {'success': False, 'error': str(e)}
    
    stats = {'total': len(rows), 'downloaded': 0, 'skipped': 0, 'failed': 0, 'bytes': 0}
    
    for i, row in enumerate(rows):
        title = row['title']
        pub_date = row['publish_date']
        pdf_url = row['pdf_url']
        
        # Build filename: YYYYMMDD_公告标题.pdf
        date_str = str(pub_date).replace('-', '') if pub_date else 'unknown'
        safe_title = sanitize_filename(title)
        filename = f"{date_str}_{safe_title}.pdf"
        filepath = os.path.join(fund_dir, filename)
        
        result = download_pdf(pdf_url, filepath)
        
        if result['success']:
            if result.get('skipped'):
                stats['skipped'] += 1
            else:
                stats['downloaded'] += 1
                stats['bytes'] += result.get('size', 0)
        else:
            stats['failed'] += 1
            logger.warning(f'[FAIL] {fund_code} | {filename} | {result.get("error", "")}')
        
        if (i + 1) % 10 == 0:
            logger.info(f'[PROGRESS] {fund_code} | {i+1}/{len(rows)} | '
                       f'OK={stats["downloaded"]} SKIP={stats["skipped"]} FAIL={stats["failed"]}')
    
    logger.info(f'[DONE] {fund_code} | 总计{stats["total"]} | '
                f'下载{stats["downloaded"]} | 跳过{stats["skipped"]} | 失败{stats["failed"]} | '
                f'{(stats["bytes"] / 1024 / 1024):.1f}MB')
    
    return {'success': True, 'stats': stats}


def download_all_pdfs(output_dir, exchange=None, limit_per_fund=None):
    """下载所有REIT的PDF"""
    try:
        with get_conn() as conn:
            cursor = conn.cursor()
            query = '''
                SELECT DISTINCT fund_code 
                FROM business.announcements 
                WHERE pdf_url IS NOT NULL AND pdf_url != ''
            '''
            if exchange:
                cursor.execute(query + ' AND exchange = %s ORDER BY fund_code', (exchange,))
            else:
                cursor.execute(query + ' ORDER BY fund_code')
            rows = cursor.fetchall()
    except Exception as e:
        logger.error(f'[DB] 查询失败: {e}')
        return
    
    fund_codes = [r['fund_code'] for r in rows]
    logger.info(f'[START] 共 {len(fund_codes)} 只REIT需要下载PDF')
    
    total_stats = {'funds': 0, 'total': 0, 'downloaded': 0, 'skipped': 0, 'failed': 0, 'bytes': 0}
    
    for code in fund_codes:
        result = download_fund_pdfs(code, output_dir, limit=limit_per_fund)
        if result.get('success'):
            s = result['stats']
            total_stats['funds'] += 1
            total_stats['total'] += s['total']
            total_stats['downloaded'] += s['downloaded']
            total_stats['skipped'] += s['skipped']
            total_stats['failed'] += s['failed']
            total_stats['bytes'] += s.get('bytes', 0)
    
    logger.info('=' * 60)
    logger.info(f'[ALL DONE] {total_stats["funds"]} 只REIT | '
                f'总计{total_stats["total"]} 个PDF | '
                f'下载{total_stats["downloaded"]} | '
                f'跳过{total_stats["skipped"]} | '
                f'失败{total_stats["failed"]} | '
                f'{(total_stats["bytes"] / 1024 / 1024):.1f}MB')
    logger.info(f'存储路径: {output_dir}')
    logger.info('=' * 60)


def main():
    parser = argparse.ArgumentParser(description='REIT公告PDF批量下载')
    parser.add_argument('--code', help='单只REIT代码')
    parser.add_argument('--exchange', choices=['SSE', 'SZSE'], help='按交易所下载')
    parser.add_argument('--all', action='store_true', help='下载全部')
    parser.add_argument('--output-dir', default='/Users/apple/Projects/CCREITS/data/announcements',
                        help='PDF存储根目录')
    parser.add_argument('--limit', type=int, help='每只REIT最多下载数量')
    args = parser.parse_args()
    
    if args.code:
        download_fund_pdfs(args.code, args.output_dir, limit=args.limit)
    elif args.all or args.exchange:
        download_all_pdfs(args.output_dir, exchange=args.exchange, limit_per_fund=args.limit)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
