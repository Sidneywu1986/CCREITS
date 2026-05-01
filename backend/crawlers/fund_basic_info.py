#!/usr/bin/env python3
"""
REIT基金基础信息爬虫
抓取规模、成立日期、剩余期限、机构持仓、债务率等静态数据
数据源：东方财富、新浪财经
"""

import requests
import json
import re
import time
from datetime import datetime
from typing import Dict, Optional, List
import os
from core.db import get_conn
import psycopg2
import logging
logger = logging.getLogger(__name__)

# 请求头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Referer': 'https://fund.eastmoney.com/'
}


class REITBasicInfoCrawler:
    """REIT基础信息爬虫"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        
    def get_fund_list(self) -> List[Dict]:
        """从数据库获取所有REIT基金代码"""
        with get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT fund_code, fund_name FROM business.funds ORDER BY fund_code')
            funds = [{'fund_code': row['fund_code'], 'fund_name': row['fund_name']} for row in cursor.fetchall()]
        return funds
    
    def fetch_eastmoney_basic(self, code: str) -> Optional[Dict]:
        """
        从东方财富获取基金基础信息
        """
        try:
            # 东方财富基金详情API
            # 需要将代码转换为东财格式
            if code.startswith('508'):
                # 上交所REIT
                secid = f"1.{code}"
            elif code.startswith('180'):
                # 深交所REIT
                secid = f"0.{code}"
            else:
                return None
            
            # 基金概况接口
            url = f"https://fundf10.eastmoney.com/jbgk_{code}.html"
            
            # 使用正则提取页面数据
            resp = self.session.get(url, timeout=15)
            resp.encoding = 'utf-8'
            
            data = {}
            html = resp.text
            
            # 提取成立日期
            date_match = re.search(r'成立日期[\s\S]*?<td[^>]*>(\d{4}-\d{2}-\d{2})</td>', html)
            if date_match:
                data['listing_date'] = date_match.group(1)
            
            # 提取基金规模
            scale_match = re.search(r'资产规模[\s\S]*?<td[^>]*>([\d.]+)\s*亿元', html)
            if scale_match:
                data['scale'] = float(scale_match.group(1))
            
            # 提取基金管理人
            manager_match = re.search(r'基金管理人[\s\S]*?<td[^>]*>([^<]+)</td>', html)
            if manager_match:
                data['manager'] = manager_match.group(1).strip()
            
            # 提取托管人
            custodian_match = re.search(r'基金托管人[\s\S]*?<td[^>]*>([^<]+)</td>', html)
            if custodian_match:
                data['custodian'] = custodian_match.group(1).strip()
            
            return data if data else None
            
        except (requests.RequestException, ValueError, TypeError) as e:
            logger.error(f'[东财] 获取{code}基础信息失败: {e}')
            return None
    
    def fetch_eastmoney_detail_api(self, code: str) -> Optional[Dict]:
        """
        从东方财富API获取更详细的数据
        """
        try:
            # 基金详情API
            url = f"https://fundgz.1234567.com.cn/js/{code}.js"
            resp = self.session.get(url, timeout=10)
            
            # 解析JSONP
            match = re.search(r'jsonpgz\((.+?)\);', resp.text)
            if match:
                data = json.loads(match.group(1))
                return {
                    'name': data.get('name'),
                    'nav': float(data['dwjz']) if 'dwjz' in data else None,
                    'nav_date': data.get('jzrq')
                }
            return None
        except (requests.RequestException, json.JSONDecodeError, ValueError, TypeError) as e:
            logger.error(f'[东财API] 获取{code}详情失败: {e}')
            return None
    
    def fetch_sina_basic(self, code: str) -> Optional[Dict]:
        """
        从新浪财经获取基础信息
        """
        try:
            # 新浪基金API
            url = f"https://stock.finance.sina.com.cn/fund/api/jsonp.php/FundRevalCallback.FundRevalCallback/fund_nav/{code}"
            resp = self.session.get(url, timeout=10)
            
            # 解析JSONP
            match = re.search(r'\((.+?)\);', resp.text)
            if match:
                data = json.loads(match.group(1))
                if data and len(data) > 0:
                    fund = data[0]
                    return {
                        'nav': float(fund.get('value', 0)) if fund.get('value') else None,
                        'nav_date': fund.get('date'),
                        'name': fund.get('name')
                    }
            return None
        except (requests.RequestException, json.JSONDecodeError, ValueError, TypeError) as e:
            logger.error(f'[新浪] 获取{code}基础信息失败: {e}')
            return None
    
    def fetch_cninfo_basic(self, code: str) -> Optional[Dict]:
        """
        从巨潮资讯网获取基础信息（招募书数据）
        """
        try:
            # 巨潮搜索API
            url = "http://www.cninfo.com.cn/new/information/topSearch/query"
            payload = {
                'keyWord': code,
                'maxNum': 10
            }
            
            resp = self.session.post(url, data=payload, timeout=10)
            data = resp.json()
            
            if data.get('data') and len(data['data']) > 0:
                item = data['data'][0]
                return {
                    'name': item.get('secName'),
                    'org_id': item.get('orgId'),
                    'category': item.get('category')
                }
            return None
        except (requests.RequestException, json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f'[巨潮] 获取{code}基础信息失败: {e}')
            return None
    
    def calculate_remaining_years(self, listing_date: str) -> Optional[str]:
        """
        根据成立日期计算剩余期限
        REITs通常有固定的存续期（如20年、50年、99年）
        """
        if not listing_date:
            return None
        
        try:
            # 解析成立日期
            start = datetime.strptime(listing_date, '%Y-%m-%d')
            now = datetime.now()
            
            # REITs默认存续期通常是20年或50年
            # 这里我们假设为20年，实际应从招募书获取
            total_years = 20
            
            # 计算已存续年数
            elapsed_days = (now - start).days
            elapsed_years = elapsed_days / 365.25
            
            remaining = total_years - elapsed_years
            if remaining > 0:
                return f"{remaining:.1f}年"
            else:
                return "即将到期"
                
        except (ValueError, TypeError) as e:
            logger.error(f'计算剩余期限失败: {e}')
            return None
    
    def merge_data(self, code: str, data_sources: List[Optional[Dict]]) -> Dict:
        """
        合并多个数据源的数据，优先使用有值的数据
        """
        merged = {
            'code': code,
            'scale': None,
            'listing_date': None,
            'remaining_years': None,
            'manager': None,
            'nav': None,
            'debt_ratio': None,
            'institution_hold': None,
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 合并数据
        for data in data_sources:
            if not data:
                continue
            for key, value in data.items():
                if value is not None and merged.get(key) is None:
                    merged[key] = value
        
        # 计算剩余期限
        if merged['listing_date'] and not merged['remaining_years']:
            merged['remaining_years'] = self.calculate_remaining_years(merged['listing_date'])
        
        return merged
    
    def update_database(self, fund_data: Dict) -> bool:
        """
        更新数据库
        """
        try:
            with get_conn() as conn:
                cursor = conn.cursor()
                
                # 构建更新SQL - 映射字段名到数据库列名
                field_mapping = {
                    'scale': 'total_shares',  # 规模(亿) -> total_shares
                    'listing_date': 'ipo_date',  # 成立日期 -> ipo_date
                    'manager': 'manager',
                    'nav': 'nav',
                    'remaining_years': 'asset_type',  # 临时存储剩余期限
                }
                
                fields = []
                values = []
                
                for source_key, db_column in field_mapping.items():
                    if fund_data.get(source_key) is not None:
                        fields.append(f"{db_column} = %s")
                        values.append(fund_data[source_key])
                
                if not fields:
                    logger.info(f"[{fund_data['code']}] 无数据可更新")
                    return False
                
                # 添加updated_at
                fields.append("updated_at = %s")
                values.append(fund_data['updated_at'])
                
                # 添加WHERE条件 - 使用fund_code
                values.append(fund_data['code'])
                
                sql = f"UPDATE business.funds SET {', '.join(fields)} WHERE fund_code = %s"
                cursor.execute(sql, values)
                rowcount = cursor.rowcount
                conn.commit()
            
            return rowcount > 0
            
        except psycopg2.Error as e:
            logger.error(f"[DB] 更新{fund_data['code']}失败: {e}")
            return False
    
    def crawl_single(self, fund_code: str, fund_name: str) -> Dict:
        """
        爬取单只REIT的基础信息
        """
        logger.info(f"\n[{fund_code}] {fund_name}")
        logger.info("-" * 50)
        
        # 从多个数据源获取数据
        eastmoney_data = self.fetch_eastmoney_basic(fund_code)
        eastmoney_api_data = self.fetch_eastmoney_detail_api(fund_code)
        sina_data = self.fetch_sina_basic(fund_code)
        cninfo_data = self.fetch_cninfo_basic(fund_code)
        
        # 合并数据
        merged = self.merge_data(fund_code, [eastmoney_data, eastmoney_api_data, sina_data, cninfo_data])
        
        # 打印获取到的数据
        logger.info(f"  规模: {merged.get('scale', '--')}亿")
        logger.info(f"  成立日期: {merged.get('listing_date', '--')}")
        logger.info(f"  剩余期限: {merged.get('remaining_years', '--')}")
        logger.info(f"  管理人: {merged.get('manager', '--')}")
        logger.info(f"  净值: {merged.get('nav', '--')}")
        
        # 更新数据库
        if self.update_database(merged):
            logger.info(f"  [OK] 数据库更新成功")
        else:
            logger.warning(f"  [WARN] 数据库无更新")
        
        return merged
    
    def crawl_all(self, limit: int = None):
        """
        爬取所有REIT的基础信息
        """
        funds = self.get_fund_list()
        logger.info(f"\n开始爬取{len(funds)}只REIT的基础信息...")
        logger.info("=" * 60)
        
        success_count = 0
        fail_count = 0
        
        for i, fund in enumerate(funds):
            if limit and i >= limit:
                break
            
            try:
                self.crawl_single(fund['fund_code'], fund['fund_name'])
                success_count += 1
            except Exception as e:
                logger.error(f"  [ERROR] 爬取失败: {e}")
                fail_count += 1
            
            # 延时，避免请求过快
            if i < len(funds) - 1:
                time.sleep(0.5)
        
        logger.info("\n" + "=" * 60)
        logger.error(f"爬取完成: 成功{success_count}, 失败{fail_count}, 总计{success_count + fail_count}")
        
        return {'success': success_count, 'failed': fail_count}


def main():
    """主入口"""
    crawler = REITBasicInfoCrawler()
    
    import argparse
    parser = argparse.ArgumentParser(description='REIT基础信息爬虫')
    parser.add_argument('--code', help='单个基金代码')
    parser.add_argument('--limit', type=int, help='限制数量')
    
    args = parser.parse_args()
    
    if args.code:
        # 爬取单只
        crawler.crawl_single(args.code, '')
    else:
        # 爬取全部
        crawler.crawl_all(limit=args.limit)


if __name__ == '__main__':
    main()
