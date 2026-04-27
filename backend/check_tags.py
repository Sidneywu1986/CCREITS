import sqlite3
conn = sqlite3.connect('database/reits.db')
cur = conn.cursor()

print('=== wechat_articles 字段 ===')
cur.execute('PRAGMA table_info(wechat_articles)')
for col in cur.fetchall():
    print(f'  {col[1]} ({col[2]})')

print()
print('=== 标签分布 ===')
cur.execute('SELECT COUNT(*) FROM wechat_articles WHERE sentiment_score != 0')
print(f'已打情感标签: {cur.fetchone()[0]}篇')

cur.execute("SELECT COUNT(*) FROM wechat_articles WHERE asset_tags != ''")
print(f'已打资产标签: {cur.fetchone()[0]}篇')

cur.execute("SELECT COUNT(*) FROM wechat_articles WHERE event_tags != ''")
print(f'已打事件标签: {cur.fetchone()[0]}篇')

cur.execute("SELECT asset_tags, COUNT(*) FROM wechat_articles WHERE asset_tags != '' GROUP BY asset_tags ORDER BY COUNT(*) DESC LIMIT 10")
print('\n资产标签 Top 10:')
for row in cur.fetchall():
    print(f'  {row[0]}: {row[1]}篇')

cur.execute("SELECT event_tags, COUNT(*) FROM wechat_articles WHERE event_tags != '' GROUP BY event_tags ORDER BY COUNT(*) DESC LIMIT 10")
print('\n事件标签 Top 10:')
for row in cur.fetchall():
    print(f'  {row[0]}: {row[1]}篇')

conn.close()
