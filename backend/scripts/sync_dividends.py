#!/usr/bin/env python3
"""
REITs 分红数据同步入口脚本
用法:
  python sync_dividends.py              # 默认从 announcements 表同步
  python sync_dividends.py --crawler    # 同时运行交易所爬虫（较慢，可能受反爬限制）
  python sync_dividends.py --all        # 全量爬取全部79只基金（耗时约5-10分钟）
"""
import sys
import os
import argparse
import logging
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

def sync_from_announcements():
    """从 announcements 表中的分红公告同步"""
    from scripts.sync_dividends_from_announcements import sync_dividends
    return sync_dividends()

def run_crawler(fund_codes=None):
    """运行交易所爬虫获取新分红公告"""
    import subprocess
    cmd = [sys.executable, os.path.join(BASE_DIR, 'crawlers', 'dividend_crawler.py')]
    if fund_codes:
        cmd.extend(['--codes'] + fund_codes)
    else:
        cmd.append('--all')
    
    logger.info("=== 启动交易所分红爬虫 ===")
    result = subprocess.run(cmd, capture_output=True, text=True)
    logger.info(result.stdout)
    if result.stderr:
        logger.info("[STDERR]", result.stderr)
    return result.returncode == 0

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='REITs分红数据同步')
    parser.add_argument('--crawler', action='store_true', help='同时运行交易所爬虫')
    parser.add_argument('--all', action='store_true', help='全量爬取全部79只基金')
    parser.add_argument('--codes', nargs='+', help='指定基金代码列表')
    args = parser.parse_args()
    
    logger.info("=" * 50)
    logger.info("REITs 分红数据同步")
    logger.info("=" * 50)
    
    # 1. 从 announcements 同步（主要来源）
    count = sync_from_announcements()
    logger.info(f"\n[1/2] 公告同步完成: 新增 {count} 条记录")
    
    # 2. 可选：运行交易所爬虫
    if args.crawler or args.all or args.codes:
        codes = None
        if args.codes:
            codes = args.codes
        elif not args.all:
            # 默认爬取部分热门基金
            codes = ['508000', '508001', '180101', '180201', '180301', '180501']
        
        success = run_crawler(codes if not args.all else None)
        logger.error(f"\n[2/2] 交易所爬虫: {'成功' if success else '失败'}")
    
    logger.info("\n同步完成！")
    logger.info("提示: 可加入 Windows 任务计划程序实现定时自动更新")
    logger.info("  命令: python " + os.path.abspath(__file__))
