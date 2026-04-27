#!/usr/bin/env python3
"""
LLM Tagger 测试 — Day 2
取 3 篇文章，测试标签提取质量和 API 成本/耗时
"""

import os
import sys
import time
import logging
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_llm_tagger")

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "reits.db")


def fetch_sample_articles(limit: int = 3) -> list:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        "SELECT id, title, published, content FROM wechat_articles WHERE content IS NOT NULL AND length(content) > 200 ORDER BY id LIMIT ?",
        (limit,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def main():
    logger.info("=" * 60)
    logger.info("Day 2: LLM tagger test (3 articles)")
    logger.info("=" * 60)

    articles = fetch_sample_articles(limit=3)
    logger.info(f"Fetched {len(articles)} articles")

    from engine.llm_tagger import LLMTagEngine

    engine = LLMTagEngine()
    total_time = 0
    total_tokens = 0

    for i, art in enumerate(articles):
        logger.info(f"\n--- Article {i+1}/{len(articles)}: id={art['id']} ---")
        logger.info(f"Title: {art['title']}")

        t0 = time.time()
        result = engine.tag_article(art)
        elapsed = time.time() - t0
        total_time += elapsed

        if result:
            logger.info(f"Success in {elapsed:.1f}s")
            sentiment = result.get("sentiment", {})
            logger.info(f"  Sentiment: score={sentiment.get('score')} emotion={sentiment.get('emotion')} confidence={sentiment.get('confidence')}")
            logger.info(f"  Assets: {result.get('assets', [])}")
            logger.info(f"  Events: {result.get('events', [])}")
            logger.info(f"  Funds: {result.get('funds', [])}")
            logger.info(f"  Extractions: {len(result.get('extractions', []))} items")
            for ext in result.get("extractions", [])[:3]:
                logger.info(f"    - {ext.get('key')}={ext.get('value')} {ext.get('unit')} ({ext.get('context')})")
            logger.info(f"  Summary: {result.get('summary', '')}")
        else:
            logger.warning(f"Failed in {elapsed:.1f}s")

        # 每篇之间暂停，控制速率
        if i < len(articles) - 1:
            time.sleep(2)

    logger.info(f"\n=== Summary ===")
    logger.info(f"Total time: {total_time:.1f}s for {len(articles)} articles")
    logger.info(f"Avg per article: {total_time/len(articles):.1f}s")
    logger.info(f"Estimated cost (DeepSeek flash): ~{len(articles)*4000*0.001/1000:.3f} yuan")


if __name__ == "__main__":
    main()
