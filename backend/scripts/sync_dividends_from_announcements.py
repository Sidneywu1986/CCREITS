#!/usr/bin/env python3
"""
从 announcements 表中的分红公告同步到 dividends 表
V2: 全页扫描 + 表格提取 + 每10份自动处理
"""
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANNOUNCEMENTS_DIR = os.path.join(os.path.dirname(BASE_DIR), 'announcements')

sys.path.insert(0, BASE_DIR)
from core.db import get_conn

def find_pdf_for_announcement(fund_code, publish_date):
    """在 announcements 目录中查找对应的PDF"""
    for d in os.listdir(ANNOUNCEMENTS_DIR):
        if d.startswith(fund_code):
            fund_dir = os.path.join(ANNOUNCEMENTS_DIR, d)
            if not os.path.exists(fund_dir):
                return None
            # 查找包含日期的PDF
            for f in os.listdir(fund_dir):
                if f.endswith('.pdf') and publish_date and publish_date.replace('-', '') in f:
                    return os.path.join(fund_dir, f)
            # 查找分红相关PDF
            for f in os.listdir(fund_dir):
                if f.endswith('.pdf') and any(k in f for k in ['分红', '收益分配', '权益分派', '现金红利']):
                    return os.path.join(fund_dir, f)
            return None
    return None

def extract_dividend_from_pdf(pdf_path):
    """从PDF提取分红信息（V2: 全页扫描 + 表格提取 + 每10份自动处理）"""
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            full_text = ""
            all_tables = []
            for page in pdf.pages:
                pt = page.extract_text()
                if pt:
                    full_text += pt + "\n"
                tables = page.extract_tables()
                if tables:
                    all_tables.extend(tables)
        
        amount = None
        record_date = None
        ex_date = None
        
        # 策略1: 在表格中查找金额（表格中的数据更结构化，分红金额常在表格中）
        for table in all_tables:
            for row in table:
                if not row:
                    continue
                row_text = ' '.join(str(c) for c in row if c)
                # 查找包含"每份"或"每10份"和金额的行
                m = re.search(r'每(?:份|10份).*?(\d+\.\d{2,4}).*?元', row_text)
                if m:
                    amount = float(m.group(1))
                    if '每10份' in row_text or '每 10 份' in row_text:
                        amount = round(amount / 10, 4)
                    if 0.001 <= amount <= 5:
                        break
            if amount:
                break
        
        # 策略2: 在全文中搜索（更宽松的模式）
        if not amount:
            amount_patterns = [
                # 每10份优先匹配，避免先匹配到金额再误判
                (r'每10份基金份额派发.*?人民币\s*([0-9]+\.[0-9]+)\s*元', True),
                (r'每10份.*?派发现金红利.*?([0-9]+\.[0-9]+)\s*元', True),
                (r'每10份.*?分配.*?([0-9]+\.[0-9]+)\s*元', True),
                (r'每10份基金份额发放现金红利人民币\s*([0-9]+\.[0-9]+)\s*元', True),
                (r'每份基金份额发放现金红利人民币\s*([0-9]+\.[0-9]+)\s*元', False),
                (r'每份基金份额派发.*?([0-9]+\.[0-9]+)\s*元', False),
                (r'每份基金分配.*?人民币\s*([0-9]+\.[0-9]+)\s*元', False),
                (r'每份.*?分配.*?人民币\s*([0-9]+\.[0-9]+)\s*元', False),
                (r'每份.*?派发现金红利.*?([0-9]+\.[0-9]+)\s*元', False),
                (r'每份.*?派发.*?([0-9]+\.[0-9]+)\s*元', False),
                (r'每份.*?分红.*?([0-9]+\.[0-9]+)\s*元', False),
                (r'每份.*?现金红利.*?([0-9]+\.[0-9]+)\s*元', False),
                (r'每份基金分配.*?(\d+\.\d{2,4}).*?元', False),
                (r'每份.*?(\d+\.\d{2,4}).*?元', False),
                (r'本次分配金额为.*?([0-9]+\.[0-9]+)\s*元', False),
                (r'分配金额.*?([0-9]+\.[0-9]+)\s*元.*?每份', False),
            ]
            for pattern, is_per10 in amount_patterns:
                m = re.search(pattern, full_text)
                if m:
                    amount = float(m.group(1))
                    if is_per10:
                        amount = round(amount / 10, 4)
                    else:
                        # 检测上下文是否有"每10份"
                        prefix = full_text[max(0, m.start()-30):m.start()]
                        if '每10份' in prefix or '每 10 份' in prefix:
                            amount = round(amount / 10, 4)
                    break
        
        # 金额合理性检查 + 二次修正
        if amount and not (0.001 <= amount <= 5):
            amount = round(amount / 10, 4)
            if not (0.001 <= amount <= 5):
                amount = None
        
        # 提取权益登记日
        for p in [
            r'权益登记日[：:]\s*(20\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日',
            r'权益登记日.*?(20\d{2})[-/年](\d{1,2})[-/月](\d{1,2})',
            r'登记日[：:]\s*(20\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日',
        ]:
            m = re.search(p, full_text)
            if m:
                record_date = f"{m.group(1)[:4]}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
                break
        
        # 提取除息日
        for p in [
            r'除息日[：:]\s*(20\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日',
            r'除息日.*?(20\d{2})[-/年](\d{1,2})[-/月](\d{1,2})',
            r'除权.*?除息日.*?(20\d{2})[-/年](\d{1,2})[-/月](\d{1,2})',
        ]:
            m = re.search(p, full_text)
            if m:
                ex_date = f"{m.group(1)[:4]}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
                break
        
        # 如果没有除息日，尝试从红利发放日推断
        if not ex_date:
            for p in [
                r'红利发放日[：:]\s*(20\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日',
                r'发放日.*?(20\d{2})[-/年](\d{1,2})[-/月](\d{1,2})',
            ]:
                m = re.search(p, full_text)
                if m:
                    ex_date = f"{m.group(1)[:4]}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
                    break
        
        return amount, record_date, ex_date
    except Exception as e:
        print(f"  解析PDF失败 {pdf_path}: {e}")
        return None, None, None

def sync_dividends():
    with get_conn() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT fund_code, title, publish_date, source_url 
            FROM business.announcements 
            WHERE category = 'dividend' 
            ORDER BY publish_date DESC
        """)
        rows = cursor.fetchall()
        print(f"找到 {len(rows)} 条分红公告")
        
        inserted = 0
        parsed = 0
        
        for fund_code, title, publish_date, source_url in rows:
            pdf_path = find_pdf_for_announcement(fund_code, publish_date)
            amount = record_date = ex_date = None
            
            if pdf_path:
                amount, record_date, ex_date = extract_dividend_from_pdf(pdf_path)
                if amount:
                    parsed += 1
                    print(f"[{fund_code}] PDF解析成功: 金额={amount}, 登记日={record_date}, 除息日={ex_date}")
            
            # 如果PDF解析失败，尝试从标题提取金额
            if not amount and title:
                m = re.search(r'([0-9]+\.[0-9]+)\s*元', title)
                if m:
                    amount = float(m.group(1))
                    if not (0.001 <= amount <= 5):
                        amount = None
            
            if not amount:
                print(f"[{fund_code}] 无法提取分红金额, 跳过")
                continue
            
            dividend_date = ex_date or record_date or publish_date
            if not dividend_date:
                continue
            
            if len(str(dividend_date)) == 8 and str(dividend_date).isdigit():
                dividend_date = f"{str(dividend_date)[:4]}-{str(dividend_date)[4:6]}-{str(dividend_date)[6:]}"
            
            # 检查是否已存在
            cursor.execute(
                "SELECT 1 FROM business.dividends WHERE fund_code = %s AND dividend_date = %s",
                (fund_code, dividend_date)
            )
            if cursor.fetchone():
                continue
            
            try:
                cursor.execute("""
                    INSERT INTO business.dividends 
                    (fund_code, dividend_date, dividend_amount, record_date, ex_dividend_date, created_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                """, (fund_code, dividend_date, amount, record_date, ex_date))
                if cursor.rowcount > 0:
                    inserted += 1
            except Exception as e:
                print(f"[{fund_code}] 插入失败: {e}")
        
        conn.commit()
    
    print(f"\n完成: 解析成功 {parsed} 条, 新插入 {inserted} 条")
    return inserted

if __name__ == '__main__':
    sync_dividends()
