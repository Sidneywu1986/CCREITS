#!/usr/bin/env python3
"""
CNInfo公告数据自动同步到数据库
含：去重、非REITs过滤、AI辅助分类、PDF有效性校验
"""

import re
import os
import sys
import requests
import hashlib
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.db import get_conn

# REITs 名称特征（用于识别真正的REITs公告）
REIT_NAME_PATTERNS = [
    'REIT', '不动产', '基础设施', '封闭式', '产业园', '物流', '仓储',
    '保障房', '安居房', '租赁住房', '有巢', '公募', '科投', '高速', '能源',
    '光伏', '风能', '水利', '环保', '生态', '环卫', '垃圾', '发电',
    '高速公路', '收费公路', '轨道交通', '地铁', '铁路', '港口', '机场',
    '数据中心', '云基地', '清洁能源', '天然气', '供热', '供水', '污水处理',
    '产业园区', '工业园', '商务', '办公', '酒店', '商场', '超市', '便利店',
    '消费', '零售', '养老', '医疗', '健康', '文旅', '旅游', '酒店', '影院'
]

# 非REITs关键词（直接标记为可疑）
SUSPICIOUS_KEYWORDS = [
    '股票代码', 'A股', 'B股', 'H股', '主板', '创业板', '科创板',
    '上证所股票', '深交所股票', '上市公告', '首次公开发行',
    'IPO', '新股', '打新', '申购', '配股', '增发', '可转债',
    '普通股票', '公司债券', '企业债', '金融债',
    '开放式指数证券',  # 开放式指数基金不是REITs
    'ETF', '交易型开放式', 'ETF联接', 'FOF', '基金中基金'
]


def is_reits_announcement(title):
    """判断是否为真正的REITs公告"""
    title_upper = title.upper()

    # 排除明显非REITs
    for kw in SUSPICIOUS_KEYWORDS:
        if kw in title:
            return False

    # REITs名称特征必须出现至少一个
    for pattern in REIT_NAME_PATTERNS:
        if pattern in title:
            return True

    return False


def classify_announcement(title):
    """自动分类公告（关键词版）"""
    title_lower = title.lower()

    # 分红类
    if any(kw in title for kw in ['分红', '收益分配', '红利', '派息', '分红公告书', '分配方案']):
        return 'dividend'

    # 运营类
    if any(kw in title for kw in ['运营', '经营', '现金流', '出租率', 'occupancy', '招募说明书更新', '资产管理', '运营情况']):
        return 'operation'

    # 财务类
    if any(kw in title for kw in ['年报', '中报', '季报', '年度报告', '中期报告', '季度报告', '审计', '财务报告', '会计', '利润', '营收']):
        return 'financial'

    # 询价类
    if any(kw in title for kw in ['询价', '定价', '发售', '认购', '扩募', '募集', '申购', '初始']):
        return 'inquiry'

    # 上市类
    if any(kw in title for kw in ['上市', '挂牌', '交易', '上市首日', '上市仪式']):
        return 'listing'

    return 'other'


def check_pdf_validity(pdf_url):
    """校验PDF是否有效（HEAD请求）"""
    try:
        if not pdf_url or pdf_url == 'None':
            return False
        resp = requests.head(pdf_url, timeout=10, allow_redirects=True)
        if resp.status_code == 200:
            content_type = resp.headers.get('content-type', '')
            if 'pdf' in content_type.lower() or resp.headers.get('content-length', 0) > 1000:
                return True
        return False
    except:
        return False


def save_announcements_to_db(announcements, fund_code):
    """
    将公告保存到数据库（含去重/过滤/校验）

    Args:
        announcements: 公告列表，每项包含title, time, pdf_url, adjunctUrl
        fund_code: 基金代码

    Returns:
        dict: 保存统计信息
    """
    if not announcements:
        return {'inserted': 0, 'skipped': 0, 'filtered': 0, 'invalid_pdf': 0, 'error': None}

    result = {'inserted': 0, 'skipped': 0, 'filtered': 0, 'invalid_pdf': 0, 'error': None}

    try:
        with get_conn() as conn:
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
                        publish_date = datetime.fromtimestamp(publish_time / 1000).strftime('%Y-%m-%d')
                    elif isinstance(publish_time, str) and len(publish_time) >= 10:
                        publish_date = publish_time[:10]
                    else:
                        publish_date = datetime.now().strftime('%Y-%m-%d')

                    # ========== 1. 非REITs过滤 ==========
                    if not is_reits_announcement(title):
                        # 标记为可疑但不删除，留人工审核
                        cursor.execute('''
                            SELECT id FROM business.announcements
                            WHERE fund_code = %s AND title = %s AND publish_date = %s
                        ''', (fund_code, title, publish_date))

                        if cursor.fetchone():
                            result['skipped'] += 1
                        else:
                            # 可疑公告，标记并入库
                            category = classify_announcement(title)
                            content_hash = hashlib.md5(f"{fund_code}:{publish_date}:{title}".encode()).hexdigest()
                            cursor.execute('''
                                INSERT INTO business.announcements
                                (fund_code, title, category, publish_date, source_url, pdf_url, exchange, confidence, content_hash)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (content_hash) DO NOTHING
                            ''', (
                                fund_code, title, category, publish_date,
                                cninfo_search_url, pdf_url, exchange,
                                60, content_hash
                            ))
                            if cursor.rowcount > 0:
                                result['inserted'] += 1
                        continue

                    # ========== 2. PDF有效性校验 ==========
                    pdf_valid = check_pdf_validity(pdf_url)

                    # ========== 3. 分类 ==========
                    category = classify_announcement(title)

                    # ========== 4. 去重检查 ==========
                    cursor.execute('''
                        SELECT id FROM business.announcements
                        WHERE fund_code = %s AND title = %s AND publish_date = %s
                    ''', (fund_code, title, publish_date))

                    if cursor.fetchone():
                        result['skipped'] += 1
                        continue

                    # 插入数据
                    content_hash = hashlib.md5(f"{fund_code}:{publish_date}:{title}".encode()).hexdigest()
                    cursor.execute('''
                        INSERT INTO business.announcements
                        (fund_code, title, category, publish_date, source_url, pdf_url, exchange, confidence, content_hash)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (content_hash) DO NOTHING
                    ''', (
                        fund_code,
                        title,
                        category,
                        publish_date,
                        cninfo_search_url,
                        pdf_url,
                        exchange,
                        90 if pdf_valid else 70,
                        content_hash
                    ))

                    if not pdf_valid:
                        result['invalid_pdf'] += 1

                    result['inserted'] += 1

                except Exception as e:
                    print(f'[DB] 保存单条公告失败: {e}')
                    continue

            conn.commit()
            print(f'[DB] 同步完成: 新增{result["inserted"]} | 跳过{result["skipped"]} | 可疑{result["filtered"]} | PDF无效{result["invalid_pdf"]}')

    except Exception as e:
        result['error'] = str(e)
        print(f'[DB] 数据库操作失败: {e}')

    return result


def get_exchange(code):
    """根据代码判断交易所"""
    if code.startswith('508'):
        return 'SSE'
    elif code.startswith('180'):
        return 'SZSE'
    return None


def sync_single_fund(fund_code, max_count=30):
    """同步单只REIT的公告到数据库"""
    from cninfo_crawler import CNInfoCrawler

    print(f'[SYNC] 开始同步 {fund_code} 的公告...')

    crawler = CNInfoCrawler()

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

    db_result = save_announcements_to_db(announcements[:max_count], fund_code)

    return {
        'success': True,
        'fund_code': fund_code,
        'total_found': len(announcements),
        'inserted': db_result['inserted'],
        'skipped': db_result['skipped'],
        'invalid_pdf': db_result.get('invalid_pdf', 0)
    }


def sync_all_reits(max_count=30):
    """同步所有REIT的公告到数据库"""
    from cninfo_crawler import CNInfoCrawler
    REIT_CODE_MAPPING = CNInfoCrawler.REIT_CODE_MAPPING

    print(f'[SYNC] 开始同步所有REIT公告，每只最多{max_count}条...')

    stats = {
        'total': len(REIT_CODE_MAPPING),
        'success': 0,
        'failed': 0,
        'total_inserted': 0,
        'total_skipped': 0,
        'total_invalid_pdf': 0
    }

    for code in REIT_CODE_MAPPING.keys():
        try:
            result = sync_single_fund(code, max_count)
            if result['success']:
                stats['success'] += 1
                stats['total_inserted'] += result['inserted']
                stats['total_skipped'] += result['skipped']
                stats['total_invalid_pdf'] += result.get('invalid_pdf', 0)
            else:
                stats['failed'] += 1
        except Exception as e:
            stats['failed'] += 1
            print(f'[SYNC] {code} 异常: {e}')

    print(f'[SYNC] 全部完成: 成功{stats["success"]}/{stats["total"]}, 新增{stats["total_inserted"]}, 跳过{stats["total_skipped"]}, PDF无效{stats["total_invalid_pdf"]}')
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