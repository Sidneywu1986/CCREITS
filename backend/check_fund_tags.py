#!/usr/bin/env python3
import sqlite3, re
conn = sqlite3.connect('database/reits.db')
cur = conn.cursor()

# 检查文章内容中基金代码出现情况
cur.execute('SELECT id, title, content FROM wechat_articles WHERE content IS NOT NULL LIMIT 5')
for row in cur.fetchall():
    codes = re.findall(r'(?<!\d)\d{6}(?!\d)', row[2] or '')
    print(f'ID {row[0]}: {row[1][:40]}... -> 基金代码: {list(set(codes))[:5]}')

# 看看 funds 表有多少只基金
cur.execute('SELECT COUNT(*) FROM funds')
print(f'\n基金总数: {cur.fetchone()[0]}')

# 检查是否已有文章-基金关联表
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%article%'")
print(f'\n文章相关表: {[r[0] for r in cur.fetchall()]}')

# 抽样检查文章中有多少包含基金代码
cur.execute('SELECT id, title, content FROM wechat_articles WHERE content IS NOT NULL')
has_code = 0
total = 0
fund_to_articles = {}
for row in cur.fetchall():
    total += 1
    codes = set(re.findall(r'(?<!\d)\d{6}(?!\d)', row[2] or ''))
    # 过滤出有效的基金代码（在 funds 表中存在的）
    if codes:
        has_code += 1
        for c in list(codes)[:3]:
            fund_to_articles.setdefault(c, 0)
            fund_to_articles[c] += 1

print(f'\n包含6位数字的文章: {has_code}/{total}')
print(f'\n出现频率最高的数字（可能是基金代码）top 15:')
for code, cnt in sorted(fund_to_articles.items(), key=lambda x: -x[1])[:15]:
    print(f'  {code}: {cnt}篇')

conn.close()
