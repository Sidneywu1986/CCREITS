#!/usr/bin/env python3
"""
CNInfo 公告定时同步脚本 - 轻量并发版
只获取列表+入库，不下载PDF，81只REIT并发执行
"""
import sys
import os
import concurrent.futures
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from crawlers.cninfo_crawler import CNInfoCrawler
from crawlers.cninfo_db_sync import save_announcements_to_db

ALL_REIT_CODES = list(CNInfoCrawler.REIT_CODE_MAPPING.keys())


def sync_single(code, max_count=5, days_back=7):
    """同步单只REIT的公告"""
    try:
        crawler = CNInfoCrawler(verbose=False)
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        fund_info = crawler.search_fund(code)
        if not fund_info:
            return {'code': code, 'found': 0, 'inserted': 0, 'skipped': 0, 'error': 'no fund info'}

        anns = crawler.get_announcements(
            code,
            fund_info.get('orgId', ''),
            start_date,
            end_date,
            page_size=min(max_count, 100)
        )

        db_result = save_announcements_to_db(anns[:max_count], code)
        return {
            'code': code,
            'found': len(anns),
            'inserted': db_result['inserted'],
            'skipped': db_result['skipped']
        }
    except Exception as e:
        return {'code': code, 'error': str(e)}


def main():
    max_workers = int(os.getenv('CNINFO_WORKERS', '8'))
    max_count = int(os.getenv('CNINFO_MAX_COUNT', '5'))
    days_back = int(os.getenv('CNINFO_DAYS', '7'))

    print(f'[CNInfo Scheduler] {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} 开始同步 {len(ALL_REIT_CODES)} 只REIT (workers={max_workers}, max_count={max_count}, days={days_back})')
    start = datetime.now()

    total_inserted = 0
    total_skipped = 0
    errors = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(sync_single, code, max_count, days_back): code
            for code in ALL_REIT_CODES
        }
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if 'error' in result and 'inserted' not in result:
                errors += 1
                print(f"  ❌ {result['code']}: {result['error']}")
            else:
                total_inserted += result['inserted']
                total_skipped += result['skipped']
                if result['inserted'] > 0:
                    print(f"  ✅ {result['code']}: +{result['inserted']} (found {result['found']})")

    duration = (datetime.now() - start).total_seconds()
    print(f'[CNInfo Scheduler] 完成: 新增 {total_inserted} | 跳过 {total_skipped} | 失败 {errors} | 耗时 {duration:.1f}s')


if __name__ == '__main__':
    main()
