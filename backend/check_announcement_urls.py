# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect('database/reits.db')
cursor = conn.cursor()

print("=== 公告URL检查 ===")
cursor.execute('SELECT fund_code, title, source_url, exchange FROM announcements WHERE source_url IS NOT NULL LIMIT 10')
for row in cursor.fetchall():
    code, title, url, exchange = row
    url_str = url[:80] + '...' if url and len(url) > 80 else url
    print(f'\n基金: {code} ({exchange})')
    print(f'标题: {title[:50]}...')
    print(f'URL: {url_str}')

print('\n=== 统计 ===')
cursor.execute('SELECT COUNT(*) FROM announcements WHERE source_url IS NOT NULL')
print(f'有URL的公告: {cursor.fetchone()[0]}条')

cursor.execute('SELECT COUNT(*) FROM announcements WHERE source_url LIKE "%.pdf"')
print(f'PDF直接链接: {cursor.fetchone()[0]}条')

conn.close()
