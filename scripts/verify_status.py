#!/usr/bin/env python3
import sqlite3

DB_PATH = r'D:\tools\消费看板5（前端）\backend\database\reits.db'
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print('='*60)
print('基金状态验证')
print('='*60)
print()

# 检查刚获批的基金
cursor.execute("SELECT code, name, status FROM funds WHERE status = 'approved'")
print('刚获批基金 (approved):')
for row in cursor.fetchall():
    print('  ' + row[0] + ' | ' + row[1] + ' | ' + row[2])

print()

# 统计
cursor.execute("SELECT status, COUNT(*) FROM funds GROUP BY status")
print('统计:')
for row in cursor.fetchall():
    status_name = '已上市' if row[0] == 'listed' else '已获批待上市'
    print('  ' + row[0] + ' (' + status_name + '): ' + str(row[1]) + '只')

conn.close()
print('='*60)
