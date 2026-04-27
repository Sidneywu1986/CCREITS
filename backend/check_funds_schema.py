import sqlite3
conn = sqlite3.connect('database/reits.db')
cur = conn.cursor()

print('=== FUNDS 表结构 ===')
cur.execute("PRAGMA table_info(funds)")
for col in cur.fetchall():
    print(f"  {col[1]} ({col[2]})")

print()
print('=== 基金行业分布 ===')
cur.execute("SELECT sector_name, COUNT(*) FROM funds GROUP BY sector_name")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}只")

print()
print('=== 示例基金数据 ===')
cur.execute("SELECT fund_code, fund_name, short_name, sector_name FROM funds LIMIT 10")
for row in cur.fetchall():
    print(f"  {row}")

conn.close()
