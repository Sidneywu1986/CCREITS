# -*- coding: utf-8 -*-
import sqlite3
conn = sqlite3.connect('database/reits.db')
cursor = conn.cursor()

print('=== 公告表当前状态 ===')
cursor.execute('SELECT COUNT(*) FROM announcements')
print(f'公告总数: {cursor.fetchone()[0]}条')

print('\n分类统计:')
cursor.execute('SELECT category, COUNT(*) FROM announcements GROUP BY category')
for row in cursor.fetchall():
    cat = row[0] or 'NULL'
    print(f'  {cat}: {row[1]}条')

print('\n最近5条公告:')
cursor.execute('SELECT fund_code, title, category, publish_date FROM announcements ORDER BY created_at DESC LIMIT 5')
for row in cursor.fetchall():
    title = row[1][:30] + '...' if row[1] else 'N/A'
    print(f'  {row[0]} | {title} | {row[2]} | {row[3]}')

conn.close()
