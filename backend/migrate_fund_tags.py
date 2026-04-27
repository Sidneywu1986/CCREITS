"""
创建 article_fund_tags 表并填充数据
匹配规则：
1. 基金代码 6 位数字匹配
2. 基金名称关键词匹配（提取 fund_name 中的核心词）
"""
import sqlite3
import re

DB_PATH = 'database/reits.db'

def extract_keywords(name: str) -> list:
    """从基金名称提取关键词用于匹配"""
    # 去除通用词
    name = re.sub(r'REIT[\u4e00-\u9fa5]?', '', name, flags=re.I)
    name = re.sub(r'封闭式基础设施证券投资基金', '', name)
    name = re.sub(r'证券投资基金', '', name)
    name = re.sub(r'基础设施', '', name)
    name = re.sub(r'[（(].*?[)）]', '', name)
    # 取2字以上的中文字符片段
    keywords = re.findall(r'[\u4e00-\u9fa5]{2,}', name)
    # 过滤过于通用的词
    stopwords = {'中金', '华夏', '华安', '博时', '平安', '易方达', '嘉实', '富国', '国泰', '招商', '广发', '南方', '鹏华', '建信', '工银', '国金', '红土', '中航', '东吴', '中信', '华泰', '申万', '东证', '国君', '光大', '中银', '民生', '中信建投'}
    # 保留所有关键词，但把2字以上的地名/项目名优先
    result = []
    for kw in keywords:
        if len(kw) >= 2:
            result.append(kw)
    return list(dict.fromkeys(result))  # 去重保持顺序

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. 创建表
    cur.execute('''
    CREATE TABLE IF NOT EXISTS article_fund_tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        article_id INTEGER NOT NULL,
        fund_code VARCHAR(10) NOT NULL,
        match_type VARCHAR(20) DEFAULT 'code',
        score REAL DEFAULT 1.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(article_id, fund_code, match_type)
    )
    ''')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_aft_article ON article_fund_tags(article_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_aft_fund ON article_fund_tags(fund_code)')

    # 2. 清空旧数据
    cur.execute('DELETE FROM article_fund_tags')

    # 3. 加载基金
    cur.execute('SELECT fund_code, fund_name, sector_name, manager FROM funds')
    funds = []
    for row in cur.fetchall():
        code, name, sector, manager = row
        keywords = extract_keywords(name)
        funds.append({
            'code': code,
            'name': name,
            'sector': sector,
            'manager': manager,
            'keywords': keywords
        })

    # 4. 加载文章
    cur.execute('SELECT id, title, content FROM wechat_articles')
    articles = cur.fetchall()

    # 5. 匹配
    insert_data = []
    for article_id, title, content in articles:
        text = (title or '') + ' ' + (content or '')
        for f in funds:
            matched = False
            # 5a. 基金代码匹配
            if re.search(rf'(?<!\d){f["code"]}(?!\d)', text):
                insert_data.append((article_id, f['code'], 'code', 1.0))
                matched = True
            # 5b. 基金名称关键词匹配（至少命中1个>=3字关键词或2个>=2字）
            if not matched and f['keywords']:
                hits_3 = sum(1 for kw in f['keywords'] if len(kw) >= 3 and kw in text)
                hits_2 = sum(1 for kw in f['keywords'] if len(kw) >= 2 and kw in text)
                if hits_3 >= 1 or hits_2 >= 2:
                    insert_data.append((article_id, f['code'], 'name', 0.6))
                    matched = True

    # 6. 批量插入
    cur.executemany(
        'INSERT OR IGNORE INTO article_fund_tags (article_id, fund_code, match_type, score) VALUES (?,?,?,?)',
        insert_data
    )
    conn.commit()

    # 7. 统计
    cur.execute('SELECT COUNT(DISTINCT article_id), COUNT(*) FROM article_fund_tags')
    distinct_articles, total = cur.fetchone()
    print(f'涉及文章数: {distinct_articles}')
    print(f'总标签数: {total}')

    print('\nTop 20 基金覆盖:')
    cur.execute('''
        SELECT fund_code, COUNT(*) as cnt FROM article_fund_tags 
        GROUP BY fund_code ORDER BY cnt DESC LIMIT 20
    ''')
    for code, cnt in cur.fetchall():
        cur.execute('SELECT fund_name FROM funds WHERE fund_code=?', (code,))
        name = cur.fetchone()[0][:20]
        print(f'  {code} {name}: {cnt}篇')

    conn.close()

if __name__ == '__main__':
    main()
