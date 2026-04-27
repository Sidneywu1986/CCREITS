#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公告数据服务 - 分层架构
第一层：SSE API（上交所REITs）- 官方API，最可靠
第二层：CNInfo API（巨潮资讯）- 官方API，支持深交所REITs
第三层：东方财富/Tonghuashun - 聚合平台，兜底
"""

import requests
import re
import os
import datetime
import time
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.db import get_conn

# REITs基金代码列表
REITS_CODES = [
    # 上交所
    '508000', '508001', '508002', '508003', '508005', '508006', '508007', '508008', '508009',
    '508010', '508011', '508012', '508015', '508016', '508017', '508018', '508019',
    '508021', '508022', '508026', '508027', '508028', '508029',
    '508031', '508032', '508033', '508035', '508036', '508037', '508038', '508039',
    '508048', '508050', '508055', '508056', '508058', '508060', '508066', '508068',
    '508069', '508077', '508078', '508080', '508082', '508084', '508085', '508086',
    '508087', '508088', '508089', '508090', '508091', '508092', '508096', '508097',
    '508098', '508099',
    # 深交所
    '180101', '180102', '180103', '180105', '180106', '180201', '180202', '180203',
    '180301', '180302', '180303', '180305', '180306', '180401', '180402', '180501',
    '180502', '180503', '180601', '180602', '180603', '180605', '180606', '180607',
    '180701', '180801', '180901'
]

# 公告分类关键词（按精确度排序，优先匹配高确定性分类）
CATEGORY_KEYWORDS = {
    'inquiry': ['问询函', '关注函', '监管工作函', '审核问询函', '反馈意见'],   # 高确定性，优先匹配
    'dividend': ['分红', '派息', '收益分配', '权益分派', '红利', '分配'],
    'listing': ['上市', '发售', '认购', '招募说明书', '扩募'],
    'disclosure': ['信息披露', '澄清', '风险提示', '停牌', '复牌'],
    'financial': ['年报', '季报', '半年报', '审计', '财务报告', '业绩预告', '报告书', '报告期', '评估报告'],
    'operation': ['运营', '租赁', '出租率', '车流量', '物业', '经营数据', '运营数据']   # 移除过于宽泛的"管理""项目""季度"
}


def classify_announcement(title: str) -> str:
    """根据标题分类公告"""
    # 高确定性财务报告标识（优先匹配，避免被分红/运营等次要关键词覆盖）
    for kw in ('季度报告', '年度报告', '半年度报告'):
        if kw in title:
            return 'financial'
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in title:
                return category
    return 'other'


def generate_summary(title: str, category: str) -> str:
    """生成摘要"""
    summaries = {
        'dividend': '本基金发布分红派息相关公告，请关注权益登记日和除息日安排。',
        'operation': '本基金发布运营相关公告，涉及物业经营、租赁收入等内容。',
        'financial': '本基金发布定期财务报告，包含营收、利润等核心财务指标。',
        'inquiry': '本基金收到交易所问询函或发布相关回复公告。',
        'listing': '本基金发布上市发行相关公告，涉及发售、认购等事项。',
        'disclosure': '本基金发布信息披露或重大事项澄清公告。',
        'other': '本基金发布重要公告，请关注具体内容。'
    }
    return summaries.get(category, summaries['other'])


def _get_fund_info_map():
    """从数据库获取基金信息映射"""
    fund_map = {}
    try:
        with get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT fund_code, fund_name, manager, custodian FROM business.funds")
            for row in cursor.fetchall():
                fund_map[row[0]] = {
                    'fund_name': row[1] or '',
                    'manager': row[2] or '',
                    'custodian': row[3] or ''
                }
    except Exception as e:
        print(f"获取基金信息失败: {e}")
    return fund_map


# ==================== 第一层：SSE API（上交所REITs） ====================

def fetch_sse_announcements(limit_per_stock: int = 30) -> List[Dict]:
    """从上交所获取上交所REITs公告"""
    all_announcements = []
    sse_url = "https://www.sse.com.cn/disclosure/fund/announcement/json/fund_bulletin_publish_order.json"

    # 上交所REITs代码
    sse_codes = [c for c in REITS_CODES if c.startswith('508')]

    # 从数据库获取基金信息（管理人、基金管理人）
    fund_info_map = _get_fund_info_map()

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.sse.com.cn/',
            'Accept': 'application/json'
        }

        # 获取全部公开的公告数据（一次请求返回当日所有公告）
        resp = requests.get(sse_url, headers=headers, timeout=15)
        data = resp.json()

        publish_data = data.get('publishData', [])

        # 筛选出上交所REITs的公告（根据securityCode前6位匹配508XXX）
        for item in publish_data:
            code = item.get('securityCode', '')
            if code not in sse_codes:
                continue

            bulletin_url = item.get('bulletinUrl', '')
            # 构造完整PDF URL
            if bulletin_url and not bulletin_url.startswith('http'):
                pdf_url = 'https://www.sse.com.cn' + bulletin_url
            else:
                pdf_url = bulletin_url

            # 从基金信息映射获取名称和管理人
            info = fund_info_map.get(code, {})
            fund_name = info.get('fund_name', '')
            manager = info.get('manager', '')
            publisher = item.get('securityAbbr', '')  # SSE JSON有简称作为发行人

            all_announcements.append({
                'fund_code': code,
                'fund_name': fund_name or item.get('securityAbbr', ''),
                'manager': manager,
                'publisher': publisher,
                'title': item.get('bulletinTitle', ''),
                'category': classify_announcement(item.get('bulletinTitle', '')),
                'summary': generate_summary(item.get('bulletinTitle', ''), classify_announcement(item.get('bulletinTitle', ''))),
                'publish_date': item.get('discloseDate', ''),
                'source_url': pdf_url,
                'pdf_url': pdf_url,
                'exchange': 'SSE',
                'confidence': 0.95,
                'source': 'sse'
            })

    except Exception as e:
        print(f"[SSE API] 获取失败: {e}")

    return all_announcements


# ==================== 第二层：CNInfo API（深交所REITs备用） ====================

def fetch_cninfo_announcements(limit_per_stock: int = 30) -> List[Dict]:
    """从CNInfo获取公告"""
    all_announcements = []

    try:
        from cninfo_crawler import CNInfoCrawler

        crawler = CNInfoCrawler()

        for code in REITS_CODES:
            # CNInfo对深交所180XXX支持最好，上交所508XXX需要orgId
            try:
                fund_info = crawler.search_fund(code)
                if not fund_info:
                    # 上交所代码没有orgId，直接跳过（已由SSE API处理）
                    if code.startswith('508'):
                        continue

                org_id = fund_info.get('orgId', '') if fund_info else ''

                announcements = crawler.get_announcements(
                    fund_code=code,
                    org_id=org_id,
                    page_size=limit_per_stock
                )

                for ann in announcements:
                    time_ms = ann.get('time', 0)
                    if time_ms:
                        publish_date = datetime.datetime.fromtimestamp(time_ms / 1000).strftime('%Y-%m-%d')
                    else:
                        publish_date = ''

                    pdf_url = ann.get('pdf_url', '')
                    source_url = pdf_url if pdf_url else ''

                    all_announcements.append({
                        'fund_code': code,
                        'title': ann.get('title', ''),
                        'category': classify_announcement(ann.get('title', '')),
                        'summary': generate_summary(ann.get('title', ''), classify_announcement(ann.get('title', ''))),
                        'publish_date': publish_date,
                        'source_url': source_url,
                        'pdf_url': pdf_url,
                        'exchange': 'SZSE' if not code.startswith('5') else 'SSE',
                        'confidence': 0.9,
                        'source': 'cninfo'
                    })
            except Exception as e:
                print(f"  [CNInfo] {code} 获取失败: {e}")
                continue

    except ImportError as e:
        print(f"[公告服务] CNInfo爬虫导入失败: {e}")

    return all_announcements


# ==================== 数据源统一入口 ====================

def fetch_all_announcements(live=True, limit_per_stock: int = 5) -> List[Dict]:
    """
    统一获取公告（分层策略）
    - live=True: 实时抓取（交易时间）
    - live=False: 使用数据库缓存
    """
    if not live:
        return get_cached_announcements()

    all_data = []

    # 第一层：SSE API（上交所REITs）
    print("[公告服务] 第一层：SSE上交所...")
    sse_data = fetch_sse_announcements(limit_per_stock)
    print(f"[公告服务] SSE获取 {len(sse_data)} 条")
    all_data.extend(sse_data)

    # 第二层：CNInfo（深交所REITs + 上交所备用）
    # 只有SSE数据不足时才用CNInfo补充
    if len(sse_data) < 5:
        print("[公告服务] 第二层：CNInfo...")
        cninfo_data = fetch_cninfo_announcements(limit_per_stock)
        print(f"[公告服务] CNInfo获取 {len(cninfo_data)} 条")

        # 合并去重
        existing_codes = {a['fund_code'] for a in all_data}
        for ann in cninfo_data:
            if ann['fund_code'] not in existing_codes:
                all_data.append(ann)

    # 如果获取数量太少，补充数据库缓存
    if len(all_data) < 10:
        print("[公告服务] 数据不足，补充数据库缓存...")
        cached = get_cached_announcements(limit=50)
        all_data = merge_announcements(all_data, cached)

    # 保存到数据库
    if all_data:
        save_announcements_to_db(all_data)

    return all_data if all_data else get_cached_announcements()


def merge_announcements(primary: List[Dict], secondary: List[Dict]) -> List[Dict]:
    """合并两个数据源的公告，去重"""
    seen = set()
    merged = []

    for ann in sorted(primary, key=lambda x: x['publish_date'], reverse=True):
        key = (ann['fund_code'], ann['title'], ann['publish_date'])
        if key not in seen:
            seen.add(key)
            merged.append(ann)

    for ann in sorted(secondary, key=lambda x: x['publish_date'], reverse=True):
        key = (ann['fund_code'], ann['title'], ann['publish_date'])
        if key not in seen:
            seen.add(key)
            merged.append(ann)

    return merged


# ==================== 数据库操作 ====================

def get_cached_announcements(limit: int = 100) -> List[Dict]:
    """获取数据库缓存的公告"""
    try:
        with get_conn() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT a.id, a.fund_code, a.fund_name, a.title, a.category, a.publish_date,
                       a.source_url, a.pdf_url, a.exchange, a.confidence, a.source, a.created_at,
                       a.manager, a.publisher,
                       f.ipo_date, f.total_shares,
                       (SELECT open_price FROM business.fund_prices WHERE fund_code = a.fund_code ORDER BY trade_date ASC LIMIT 1) as first_open_price,
                       (SELECT close_price FROM business.fund_prices WHERE fund_code = a.fund_code ORDER BY trade_date DESC LIMIT 1) as latest_price,
                       a.status, a.status_changed_at, a.is_suspicious
                FROM business.announcements a
                LEFT JOIN business.funds f ON a.fund_code = f.fund_code
                ORDER BY a.publish_date DESC
                LIMIT %s
            """, (limit,))

            rows = cursor.fetchall()

        announcements = []
        for row in rows:
            ipo_date = row[14] or ''
            total_shares = row[15] or 0  # 亿元（亿股）
            first_open_price = row[16] or 0  # 元（首日开盘价）
            latest_price = row[17] or 0  # 元
            status = row[18] or 'draft'
            status_changed_at = row[19] or ''
            is_suspicious = row[20] if row[20] is not None else 0

            # 发行市值 = 首日开盘价 × 总份额（亿元）
            ipo_market_cap = first_open_price * total_shares if first_open_price and total_shares else 0
            # 今日市值 = 最新价 × 总份额（亿元）
            current_market_cap = latest_price * total_shares if latest_price and total_shares else 0

            announcements.append({
                'id': row[0],
                'fund_code': row[1],
                'fund_name': row[2] or '',
                'title': row[3],
                'category': row[4] or 'other',
                'publish_date': row[5],
                'source_url': row[6],
                'pdf_url': row[7],
                'exchange': row[8],
                'confidence': row[9] / 100 if row[9] else 0.9,
                'source': row[10],
                'created_at': row[11],
                'manager': row[12] or '',
                'publisher': row[13] or '',
                'ipo_date': ipo_date,
                'ipo_market_cap': round(ipo_market_cap, 2),   # 发行市值（亿元）
                'current_market_cap': round(current_market_cap, 2),  # 今日市值（亿元）
                'status': status,
                'status_changed_at': status_changed_at,
                'is_suspicious': is_suspicious
            })

        return announcements
    except Exception as e:
        print(f"获取缓存公告失败: {e}")
        return []


def save_announcements_to_db(announcements: List[Dict]) -> int:
    """保存公告到数据库"""
    if not announcements:
        return 0

    try:
        with get_conn() as conn:
            cursor = conn.cursor()

            inserted = 0
            for ann in announcements:
                try:
                    cursor.execute("""
                        INSERT INTO business.announcements
                        (fund_code, fund_name, title, category, source, source_url, pdf_url, exchange, confidence, publish_date, is_processed, is_important, manager, publisher)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE, FALSE, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (
                        ann['fund_code'],
                        ann.get('fund_name', ''),
                        ann['title'],
                        ann['category'],
                        ann.get('source', 'cninfo'),
                        ann['source_url'],
                        ann['pdf_url'],
                        ann['exchange'],
                        int(ann.get('confidence', 0.9) * 100),
                        ann['publish_date'],
                        ann.get('manager', ''),
                        ann.get('publisher', '')
                    ))
                    if cursor.rowcount > 0:
                        inserted += 1
                except Exception as e:
                    pass

            conn.commit()
        print(f"[公告服务] 保存 {inserted} 条新公告到数据库")
        return inserted
    except Exception as e:
        print(f"保存公告失败: {e}")
        return 0


# ==================== 工具函数 ====================

def get_announcements_by_fund(code: str, limit: int = 20) -> List[Dict]:
    """获取指定基金的公告"""
    try:
        with get_conn() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, fund_code, fund_name, title, category, publish_date,
                       source_url, pdf_url, exchange, confidence, source,
                       manager, publisher, status, status_changed_at, is_suspicious
                FROM business.announcements
                WHERE fund_code = %s
                ORDER BY publish_date DESC
                LIMIT %s
            """, (code, limit))

            rows = cursor.fetchall()

        return [{
            'id': row[0],
            'fund_code': row[1],
            'fund_name': row[2] or '',
            'title': row[3],
            'category': row[4] or 'other',
            'publish_date': row[5],
            'source_url': row[6],
            'pdf_url': row[7],
            'exchange': row[8],
            'confidence': row[9] / 100 if row[9] else 0.9,
            'source': row[10],
            'manager': row[11] or '',
            'publisher': row[12] or '',
            'status': row[13] or 'draft',
            'status_changed_at': row[14] or '',
            'is_suspicious': row[15] if row[15] is not None else 0
        } for row in rows]
    except Exception as e:
        print(f"获取基金公告失败: {e}")
        return []


def get_announcements_by_category(category: str, limit: int = 50) -> List[Dict]:
    """按分类获取公告"""
    try:
        with get_conn() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, fund_code, fund_name, title, category, publish_date,
                       source_url, pdf_url, exchange, confidence, source,
                       manager, publisher, status, status_changed_at, is_suspicious
                FROM business.announcements
                WHERE category = %s
                ORDER BY publish_date DESC
                LIMIT %s
            """, (category, limit))

            rows = cursor.fetchall()

        return [{
            'id': row[0],
            'fund_code': row[1],
            'fund_name': row[2] or '',
            'title': row[3],
            'category': row[4] or 'other',
            'publish_date': row[5],
            'source_url': row[6],
            'pdf_url': row[7],
            'exchange': row[8],
            'confidence': row[9] / 100 if row[9] else 0.9,
            'source': row[10],
            'manager': row[11] or '',
            'publisher': row[12] or '',
            'status': row[13] or 'draft',
            'status_changed_at': row[14] or '',
            'is_suspicious': row[15] if row[15] is not None else 0
        } for row in rows]
    except Exception as e:
        print(f"按分类获取公告失败: {e}")
        return []


def mark_as_read(announcement_id: int) -> bool:
    """标记公告已读"""
    try:
        with get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE business.announcements SET is_important = TRUE WHERE id = %s", (announcement_id,))
            conn.commit()
        return True
    except Exception as e:
        print(f"标记已读失败: {e}")
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("公告数据服务测试")
    print("=" * 60)

    # 测试SSE API
    print("\n=== 测试SSE API ===")
    sse_data = fetch_sse_announcements(limit_per_stock=30)
    print(f"SSE获取 {len(sse_data)} 条公告")
    for ann in sse_data[:5]:
        print(f"  [{ann['exchange']}] {ann['publish_date']} [{ann['category']}] {ann['title'][:40]}...")

    # 测试获取全部公告
    print("\n=== 测试 fetch_all_announcements ===")
    announcements = fetch_all_announcements(live=True, limit_per_stock=3)
    print(f"\n获取到 {len(announcements)} 条公告")

    # 显示前10条
    print("\n前10条公告:")
    for i, ann in enumerate(announcements[:10]):
        print(f"  [{ann['exchange']}] {ann['publish_date']} [{ann['category']}] {ann['title'][:40]}...")

    # 统计分类
    categories = {}
    for ann in announcements:
        cat = ann['category']
        categories[cat] = categories.get(cat, 0) + 1
    print(f"\n分类统计: {categories}")
