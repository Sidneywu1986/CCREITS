import sqlite3
conn = sqlite3.connect('database/reits.db')
with open('database/rsds_v1.1.2_sqlite.sql', 'r', encoding='utf-8') as f:
    sql = f.read()
conn.executescript(sql)
conn.commit()
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cursor.fetchall()]
print('Total tables:', len(tables))
print('New RSDS tables:')
for t in tables:
    if t.startswith('reit') or t.startswith('reits') or t == 'data_lineage':
        cursor.execute(f'SELECT COUNT(*) FROM {t}')
        count = cursor.fetchone()[0]
        print(f'  {t}: {count} rows')
conn.close()
print('Done.')
