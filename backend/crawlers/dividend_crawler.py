#!/usr/bin/env python3
"""
REITs 分红公告爬虫（沪深交易所双通道）
避开巨潮盲区，直连交易所接口
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict
from abc import ABC, abstractmethod
import time
import re
import os
import sys
from core.db import get_conn
import logging
logger = logging.getLogger(__name__)

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class BaseREITsExchangeCrawler(ABC):
    """交易所 REITs 爬虫抽象基类"""
    
    def __init__(self):
        self.session = requests.Session()
        self.dividend_keywords = [
            '收益分配', '分红公告', '权益分派', '现金红利', 
            '每份派发现金', '权益登记日', '除息日', '红利发放'
        ]
    
    @abstractmethod
    def fetch_dividend_announcements(self, fund_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取分红公告列表"""
        pass
    
    def _extract_dividend_from_title(self, title: str) -> Dict:
        """从标题提取分红关键信息"""
        info = {
            'dividend_per_share': None,
            'record_date': None,
            'ex_dividend_date': None,
            'is_dividend': any(kw in title for kw in self.dividend_keywords)
        }
        
        # 提取金额（每份 X 元 或 每10份 X 元）
        amount_match = re.search(r'每(?:份|10份).*?([0-9]+\.[0-9]+)\s*元', title)
        if amount_match:
            amount = float(amount_match.group(1))
            if '每10份' in title:
                amount = round(amount / 10, 4)
            info['dividend_per_share'] = amount
        
        # 提取日期（权益登记日/除息日）
        date_matches = re.findall(r'(20\d{2}年\d{1,2}月\d{1,2}日)', title)
        if date_matches:
            if '登记' in title or '权益' in title:
                info['record_date'] = date_matches[0]
            if '除息' in title or '除权' in title:
                info['ex_dividend_date'] = date_matches[0]
                
        return info


class SHREITsDividendCrawler(BaseREITsExchangeCrawler):
    """上交所 REITs 分红爬虫（508XXX 系列）"""
    
    def __init__(self):
        super().__init__()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://www.sse.com.cn/assortment/fund/reits/home/',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
        })
        self.base_url = "http://query.sse.com.cn/commonQuery.do"
    
    def fetch_dividend_announcements(self, fund_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取上交所 REITs 分红公告"""
        if not start_date:
            start_date = (datetime.now() - timedelta(days=180)).strftime('%Y%m%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
            
        params = {
            'sqlId': 'FUND_SSE_SCSJ_CJGK_ZQSL',
            'productId': fund_code,
            'startDate': start_date.replace('-', ''),
            'endDate': end_date.replace('-', ''),
            'pageHelp.pageSize': 25,
            'pageHelp.pageNo': 1,
            'pageHelp.beginPage': 1,
            'pageHelp.endPage': 5,
            '_': int(time.time() * 1000)
        }
        
        all_items = []
        page = 1
        
        try:
            while True:
                params['pageHelp.pageNo'] = page
                params['pageHelp.beginPage'] = page
                params['pageHelp.endPage'] = page + 1
                
                resp = self.session.get(self.base_url, params=params, timeout=15)
                data = resp.json()
                
                if not data.get('result'):
                    break
                
                for item in data['result']:
                    title = item.get('bulletin_TITLE', '').strip()
                    if not any(kw in title for kw in self.dividend_keywords):
                        continue
                    
                    div_info = self._extract_dividend_from_title(title)
                    
                    all_items.append({
                        'fund_code': fund_code,
                        'exchange': 'SSE',
                        'announcement_id': item.get('bulletin_ID'),
                        'title': title,
                        'publish_date': item.get('bulletin_YMD'),
                        'publish_time': item.get('bulletin_WD'),
                        'url': f"http://www.sse.com.cn{item.get('bulletin_URL', '')}" if item.get('bulletin_URL') else None,
                        'dividend_per_share': div_info['dividend_per_share'],
                        'record_date': div_info['record_date'],
                        'ex_dividend_date': div_info['ex_dividend_date'],
                        'source': 'sse_direct',
                        'crawled_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                
                total_pages = data.get('pageHelp', {}).get('pageCount', 1)
                if page >= total_pages or len(data['result']) < 25:
                    break
                    
                page += 1
                time.sleep(0.5)
                
        except Exception as e:
            logger.error(f"[ERROR] 上交所 {fund_code} 抓取失败: {e}")
            
        return pd.DataFrame(all_items)


class SZREITsDividendCrawler(BaseREITsExchangeCrawler):
    """深交所 REITs 分红爬虫（180XXX 系列）"""
    
    def __init__(self):
        super().__init__()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://www.szse.cn/market/fund/reits/bulletin/',
            'Accept': 'application/json, text/plain, */*',
        })
        self.base_url = "http://www.szse.cn/api/disc/announcement/list"
    
    def fetch_dividend_announcements(self, fund_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取深交所 REITs 分红公告"""
        if not start_date:
            start_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        all_items = []
        page = 1
        page_size = 30
        
        try:
            while True:
                params = {
                    'channelCode': 'fund',
                    'pageSize': page_size,
                    'pageNum': page,
                    'keywords': fund_code,
                    'startTime': start_date,
                    'endTime': end_date,
                }
                
                resp = self.session.get(self.base_url, params=params, timeout=15)
                data = resp.json()
                
                if not data.get('data') or not data['data']:
                    break
                
                announcements = data['data']
                
                for item in announcements:
                    title = item.get('title', '').strip()
                    if not any(kw in title for kw in self.dividend_keywords):
                        continue
                    
                    div_info = self._extract_dividend_from_title(title)
                    
                    all_items.append({
                        'fund_code': fund_code,
                        'exchange': 'SZSE',
                        'announcement_id': item.get('id'),
                        'title': title,
                        'publish_date': item.get('publishTime', '').split()[0] if item.get('publishTime') else None,
                        'publish_time': item.get('publishTime'),
                        'url': item.get('url'),
                        'dividend_per_share': div_info['dividend_per_share'],
                        'record_date': div_info['record_date'],
                        'ex_dividend_date': div_info['ex_dividend_date'],
                        'source': 'szse_direct',
                        'crawled_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                
                if len(announcements) < page_size:
                    break
                    
                page += 1
                time.sleep(0.8)
                
        except Exception as e:
            logger.error(f"[ERROR] 深交所 {fund_code} 抓取失败: {e}")
            
        return pd.DataFrame(all_items)


class REITsDividendManager:
    """REITs 分红统一管理器"""
    
    def __init__(self):
        self.sse_crawler = SHREITsDividendCrawler()
        self.szse_crawler = SZREITsDividendCrawler()
        self.code_pattern_sse = re.compile(r'^508\d{3}$')
        self.code_pattern_szse = re.compile(r'^180\d{3}$')
        

    
    def get_dividends(self, fund_codes: List[str], start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """批量获取多只 REITs 分红信息"""
        all_results = []
        
        for code in fund_codes:
            code = str(code).strip()
            logger.info(f"[{datetime.now().strftime('%H:%M:%S')}] 处理 {code}...")
            
            try:
                if self.code_pattern_sse.match(code):
                    df = self.sse_crawler.fetch_dividend_announcements(code, start_date, end_date)
                elif self.code_pattern_szse.match(code):
                    df = self.szse_crawler.fetch_dividend_announcements(code, start_date, end_date)
                else:
                    logger.info(f"[WARN] {code} 非标准 REITs 代码")
                    continue
                
                if not df.empty:
                    all_results.append(df)
                    logger.info(f"  └─ 获取 {len(df)} 条分红公告")
                    
                    # 立即保存到数据库
                    self.save_to_db(df)
                else:
                    logger.info(f"  └─ 无分红公告")
                    
            except Exception as e:
                logger.info(f"[ERROR] 处理 {code} 异常: {e}")
            
            time.sleep(1.5)
        
        if all_results:
            combined = pd.concat(all_results, ignore_index=True)
            combined = combined.sort_values('publish_date', ascending=False)
            return combined
        return pd.DataFrame()
    
    def save_to_db(self, df: pd.DataFrame):
        """保存分红公告到数据库（announcements + dividends 双写）"""
        if df.empty:
            return
        
        with get_conn() as conn:
            cursor = conn.cursor()
            
            for _, row in df.iterrows():
                try:
                    # 1. 保存到 announcements
                    cursor.execute("""
                        INSERT INTO business.announcements 
                        (fund_code, title, category, publish_date, source_url, exchange, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (fund_code, title, publish_date) DO UPDATE SET
                            category = EXCLUDED.category,
                            source_url = EXCLUDED.source_url,
                            exchange = EXCLUDED.exchange,
                            created_at = EXCLUDED.created_at
                    """, (
                        row['fund_code'],
                        row['title'],
                        'dividend',
                        row['publish_date'],
                        row['url'],
                        row['exchange']
                    ))
                    
                    # 2. 如果解析出了分红金额，同时写入 dividends 表
                    amount = row.get('dividend_per_share')
                    if amount and amount > 0:
                        # 尝试从标题提取日期
                        ex_date = row.get('ex_dividend_date')
                        record_date = row.get('record_date')
                        pub_date = row.get('publish_date', '')
                        
                        # 日期标准化
                        def normalize_date(d):
                            if not d:
                                return None
                            d = str(d).replace('/', '-').replace('.', '-')
                            if len(d) == 8 and d.isdigit():
                                return f"{d[:4]}-{d[4:6]}-{d[6:]}"
                            return d if len(d) >= 8 else None
                        
                        dividend_date = normalize_date(ex_date) or normalize_date(record_date) or normalize_date(pub_date)
                        if dividend_date:
                            cursor.execute("""
                                INSERT INTO business.dividends 
                                (fund_code, dividend_date, dividend_amount, record_date, ex_dividend_date, created_at)
                                VALUES (%s, %s, %s, %s, %s, NOW())
                                ON CONFLICT DO NOTHING
                            """, (
                                row['fund_code'],
                                dividend_date,
                                amount,
                                normalize_date(record_date),
                                normalize_date(ex_date)
                            ))
                except Exception as e:
                    logger.error(f"[ERROR] 保存失败 {row['fund_code']}: {e}")
        
        logger.info(f"  └─ 保存到数据库")


def main():
    """主函数 - 从命令行参数获取基金代码"""
    import argparse
    
    parser = argparse.ArgumentParser(description='REITs分红公告爬虫')
    parser.add_argument('--codes', nargs='+', help='基金代码列表（如508000 180101）')
    parser.add_argument('--start-date', help='开始日期（YYYY-MM-DD）')
    parser.add_argument('--end-date', help='结束日期（YYYY-MM-DD）')
    parser.add_argument('--all', action='store_true', help='爬取全部79只REITs')
    
    args = parser.parse_args()
    
    manager = REITsDividendManager()
    
    if args.all:
        # 全部79只REITs代码
        codes = (
            ['508{:03d}'.format(i) for i in range(0, 100)] +
            ['180{:03d}'.format(i) for i in range(100, 1000)]
        )
        # 过滤掉无效代码（实际存在的）
        codes = [c for c in codes if c not in ['180503', '508020']]  # 待上市
    elif args.codes:
        codes = args.codes
    else:
        # 测试代码
        codes = ['508056', '508000', '180101', '180201']
    
    logger.info(f"=== REITs分红公告爬虫 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ===")
    logger.info(f"共 {len(codes)} 只基金\n")
    
    results = manager.get_dividends(
        fund_codes=codes,
        start_date=args.start_date,
        end_date=args.end_date
    )
    
    if not results.empty:
        logger.info(f"\n=== 完成！共获取 {len(results)} 条分红公告 ===")
        logger.info(results[['fund_code', 'exchange', 'publish_date', 'title', 'dividend_per_share']].head(10))
    else:
        logger.info("\n未获取到数据")


if __name__ == "__main__":
    main()
