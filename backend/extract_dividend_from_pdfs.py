#!/usr/bin/env python3
"""
从公告PDF中提取分红数据，计算正确派息率
"""

import os
import re
import json
from collections import defaultdict
from datetime import datetime
from core.db import get_conn
import logging
logger = logging.getLogger(__name__)

def extract_dividend_from_pdf(pdf_path):
    """从单个PDF中提取分红金额"""
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages[:3]:  # 只读前3页
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        # 查找每份分红金额
        # 常见格式: "每份基金分配人民币 X.XXXX 元", "每份派发现金红利 X.XXXX 元"
        patterns = [
            r'每份.*?分配.*?([0-9]+\.[0-9]+)\s*元',
            r'每份.*?派发现金红利.*?([0-9]+\.[0-9]+)\s*元',
            r'每份.*?派发.*?([0-9]+\.[0-9]+)\s*元',
            r'每份.*?分红.*?([0-9]+\.[0-9]+)\s*元',
            r'每份.*?现金红利.*?([0-9]+\.[0-9]+)\s*元',
            r'每份基金份额发放现金红利人民币\s*([0-9]+\.[0-9]+)\s*元',
            r'每份基金份额派发.*?([0-9]+\.[0-9]+)\s*元',
            r'每份基金分配.*?(\d+\.\d{2,4}).*?元',
            r'每份.*?(\d+\.\d{2,4}).*?元',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                amount = float(match.group(1))
                # 合理性检查：每份分红通常在0.01-2元之间
                if 0.001 <= amount <= 5:
                    return amount
        
        return None
    except (OSError, ValueError, TypeError) as e:
        logger.error(f"解析PDF失败 {pdf_path}: {e}")
        return None

def extract_date_from_filename(filename):
    """从文件名提取日期"""
    match = re.search(r'(\d{8})', filename)
    if match:
        return match.group(1)
    return None

def scan_all_dividend_pdfs():
    """扫描所有分红公告PDF"""
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'announcements')
    
    fund_dividends = defaultdict(list)
    
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if not f.endswith('.pdf'):
                continue
            if '分红' in f or '收益分配' in f or '权益分派' in f:
                pdf_path = os.path.join(root, f)
                
                # 从目录名提取基金代码
                parts = os.path.normpath(root).split(os.sep)
                fund_code = None
                for part in parts:
                    if part.startswith('180') or part.startswith('508'):
                        fund_code = part.split('_')[0]
                        break
                
                if fund_code:
                    date = extract_date_from_filename(f)
                    amount = extract_dividend_from_pdf(pdf_path)
                    fund_dividends[fund_code].append({
                        'date': date,
                        'filename': f,
                        'amount': amount,
                        'path': pdf_path
                    })
    
    return fund_dividends

def calculate_correct_dividend_yield(fund_dividends, local_data, realtime_data):
    """计算正确的派息率"""
    results = []
    
    for code, dividends in fund_dividends.items():
        info = local_data.get(code, {})
        rt = realtime_data.get(code, {})
        current_price = rt.get('current_price', 0) or info.get('nav', 0)
        
        # 过滤有金额的分红记录
        valid = [d for d in dividends if d['amount'] is not None]
        if not valid:
            continue
        
        # 按日期排序
        valid.sort(key=lambda x: x['date'] or '00000000')
        
        # 计算近12个月分红总额
        total_dividend = sum(d['amount'] for d in valid)
        count = len(valid)
        
        # 估算年化派息率（假设每年分红次数相同）
        if count >= 2 and valid[0]['date'] and valid[-1]['date']:
            first_date = datetime.strptime(valid[0]['date'], '%Y%m%d')
            last_date = datetime.strptime(valid[-1]['date'], '%Y%m%d')
            days = (last_date - first_date).days
            if days > 30:
                # 年化 = (总分红 / 天数) * 365
                annual_dividend = total_dividend / days * 365
            else:
                annual_dividend = total_dividend
        else:
            annual_dividend = total_dividend
        
        # 基于市价的派息率
        market_yield = (annual_dividend / current_price * 100) if current_price else 0
        
        # 基于净值的派息率
        nav = info.get('nav', 0)
        nav_yield = (annual_dividend / nav * 100) if nav else 0
        
        stored_yield = info.get('dividend_yield')
        
        results.append({
            'code': code,
            'name': info.get('name', ''),
            'current_price': current_price,
            'nav': nav,
            'stored_dividend_yield': stored_yield,
            'calculated_market_yield': round(market_yield, 2),
            'calculated_nav_yield': round(nav_yield, 2),
            'annual_dividend_estimate': round(annual_dividend, 4),
            'total_dividend_from_pdfs': round(total_dividend, 4),
            'dividend_count': count,
            'first_date': valid[0]['date'],
            'last_date': valid[-1]['date'],
            'dividends': [{'date': d['date'], 'amount': d['amount']} for d in valid]
        })
    
    return results

if __name__ == '__main__':
    logger.info("扫描分红公告PDF...")
    fund_dividends = scan_all_dividend_pdfs()
    logger.info(f"找到 {len(fund_dividends)} 只基金的分红公告")
    
    # 获取本地数据库数据
    with get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT fund_code, fund_name, nav, dividend_yield FROM business.funds')
            local_data = {r[0]: {'name': r[1], 'nav': r[2], 'dividend_yield': r[3]} for r in cursor.fetchall()}
    
    # 获取实时价格
    import sys
    sys.path.insert(0, 'services')
    from realtime_quotes import fetch_all_reits_quotes
    
    try:
        quotes = fetch_all_reits_quotes()
        realtime_data = {q['fund_code']: q for q in quotes}
    except (RuntimeError, ValueError) as e:
        logger.error(f"获取实时价格失败: {e}")
        realtime_data = {}
    
    logger.info("计算正确派息率...")
    results = calculate_correct_dividend_yield(fund_dividends, local_data, realtime_data)
    
    # 保存结果
    with open('dividend_correction.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n完成！共分析 {len(results)} 只基金")
    logger.info(f"结果已保存到: dividend_correction.json")
    
    # 打印对比
    logger.info("\n" + "="*100)
    logger.info("派息率对比 (仅显示PDF解析成功的基金)")
    logger.info("="*100)
    logger.info(f"{'代码':<10} {'名称':<22} {'存储值':>10} {'市价派息率':>12} {'净值派息率':>12} {'近12月分红':>12} {'分红次数':>8}")
    logger.info("-"*100)
    
    for r in sorted(results, key=lambda x: x['calculated_market_yield'], reverse=True):
        stored = f"{r['stored_dividend_yield']:.2f}%" if r['stored_dividend_yield'] else "N/A"
        name = r['name'][:20] if r['name'] else ''
        logger.info(f"{r['code']:<10} {name:<22} {stored:>10} {r['calculated_market_yield']:>11.2f}% {r['calculated_nav_yield']:>11.2f}% {r['annual_dividend_estimate']:>12.4f} {r['dividend_count']:>8}")
