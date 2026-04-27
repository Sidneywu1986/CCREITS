import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

# 更新后的分类关键词（与 announcements.py 保持一致）
CATEGORY_KEYWORDS = {
    'inquiry': ['问询函', '关注函', '监管工作函', '审核问询函', '反馈意见'],
    'dividend': ['分红', '派息', '收益分配', '权益分派', '红利', '分配'],
    'listing': ['上市', '发售', '认购', '招募说明书', '扩募'],
    'disclosure': ['信息披露', '澄清', '风险提示', '停牌', '复牌'],
    'financial': ['年报', '季报', '半年报', '审计', '财务报告', '业绩预告', '报告书', '报告期', '评估报告'],
    'operation': ['运营', '租赁', '出租率', '车流量', '物业', '经营数据', '运营数据']
}

def classify(title):
    # 高确定性财务报告标识（优先匹配，避免被分红/运营等次要关键词覆盖）
    for kw in ('季度报告', '年度报告', '半年度报告'):
        if kw in title:
            return 'financial'
    for cat, kws in CATEGORY_KEYWORDS.items():
        for kw in kws:
            if kw in title:
                return cat
    return 'other'

def main():
    conn = sqlite3.connect('database/reits.db')
    cursor = conn.cursor()
    
    # 获取所有公告
    cursor.execute("SELECT id, title, category FROM announcements")
    rows = cursor.fetchall()
    
    updates = []
    changes = {k: 0 for k in list(CATEGORY_KEYWORDS.keys()) + ['other']}
    
    for id_, title, old_cat in rows:
        new_cat = classify(title)
        if new_cat != old_cat:
            updates.append((new_cat, id_))
            changes[new_cat] += 1
    
    if updates:
        cursor.executemany("UPDATE announcements SET category = ? WHERE id = ?", updates)
        conn.commit()
        print(f"Updated {len(updates)} rows")
    else:
        print("No changes needed")
    
    # 统计各分类数量
    print("\nNew category distribution:")
    cursor.execute("SELECT category, COUNT(*) FROM announcements GROUP BY category ORDER BY COUNT(*) DESC")
    for cat, cnt in cursor.fetchall():
        name = {'dividend':'分红公告','operation':'运营公告','financial':'财务报告',
                'inquiry':'问询函件','listing':'上市公告','disclosure':'信息披露','other':'其他公告'}.get(cat, cat)
        print(f"  {name:10s} ({cat}): {cnt}")
    
    # 显示问询函件样本
    print("\nSample 'inquiry' announcements:")
    cursor.execute("SELECT title FROM announcements WHERE category = 'inquiry' LIMIT 10")
    for row in cursor.fetchall():
        print(f"  • {row[0]}")
    
    conn.close()

if __name__ == '__main__':
    main()
