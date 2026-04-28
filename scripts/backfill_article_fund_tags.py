#!/usr/bin/env python3
"""
文章-基金关联回溯脚本
用关键词匹配（基金代码 + 基金名称）给已有文章打标签
"""
import json
import re
import sys
from collections import defaultdict

sys.path.insert(0, 'backend')
from core.db import get_conn


def normalize_name(name: str) -> str:
    """提取基金名称中的核心识别部分"""
    # 去掉常见后缀
    suffixes = ['REIT', '封闭式基础设施', '基础设施', '证券投资基金', '基金']
    core = name
    for s in suffixes:
        core = core.replace(s, '')
    return core.strip()


def extract_fund_codes(text: str, valid_codes: set) -> set:
    """从文本中提取有效的6位基金代码"""
    codes = set()
    for m in re.finditer(r'\b(\d{6})\b', text):
        code = m.group(1)
        if code in valid_codes:
            codes.add(code)
    return codes


def match_fund_names(text: str, funds: list) -> set:
    """从文本中匹配基金名称"""
    matched = set()
    for fund in funds:
        code = fund['fund_code']
        name = fund['fund_name']
        # 精确匹配全称
        if name in text:
            matched.add(code)
            continue
        # 匹配核心名称（去掉REIT等后缀）
        core = normalize_name(name)
        if core and len(core) >= 4 and core in text:
            matched.add(code)
    return matched


def backfill():
    with get_conn() as conn:
        cur = conn.cursor()

        # 1. 加载所有基金
        cur.execute("SELECT fund_code, fund_name FROM business.funds ORDER BY fund_code")
        funds = [{'fund_code': r['fund_code'], 'fund_name': r['fund_name']} for r in cur.fetchall()]
        valid_codes = {f['fund_code'] for f in funds}
        print(f"加载 {len(funds)} 只基金")

        # 2. 加载所有文章
        cur.execute("""
            SELECT id, title, COALESCE(content, '') as content
            FROM business.wechat_articles
            ORDER BY id
        """)
        articles = [{'id': r['id'], 'title': r['title'], 'content': r['content']} for r in cur.fetchall()]
        print(f"加载 {len(articles)} 篇文章")

        # 3. 逐篇匹配
        total_tags = 0
        tagged_articles = 0
        for art in articles:
            text = art['title'] + ' ' + art['content']
            matched_codes = extract_fund_codes(text, valid_codes)
            matched_codes |= match_fund_names(text, funds)

            if matched_codes:
                # 更新 related_funds
                cur.execute("""
                    UPDATE business.wechat_articles
                    SET related_funds = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (json.dumps(sorted(matched_codes)), art['id']))

                # 插入 article_fund_tags
                for code in matched_codes:
                    cur.execute("""
                        INSERT INTO business.article_fund_tags (article_id, fund_code)
                        VALUES (%s, %s)
                        ON CONFLICT (article_id, fund_code) DO NOTHING
                    """, (art['id'], code))

                total_tags += len(matched_codes)
                tagged_articles += 1

        conn.commit()

        print(f"\n完成: {tagged_articles}/{len(articles)} 篇文章有关联")
        print(f"共生成 {total_tags} 条 article_fund_tags")


if __name__ == '__main__':
    backfill()
