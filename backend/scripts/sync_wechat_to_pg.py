#!/usr/bin/env python3
"""
同步 we-mp-rss 文章到主库 —— SQLite → PostgreSQL 版
支持：连续空格合并、超长内容预警、增量同步
"""

import os
import sys
import logging
import re
from datetime import datetime
from typing import List, Dict, Optional
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.db import get_conn

# 源数据库（we-mp-rss SQLite）
SOURCE_DB_PATH = os.getenv("WEMP_SOURCE_DB", "./scripts/we_mp_rss_source.db")
if not os.path.isabs(SOURCE_DB_PATH):
    SOURCE_DB_PATH = os.path.join(os.path.dirname(__file__), os.path.basename(SOURCE_DB_PATH))

BATCH_SIZE = 100
CONTENT_WARN_THRESHOLD = 50000

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("wechat_sync")


def fetch_source_articles(conn, last_sync: Optional[datetime] = None) -> List[Dict]:
    # Build mp_id → mp_name mapping
    mp_map = {}
    cur = conn.cursor()
    cur.execute("SELECT id, mp_name FROM feeds")
    for row in cur.fetchall():
        mp_map[row[0]] = row[1]

    sql = """
    SELECT a.title, a.url as link, a.publish_time as published,
           a.content as raw_content, a.mp_id
    FROM articles a
    WHERE a.content IS NOT NULL 
      AND length(trim(a.content)) > 100
    """
    params = []
    if last_sync:
        # Convert datetime to unix timestamp for comparison
        import time
        ts = int(time.mktime(last_sync.timetuple()))
        sql += " AND a.publish_time > ?"
        params.append(ts)
    sql += " ORDER BY a.publish_time DESC"

    cur.execute(sql, params)
    results = []
    for row in cur.fetchall():
        results.append({
            "title": row[0],
            "link": row[1],
            "published": row[2],
            "raw_content": row[3],
            "mp_id": row[4],
            "source": mp_map.get(row[4], row[4])
        })
    return results


def clean_html(raw_html: str):
    text = re.sub(r"<[^>]+>", "", raw_html)
    text = re.sub(r'[\s\u3000]+', ' ', text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)

    junk = ["本文来源", "免责声明", "推荐阅读", "关注公众号",
            "点击在看", "原创声明", "赞赏", "转发", "在看"]
    lines = []
    for line in text.split("\n"):
        line = line.strip()
        if any(line.startswith(j) for j in junk):
            continue
        if len(line) > 0:
            lines.append(line)

    cleaned = "\n".join(lines)
    return cleaned, len(cleaned)


def upsert_to_target(articles: List[Dict]):
    with get_conn() as conn:
        cur = conn.cursor()
        inserted = 0
        for a in articles:
            content, length = clean_html(a["raw_content"])

            if length > CONTENT_WARN_THRESHOLD:
                logger.warning(f"超长文章: {a['title'][:40]} ({length}字), 已截断")
                content = content[:CONTENT_WARN_THRESHOLD]

            # Convert unix timestamp to ISO datetime string
            published = None
            if a["published"]:
                published = datetime.fromtimestamp(a["published"]).isoformat()

            # 检查是否已存在
            cur.execute("SELECT 1 FROM business.wechat_articles WHERE link = %s", (a["link"],))
            if cur.fetchone():
                continue

            cur.execute("""
                INSERT INTO business.wechat_articles
                    (source, title, link, published, content, vectorized)
                VALUES (%s, %s, %s, %s, %s, FALSE)
            """, (a["source"], a["title"], a["link"], published, content))
            inserted += 1

        conn.commit()
        logger.info(f"Inserted {inserted} new articles")


def get_last_sync_time() -> Optional[datetime]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT MAX(published) FROM business.wechat_articles")
        row = cur.fetchone()
        if row and row[0]:
            dt_val = row[0]
            if isinstance(dt_val, str):
                return datetime.fromisoformat(dt_val.replace('Z', '+00:00'))
            elif isinstance(dt_val, datetime):
                return dt_val
    return None


def main():
    logger.info("开始同步 we-mp-rss 文章...")
    logger.info(f"源库: {SOURCE_DB_PATH}")

    if not os.path.exists(SOURCE_DB_PATH):
        logger.error(f"源数据库不存在: {SOURCE_DB_PATH}")
        sys.exit(1)

    source_conn = sqlite3.connect(SOURCE_DB_PATH)

    try:
        last_sync = get_last_sync_time()
        logger.info(f"增量锚点: {last_sync}")

        articles = fetch_source_articles(source_conn, last_sync)
        logger.info(f"源库待同步: {len(articles)} 篇")

        if articles:
            upsert_to_target(articles)
            with get_conn() as conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM business.wechat_articles")
                total = cur.fetchone()[0]
                logger.info(f"成功入库: {len(articles)} 篇，目标库总计: {total} 篇")
        else:
            logger.info("无新文章，跳过")

    finally:
        source_conn.close()


if __name__ == "__main__":
    main()
