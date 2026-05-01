#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
巨潮资讯网(CNInfo) REIT基金公告爬虫
版本：2.0.0 - 修复版，支持REIT基金公告爬取
作者：REITs数据中心

使用方式：
    python cninfo_crawler.py --keyword 180101 --max-count 30 --output-dir ./announcements --json-output

支持的REIT基金代码格式：
    - 180XXX (深交所REIT，如180101博时蛇口产业园REIT)
    - 508XXX 需要映射到对应的180XXX代码
"""

import requests
import json
import time
import os
import sys
import argparse
import re
from datetime import datetime, timedelta
import logging
logger = logging.getLogger(__name__)


class CNInfoCrawler:
    """巨潮资讯网REIT基金爬虫"""
    
    VERSION = "2.0.0"
    
    # REIT代码映射表 - 支持全部79只REIT (2025年12月更新)
    # 数据来源: D:\kimi\reitssys\datadaily 日线数据文件
    REIT_CODE_MAPPING = {
        # 上交所REIT (508XXX) - 58只
        '508000': '508000',  # 华安张江产业园REIT
        '508001': '508001',  # 浙商沪杭甬REIT
        '508002': '508002',  # 华安百联消费REIT
        '508003': '508003',  # 中航首钢生物质REIT
        '508005': '508005',  # 华夏首创水务REIT
        '508006': '508006',  # 富国首创水务REIT
        '508007': '508007',  # 中金山东高速REIT
        '508008': '508008',  # 华夏中国交建REIT
        '508009': '508009',  # 中金安徽交控REIT
        '508010': '508010',  # 华夏合肥高新REIT
        '508011': '508011',  # 嘉实物美消费REIT
        '508012': '508012',  # 华夏和达高科REIT
        '508015': '508015',  # 华夏京保REIT
        '508016': '508016',  # 华夏华润有巢REIT
        '508017': '508017',  # 华夏金茂商业REIT
        '508018': '508018',  # 华夏中国交建REIT扩募
        '508019': '508019',  # 中金普洛斯REIT
        '508021': '508021',  # 国泰君安临港REIT
        '508022': '508022',  # 国泰君安东久新经济REIT
        '508026': '508026',  # 嘉实京东仓储REIT
        '508027': '508027',  # 东吴苏园产业REIT
        '508028': '508028',  # 中金厦门安居REIT
        '508029': '508029',  # 华夏北京保障房REIT
        '508031': '508031',  # 富国杭州坡地REIT
        '508033': '508033',  # 鹏华深圳能源REIT
        '508036': '508036',  # 平安广州广河REIT
        '508039': '508039',  # 中金湖北科投REIT
        '508048': '508048',  # 华夏越秀高速REIT
        '508050': '508050',  # 华夏中核清洁能源REIT
        '508055': '508055',  # 中信建投国家电投REIT
        '508056': '508056',  # 中金普洛斯REIT扩募
        '508058': '508058',  # 中金厦门安居REIT扩募
        '508060': '508060',  # 中金武汉REIT
        '508066': '508066',  # 华泰紫金江苏交控REIT
        '508068': '508068',  # 华夏北京保障房REIT扩募
        '508069': '508069',  # 中金山东高速REIT扩募
        '508077': '508077',  # 华夏基金华润有巢REIT扩募
        '508078': '508078',  # 华夏基金深国际REIT
        '508080': '508080',  # 华夏金隅智造工场REIT
        '508082': '508082',  # 嘉实电建清洁能源REIT
        '508084': '508084',  # 华夏首创奥特莱斯REIT
        '508085': '508085',  # 中金印力消费REIT
        '508086': '508086',  # 华夏深国际REIT
        '508087': '508087',  # 中金重庆两江REIT
        '508088': '508088',  # 华夏合肥高新REIT扩募
        '508089': '508089',  # 华夏基金城投宽庭REIT
        '508090': '508090',  # 建信中关村REIT
        '508091': '508091',  # 华夏南京交通REIT
        '508092': '508092',  # 国金铁建重庆渝遂REIT
        '508096': '508096',  # 嘉实京东智能产业园REIT
        '508097': '508097',  # 华夏基金蒙能REIT
        '508098': '508098',  # 易方达广州开发区REIT
        '508099': '508099',  # 建信中关村REIT扩募
        
        # 深交所REIT (180XXX) - 21只
        '180101': '180101',  # 博时蛇口产业园REIT
        '180102': '180102',  # 华夏合肥高新REIT
        '180103': '180103',  # 华夏和达高科REIT
        '180105': '180105',  # 红土创新盐田港REIT
        '180106': '180106',  # 博时招商蛇口REIT
        '180201': '180201',  # 平安广州广河REIT
        '180202': '180202',  # 平安广州广河REIT扩募
        '180203': '180203',  # 华夏越秀高速REIT
        '180301': '180301',  # 红土创新深圳安居REIT
        '180302': '180302',  # 华夏深国际REIT
        '180303': '180303',  # 红土创新盐田港REIT扩募
        '180305': '180305',  # 华夏合肥高新REIT扩募
        '180306': '180306',  # 华夏深国际REIT扩募
        '180401': '180401',  # 鹏华深圳能源REIT
        '180402': '180402',  # 鹏华深圳能源REIT扩募
        '180501': '180501',  # 华夏和达高科REIT扩募
        '180502': '180502',  # 华夏北京保障房REIT
        '180601': '180601',  # 中金普洛斯REIT
        '180602': '180602',  # 中金厦门安居REIT
        '180603': '180603',  # 华夏中国交建REIT
        '180605': '180605',  # 红土创新深圳安居REIT扩募
        '180606': '180606',  # 华夏中国交建REIT扩募
        '180607': '180607',  # 华夏合肥高新REIT扩募2
        '180701': '180701',  # 华夏基金华润有巢REIT
        '180801': '180801',  # 中金普洛斯REIT扩募
        '180901': '180901',  # 华夏北京保障房REIT
    }
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': 'http://www.cninfo.com.cn',
            'Referer': 'http://www.cninfo.com.cn'
        }
        self.session.headers.update(self.headers)
        
        self.search_url = "http://www.cninfo.com.cn/new/information/topSearch/query"
        self.announcement_url = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
        self.download_base = "http://static.cninfo.com.cn/"
        
        self.stats = {'total_found': 0, 'downloaded': 0, 'failed': 0, 'skipped': 0}
    
    def log(self, level, message):
        """输出日志（JSON格式供Java解析）"""
        log_entry = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'level': level,
            'message': message
        }
        if self.verbose or level in ['ERROR', 'WARN', 'INFO']:
            logger.info(json.dumps(log_entry, ensure_ascii=False), flush=True)
    
    def _convert_code(self, code):
        """转换REIT代码（508XXX -> 180XXX）"""
        code = str(code).strip()
        if code in self.REIT_CODE_MAPPING:
            converted = self.REIT_CODE_MAPPING[code]
            self.log('INFO', f'代码转换: {code} -> {converted}')
            return converted
        return code
    
    def search_fund(self, keyword):
        """
        搜索基金，获取orgId
        返回: {'code': '...', 'name': '...', 'orgId': '...'} 或 None
        """
        # 尝试转换代码
        keyword = self._convert_code(keyword)
        
        # 上交所REIT (508XXX) 巨潮搜索接口不支持，直接构造
        if keyword.startswith('508'):
            self.log('INFO', f'上交所REIT直接构造: {keyword}')
            return {
                'code': keyword,
                'name': f'上海REIT-{keyword}',
                'orgId': '',
                'market': 'sh'
            }
        
        self.log('INFO', f'搜索基金: {keyword}')
        params = {'keyWord': keyword, 'maxNum': '10'}
        
        try:
            resp = self.session.post(self.search_url, data=params, timeout=10)
            data = resp.json()
            
            if isinstance(data, list):
                for item in data:
                    if item.get('type') == 'fund':
                        result = {
                            'code': item.get('code'),
                            'name': item.get('zwjc'),
                            'orgId': item.get('orgId'),
                            'category': item.get('category')
                        }
                        self.log('INFO', f"找到基金: {result['code']} - {result['name']}")
                        return result
            
            self.log('WARN', f'未找到基金: {keyword}')
            return None
            
        except (requests.RequestException, json.JSONDecodeError, KeyError, ValueError) as e:
            self.log('ERROR', f'搜索失败: {e}')
            return None
    
    def get_announcements(self, fund_code, org_id, start_date=None, end_date=None, page_size=100):
        """
        获取公告列表
        关键：不使用plate参数，column使用'fund'
        """
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        self.log('INFO', f'获取公告: {fund_code} ({start_date} ~ {end_date})')
        
        params = {
            'pageNum': '1',
            'pageSize': str(page_size),
            'tabName': 'fulltext',
            'column': 'fund',  # 基金类型
            'stock': f'{fund_code},{org_id}',
            'seDate': f'{start_date}~{end_date}',
            'sortType': 'desc'
        }
        
        announcements = []
        page = 1
        max_pages = 10
        
        while page <= max_pages:
            params['pageNum'] = str(page)
            
            try:
                resp = self.session.post(self.announcement_url, data=params, headers=self.headers, timeout=15)
                data = resp.json()
                
                if not data.get('announcements'):
                    break
                
                for item in data['announcements']:
                    announcements.append({
                        'title': item.get('announcementTitle', ''),
                        'time': item.get('announcementTime', ''),
                        'pdf_url': f"{self.download_base}{item.get('adjunctUrl', '')}",
                        'adjunctUrl': item.get('adjunctUrl', ''),
                        'stock_code': fund_code
                    })
                
                total = data.get('totalRecordNum') or 0
                current_page_anns = data.get('announcements') or []
                self.log('DEBUG', f'第{page}页: 获取 {len(current_page_anns)} 条，累计 {len(announcements)}/{total}')
                
                if page * page_size >= total or len(current_page_anns) < page_size:
                    break
                
                page += 1
                time.sleep(0.5)
                
            except (requests.RequestException, json.JSONDecodeError, KeyError, ValueError) as e:
                self.log('ERROR', f'获取第{page}页失败: {e}')
                break
        
        self.stats['total_found'] = len(announcements)
        self.log('INFO', f'公告获取完成: 共 {len(announcements)} 条')
        return announcements
    
    def download_pdf(self, announcement, save_dir):
        """下载PDF文件"""
        url = announcement.get('pdf_url')
        if not url or not announcement.get('adjunctUrl'):
            return {'success': False, 'error': '无效的PDF链接'}
        
        # 生成文件名
        time_str = announcement.get('time', '')
        if isinstance(time_str, str) and len(time_str) > 10:
            time_str = time_str[:10].replace('-', '')
        elif isinstance(time_str, int):
            # 时间戳格式，转换为日期字符串
            from datetime import datetime
            time_str = datetime.fromtimestamp(time_str/1000).strftime('%Y%m%d')
        else:
            time_str = ''
        
        title = re.sub(r'[\\/*?:"<>|]', '_', announcement.get('title', 'unnamed'))
        filename = f"{time_str}_{title}.pdf"[:150]  # 限制文件名长度
        filepath = os.path.join(save_dir, filename)
        
        try:
            os.makedirs(save_dir, exist_ok=True)
            resp = self.session.get(url, timeout=30)
            
            with open(filepath, 'wb') as f:
                f.write(resp.content)
            
            self.stats['downloaded'] += 1
            self.log('INFO', f'下载成功: {filename}')
            return {'success': True, 'filepath': filepath, 'filename': filename}
            
        except (OSError, requests.RequestException) as e:
            self.stats['failed'] += 1
            self.log('ERROR', f'下载失败: {filename} - {e}')
            return {'success': False, 'error': '下载失败，请检查网络和磁盘空间'}
    
    def batch_crawl(self, keyword, start_date=None, end_date=None, max_count=50, 
                    output_dir='./announcements', task_id=None):
        """
        批量爬取入口
        """
        result = {
            'success': False,
            'task_id': task_id,
            'keyword': keyword,
            'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'end_time': None,
            'duration_seconds': 0,
            'fund_info': None,
            'announcements': [],
            'downloads': [],
            'stats': {},
            'error': None
        }
        
        try:
            start_dt = datetime.now()
            
            # 1. 搜索基金（深交所180XXX）或直接构造（上交所508XXX）
            fund_info = self.search_fund(keyword)
            
            if not fund_info and keyword.startswith('508'):
                # 上交所REIT直接构造信息（公告接口支持508XXX直接查询）
                fund_info = {
                    'code': keyword,
                    'name': f'上海REIT-{keyword}',
                    'orgId': '',  # 508XXX不需要orgId
                    'market': 'sh'
                }
                self.log('INFO', f'上交所REIT直接查询: {keyword}')
            
            if not fund_info:
                result['error'] = '未找到相关基金'
                return result
            
            result['fund_info'] = fund_info
            
            # 2. 获取公告列表
            anns = self.get_announcements(
                fund_info['code'], 
                fund_info.get('orgId', ''),  # 508XXX可能为空
                start_date, 
                end_date, 
                page_size=min(max_count, 100)
            )
            result['announcements'] = anns[:max_count]
            
            # 3. 下载PDF
            save_dir = os.path.join(output_dir, f"{fund_info['code']}_{fund_info['name']}_公告")
            downloads = []
            
            for ann in anns[:max_count]:
                dl_result = self.download_pdf(ann, save_dir)
                downloads.append({
                    'title': ann['title'],
                    'time': ann['time'],
                    'result': dl_result
                })
            
            result['downloads'] = downloads
            result['stats'] = self.stats
            result['success'] = True
            
            # 自动同步到数据库
            try:
                from crawlers.cninfo_db_sync import save_announcements_to_db
                db_result = save_announcements_to_db(result['announcements'], fund_info['code'])
                result['db_sync'] = db_result
            except (ImportError, RuntimeError, ValueError) as e:
                self.log('WARN', f'数据库同步失败: {e}')
                result['db_sync'] = {'error': '数据库同步失败'}
            
            end_dt = datetime.now()
            result['end_time'] = end_dt.strftime('%Y-%m-%d %H:%M:%S')
            result['duration_seconds'] = (end_dt - start_dt).total_seconds()
            
            self.log('INFO', f"爬取完成: {fund_info['code']} - 成功{self.stats['downloaded']}/总计{self.stats['total_found']}")
            
        except (RuntimeError, OSError, ValueError) as e:
            result['error'] = '爬取异常，请查看日志'
            self.log('ERROR', f'爬取异常: {e}')
        
        return result


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description='巨潮资讯网REIT基金公告爬虫')
    parser.add_argument('--keyword', required=True, help='REIT基金代码（如180101, 508000等）')
    parser.add_argument('--start-date', help='起始日期(YYYY-MM-DD)')
    parser.add_argument('--end-date', help='结束日期(YYYY-MM-DD)')
    parser.add_argument('--max-count', type=int, default=50, help='最大下载数量')
    parser.add_argument('--output-dir', default='./announcements', help='输出目录')
    parser.add_argument('--json-output', action='store_true', help='输出JSON格式结果')
    parser.add_argument('--task-id', help='任务ID')
    parser.add_argument('--verbose', action='store_true', help='详细日志')
    
    args = parser.parse_args()
    
    crawler = CNInfoCrawler(verbose=args.verbose)
    result = crawler.batch_crawl(
        keyword=args.keyword,
        start_date=args.start_date,
        end_date=args.end_date,
        max_count=args.max_count,
        output_dir=args.output_dir,
        task_id=args.task_id
    )
    
    if args.json_output:
        # 输出最终结果JSON（供Java解析）
        logger.info(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # 简化输出
        if result['success']:
            logger.info(f"\n✅ 爬取成功!")
            logger.info(f"   基金: {result['fund_info']['name']}")
            logger.info(f"   公告: {len(result['announcements'])} 条")
            logger.info(f"   下载: {result['stats']['downloaded']} 个PDF")
            logger.info(f"   保存: {args.output_dir}")
        else:
            logger.error(f"\n❌ 爬取失败: {result['error']}")
            sys.exit(1)


if __name__ == '__main__':
    main()
