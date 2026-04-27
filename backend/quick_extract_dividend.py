#!/usr/bin/env python3
"""
快速从少量分红公告PDF中提取分红数据
只处理10只基金作为样本验证
"""

import os
import re
import json
import sqlite3

def extract_dividend_from_pdf(pdf_path):
    """快速提取分红金额"""
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            # 只读第一页，速度更快
            text = pdf.pages[0].extract_text() or ""
        
        # 查找金额模式（常见格式）
        patterns = [
            r'每份基金分配人民币\s*([0-9]+\.[0-9]+)\s*元',
            r'每份派发现金红利\s*([0-9]+\.[0-9]+)\s*元',
            r'每份基金份额发放现金红利人民币\s*([0-9]+\.[0-9]+)\s*元',
            r'每份基金份额派发.*?([0-9]+\.[0-9]+)\s*元',
            r'每份.*?([0-9]+\.[0-9]{3,4})\s*元',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                amount = float(match.group(1))
                if 0.001 <= amount <= 5:
                    return amount
        
        return None
    except Exception as e:
        return None

def main():
    base_dir = 'announcements'
    
    # 扫描分红PDF
    fund_pdfs = {}
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if not f.endswith('.pdf'):
                continue
            if '分红' in f or '收益分配' in f or '权益分派' in f:
                parts = os.path.normpath(root).split(os.sep)
                fund_code = None
                for part in parts:
                    if part.startswith('180') or part.startswith('508'):
                        fund_code = part.split('_')[0]
                        break
                if fund_code:
                    if fund_code not in fund_pdfs:
                        fund_pdfs[fund_code] = []
                    fund_pdfs[fund_code].append(os.path.join(root, f))
    
    print(f"找到 {len(fund_pdfs)} 只基金的分红公告")
    
    # 获取数据库数据
    conn = sqlite3.connect('database/reits.db')
    cursor = conn.cursor()
    cursor.execute('SELECT fund_code, fund_name, nav, dividend_yield FROM funds')
    local_data = {r[0]: {'name': r[1], 'nav': r[2], 'dividend_yield': r[3]} for r in cursor.fetchall()}
    conn.close()
    
    # 解析PDF（每只基金最多3份）
    results = []
    for code, pdfs in sorted(fund_pdfs.items()):
        info = local_data.get(code, {})
        dividends = []
        for pdf_path in sorted(pdfs)[:3]:
            amount = extract_dividend_from_pdf(pdf_path)
            if amount:
                dividends.append(amount)
        
        if dividends:
            avg = sum(dividends) / len(dividends)
            total = sum(dividends)
            nav = info.get('nav', 0)
            stored = info.get('dividend_yield')
            nav_yield = (total / nav * 100) if nav else 0
            results.append({
                'code': code,
                'name': info.get('name', '')[:20],
                'stored_yield': stored,
                'parsed_dividends': dividends,
                'total': round(total, 4),
                'nav_yield_estimate': round(nav_yield, 2),
            })
    
    # 输出对比
    print("\n" + "="*90)
    print(f"{'代码':<10} {'名称':<22} {'存储派息率':>12} {'解析分红总额':>14} {'估算派息率':>12} {'分红次数':>8}")
    print("-"*90)
    for r in results:
        stored = f"{r['stored_yield']:.2f}%" if r['stored_yield'] else "N/A"
        print(f"{r['code']:<10} {r['name']:<22} {stored:>12} {r['total']:>14.4f} {r['nav_yield_estimate']:>11.2f}% {len(r['parsed_dividends']):>8}")
    
    # 保存结果
    with open('quick_dividend_check.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存到 quick_dividend_check.json")

if __name__ == '__main__':
    main()
