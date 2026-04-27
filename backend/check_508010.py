import sqlite3
conn = sqlite3.connect('database/reits.db')
cur = conn.cursor()

cur.execute('SELECT article_id, match_type, score FROM article_fund_tags WHERE fund_code = ?', ('508010',))
rows = cur.fetchall()
print('508010 tagged articles:', len(rows))
for aid, mt, sc in rows[:10]:
    cur.execute('SELECT title FROM wechat_articles WHERE id = ?', (aid,))
    t = cur.fetchone()
    title = t[0][:40] if t else '?'
    print(f'  AID={aid} {mt} score={sc} {title}')

conn.close()
