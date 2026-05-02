#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分红数据同步服务 - 从东方财富获取REIT分红数据
"""

import re
import logging
from typing import List, Dict, Optional
from datetime import datetime

import requests
from bs4 import BeautifulSoup
import psycopg2

from core.db import get_conn

logger = logging.getLogger(__name__)

# REITs基金代码列表
REITS_CODES = [
    '508000', '508001', '508002', '508003', '508005', '508006', '508007', '508008', '508009',
    '508010', '508011', '508012', '508015', '508016', '508017', '508018', '508019',
    '508021', '508022', '508026', '508027', '508028', '508029',
    '508031', '508032', '508033', '508035', '508036', '508037', '508038', '508039',
    '508048', '508050', '508055', '508056', '508058', '508060', '508066', '508068',
    '508069', '508077', '508078', '508080', '508082', '508084', '508085', '508086',
    '508087', '508088', '508089', '508090', '508091', '508092', '508096', '508097',
    '508098', '508099',
    '180101', '180102', '180103', '180105', '180106', '180201', '180202', '180203',
    '180301', '180302', '180303', '180305', '180306', '180401', '180402', '180501',
    '180502', '180503', '180601', '180602', '180603', '180605', '180606', '180607',
    '180701', '180801', '180901'
]


def parse_dividend_amount(text: str) -> Optional[float]:
    """解析分红金额文本，如'每份派现金0.0549元' -> 0.0549"""
    if not text:
        return None
    text = text.strip()
    if text in ('暂无分红', '暂无拆分信息!'):
        return None
    match = re.search(r'(\d+\.?\d*)', text.replace(',', ''))
    if match:
        return float(match.group(1))
    return None


def fetch_fund_dividends(fund_code: str) -> List[Dict]:
    """从东方财富获取单只基金的分红数据"""
    url = f"https://fundf10.eastmoney.com/fhsp_{fund_code}.html"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://fundf10.eastmoney.com/',
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = 'utf-8'

        soup = BeautifulSoup(resp.text, 'html.parser')
        tables = soup.find_all('table')

        dividends = []
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) <= 1:
                continue

            header = [c.get_text(strip=True) for c in rows[0].find_all(['td', 'th'])]
            if '权益登记日' not in header and '除息日' not in header:
                continue

            # 定位列索引
            year_idx = header.index('年份') if '年份' in header else None
            record_idx = header.index('权益登记日') if '权益登记日' in header else None
            ex_idx = header.index('除息日') if '除息日' in header else None
            amount_idx = header.index('每份分红') if '每份分红' in header else None
            pay_idx = header.index('分红发放日') if '分红发放日' in header else None

            for row in rows[1:]:
                cells = [c.get_text(strip=True) for c in row.find_all(['td', 'th'])]
                if len(cells) < 3:
                    continue
                if '暂无' in cells[0] or '暂无' in cells[-1]:
                    continue

                year_text = cells[year_idx] if year_idx is not None and year_idx < len(cells) else ''
                year_match = re.search(r'(\d{4})', year_text)
                dividend_year = int(year_match.group(1)) if year_match else None

                record_date = cells[record_idx] if record_idx is not None and record_idx < len(cells) else None
                ex_date = cells[ex_idx] if ex_idx is not None and ex_idx < len(cells) else None
                amount_text = cells[amount_idx] if amount_idx is not None and amount_idx < len(cells) else ''
                pay_date = cells[pay_idx] if pay_idx is not None and pay_idx < len(cells) else None

                dividend_per_share = parse_dividend_amount(amount_text)
                if dividend_per_share is None:
                    continue

                #  dividend_date 使用除息日，如果没有则用权益登记日
                dividend_date = ex_date or record_date

                dividends.append({
                    'fund_code': fund_code,
                    'dividend_year': dividend_year,
                    'record_date': record_date,
                    'ex_dividend_date': ex_date,
                    'dividend_per_share': dividend_per_share,
                    'dividend_amount': dividend_per_share,
                    'dividend_payment_date': pay_date,
                    'dividend_date': dividend_date,
                })

        return dividends
    except Exception as e:
        logger.error(f"获取 {fund_code} 分红数据失败: {e}")
        return []


def sync_fund_dividends(fund_code: str) -> int:
    """同步单只基金的分红数据到数据库，返回新增条数"""
    dividends = fetch_fund_dividends(fund_code)
    if not dividends:
        return 0

    inserted = 0
    try:
        with get_conn() as conn:
            cursor = conn.cursor()
            for d in dividends:
                try:
                    cursor.execute("""
                        INSERT INTO business.dividends
                        (fund_code, dividend_year, dividend_round, dividend_date,
                         dividend_amount, dividend_per_share, record_date,
                         ex_dividend_date, dividend_payment_date)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (
                        d['fund_code'],
                        d['dividend_year'],
                        None,  # dividend_round 暂不计算
                        d['dividend_date'],
                        d['dividend_amount'],
                        d['dividend_per_share'],
                        d['record_date'],
                        d['ex_dividend_date'],
                        d['dividend_payment_date'],
                    ))
                    if cursor.rowcount > 0:
                        inserted += 1
                except psycopg2.Error as e:
                    logger.warning(f"插入分红数据失败 {fund_code}: {e}")
                    pass
            conn.commit()
        logger.info(f"[分红同步] {fund_code}: 新增 {inserted} 条")
        return inserted
    except psycopg2.Error as e:
        logger.error(f"同步分红数据失败 {fund_code}: {e}")
        return 0


def sync_all_dividends() -> int:
    """同步所有REIT的分红数据"""
    total = 0
    for code in REITS_CODES:
        count = sync_fund_dividends(code)
        total += count
    logger.info(f"[分红同步] 全部完成，共新增 {total} 条")
    return total
