#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量爬取全部79只REIT公告
并发执行，支持断点续传和统计报告
"""

import os
import sys
import json
import time
import concurrent.futures
from datetime import datetime, timedelta
from pathlib import Path
import logging

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cninfo_crawler import CNInfoCrawler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawl_all_reits.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 全部79只REIT代码列表
ALL_REIT_CODES = [
    # 上交所REIT (58只)
    '508000', '508001', '508002', '508003', '508005', '508006', '508007', '508008', 
    '508009', '508010', '508011', '508012', '508015', '508016', '508017', '508018',
    '508019', '508021', '508022', '508026', '508027', '508028', '508029', '508031',
    '508033', '508036', '508039', '508048', '508050', '508055', '508056', '508058',
    '508060', '508066', '508068', '508069', '508077', '508078', '508080', '508082',
    '508084', '508085', '508086', '508087', '508088', '508089', '508090', '508091',
    '508092', '508096', '508097', '508098', '508099',
    # 深交所REIT (21只)
    '180101', '180102', '180103', '180105', '180106', '180201', '180202', '180203',
    '180301', '180302', '180303', '180305', '180306', '180401', '180402', '180501',
    '180502', '180601', '180602', '180603', '180605', '180606', '180607', '180701',
    '180801', '180901'
]

# 统计信息
class CrawlStats:
    def __init__(self):
        self.total = len(ALL_REIT_CODES)
        self.success = 0
        self.failed = 0
        self.total_announcements = 0
        self.total_downloaded = 0
        self.start_time = time.time()
        self.results = []
        self.errors = []
    
    def add_success(self, code, name, ann_count, downloaded):
        self.success += 1
        self.total_announcements += ann_count
        self.total_downloaded += downloaded
        self.results.append({
            'code': code,
            'name': name,
            'announcements': ann_count,
            'downloaded': downloaded,
            'status': 'success'
        })
        logger.info(f'完成 {code}: {ann_count}条公告, {downloaded}个PDF')
    
    def add_failed(self, code, error):
        self.failed += 1
        self.errors.append({'code': code, 'error': str(error)})
        logger.error(f'失败 {code}: {error}')
    
    def report(self):
        duration = time.time() - self.start_time
        print('\n' + '='*70)
        print('[批量爬取统计报告]')
        print('='*70)
        print(f'总数量:    {self.total} 只REIT')
        print(f'成功:      {self.success} 只 ({self.success/self.total*100:.1f}%)')
        print(f'失败:      {self.failed} 只 ({self.failed/self.total*100:.1f}%)')
        print(f'总公告:    {self.total_announcements} 条')
        print(f'总下载:    {self.total_downloaded} 个PDF')
        print(f'耗时:      {duration:.1f} 秒 ({duration/60:.1f} 分钟)')
        print(f'平均速度:  {self.total_announcements/duration:.1f} 条/秒')
        print('='*70)
        
        if self.errors:
            print('\n失败列表:')
            for err in self.errors:
                print(f"  {err['code']}: {err['error']}")
        
        # 保存详细报告
        report_file = f'crawl_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                'summary': {
                    'total': self.total,
                    'success': self.success,
                    'failed': self.failed,
                    'total_announcements': self.total_announcements,
                    'total_downloaded': self.total_downloaded,
                    'duration_seconds': duration
                },
                'results': self.results,
                'errors': self.errors
            }, f, ensure_ascii=False, indent=2)
        print(f'\n详细报告已保存: {report_file}')


def crawl_single_reit(code, output_dir, max_count=50):
    """
    爬取单只REIT的公告
    """
    try:
        crawler = CNInfoCrawler(verbose=False)
        
        # 爬取公告（不下载PDF，只获取列表）
        result = crawler.batch_crawl(
            keyword=code,
            start_date=(datetime.now() - timedelta(days=365*2)).strftime('%Y-%m-%d'),  # 近2年
            end_date=datetime.now().strftime('%Y-%m-%d'),
            max_count=max_count,
            output_dir=output_dir,
            task_id=f'batch_{code}'
        )
        
        if result['success']:
            return {
                'code': code,
                'name': result['fund_info']['name'] if result['fund_info'] else code,
                'announcements': len(result['announcements']),
                'downloaded': result['stats'].get('downloaded', 0),
                'status': 'success'
            }
        else:
            return {
                'code': code,
                'error': result.get('error', '未知错误'),
                'status': 'failed'
            }
            
    except (RuntimeError, OSError, ValueError) as e:
        return {
            'code': code,
            'error': '爬取异常，请查看日志',
            'status': 'failed'
        }


def batch_crawl_all(
    max_workers=5,  # 并发数
    max_count=50,   # 每只REIT最大公告数
    output_dir='./all_reits_announcements'
):
    """
    批量爬取全部79只REIT
    """
    stats = CrawlStats()
    
    print('='*70)
    print(f'开始批量爬取 {len(ALL_REIT_CODES)} 只REIT公告')
    print(f'   并发数: {max_workers}')
    print(f'   每只股票最大: {max_count} 条')
    print(f'   输出目录: {output_dir}')
    print('='*70)
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 并发执行
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_code = {
            executor.submit(crawl_single_reit, code, output_dir, max_count): code 
            for code in ALL_REIT_CODES
        }
        
        # 处理完成的任务
        for future in concurrent.futures.as_completed(future_to_code):
            code = future_to_code[future]
            try:
                result = future.result(timeout=120)  # 2分钟超时
                
                if result['status'] == 'success':
                    stats.add_success(
                        result['code'], 
                        result['name'],
                        result['announcements'],
                        result['downloaded']
                    )
                else:
                    stats.add_failed(result['code'], result['error'])
                    
            except (RuntimeError, OSError, ValueError) as e:
                stats.add_failed(code, f'执行异常: {e}')
            
            # 打印进度
            progress = stats.success + stats.failed
            if progress % 10 == 0 or progress == stats.total:
                print(f'\n进度: {progress}/{stats.total} ({progress/stats.total*100:.1f}%)')
    
    # 生成报告
    stats.report()
    return stats


def quick_test_sample():
    """
    快速测试：抽样爬取5只REIT
    """
    sample_codes = ['508000', '508002', '180101', '180201', '508056']
    print('='*70)
    print('快速测试模式 (抽样5只)')
    print('='*70)
    
    stats = CrawlStats()
    stats.total = len(sample_codes)
    
    for code in sample_codes:
        result = crawl_single_reit(code, './test_announcements', max_count=5)
        if result['status'] == 'success':
            stats.add_success(result['code'], result['name'], 
                           result['announcements'], result['downloaded'])
        else:
            stats.add_failed(result['code'], result['error'])
    
    stats.report()
    return stats


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='批量爬取79只REIT公告')
    parser.add_argument('--test', action='store_true', help='快速测试模式(抽样5只)')
    parser.add_argument('--workers', type=int, default=5, help='并发数(默认5)')
    parser.add_argument('--max-count', type=int, default=50, help='每只最大公告数(默认50)')
    parser.add_argument('--output', type=str, default='./all_reits_announcements', 
                       help='输出目录')
    
    args = parser.parse_args()
    
    if args.test:
        quick_test_sample()
    else:
        batch_crawl_all(
            max_workers=args.workers,
            max_count=args.max_count,
            output_dir=args.output
        )
