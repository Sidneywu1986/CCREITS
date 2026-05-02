#!/usr/bin/env python3
"""
LLM 驱动标签引擎 — Day 2
一次 API 调用输出：情感/资产/事件/基金/结构化数据
适配 SQLite wechat_articles 表
"""

import os
import sys
import json
import re
import logging
import time
from typing import List, Dict, Optional
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# 加载 .env 文件（确保 API key 可用）
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
except ImportError:
    pass

from core.db import get_conn

logger = logging.getLogger("llm_tagger")

CHECKPOINT_FILE = os.path.join(os.path.dirname(__file__), "..", "scripts", ".retag_checkpoint.json")

# DeepSeek API 配置（从环境变量读取）
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_PRO_MODEL", "deepseek-v4-pro")

TAG_PROMPT = """你是REITs行业专业分析师。请仔细阅读以下公众号文章，提取结构化信息。

文章标题：{title}
发布时间：{published}
正文：{content}

请按以下JSON格式输出（不要输出任何其他内容）：

{{
  "sentiment": {{
    "score": -3到+3的整数（-3极度悲观，+3极度乐观，0中性）,
    "emotion": "恐慌/贪婪/乐观/悲观/中性/谨慎/兴奋/失望 之一",
    "confidence": 0到1之间
  }},
  "assets": [
    "资产类型标签，如：产业园/仓储物流/数据中心/能源环保/高速公路/保障性租赁住房/购物中心/办公楼/新能源/水利/铁路"
  ],
  "events": [
    "事件类型标签，如：分红/扩募/并购/增持/减持/解禁/政策发布/监管问询/出租率变化/租金调整/客流变化/估值调整/业绩发布/解禁/回购"
  ],
  "funds": [
    {{"code": "6位基金代码或简称", "name": "基金全称", "mention_type": "主体/对比/引用"}}
  ],
  "extractions": [
    {{
      "key": "指标名称，如：出租率/分派率/每份分红/租金增长率/建筑面积/评估价值",
      "value": "具体数值",
      "unit": "单位，如：%/元/万元/亿元/平方米",
      "context": "原文中的上下文片段，20字以内",
      "time_ref": "时间参照，如：2024Q3/2024年/截至2024年底"
    }}
  ],
  "summary": "一句话总结文章核心观点，30字以内"
}}

注意：
- 如果文章不涉及具体基金，funds留空数组
- 如果文章没有具体数字，extractions留空数组
- 资产标签必须精确到细分业态，不要笼统写"基础设施"
- 事件标签要具体，不要写"其他"
- 情感判断要基于全文基调，不要只看标题
"""


class LLMTagEngine:
    """LLM 驱动标签引擎"""

    def __init__(self):
        self._client = None
        self.batch_size = 5
        self._ensure_client()

    def _ensure_client(self):
        if self._client is not None:
            return
        try:
            import openai
            self._client = openai.OpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL,
                timeout=120,
            )
            logger.info(f"LLM client initialized: {DEEPSEEK_BASE_URL} model={DEEPSEEK_MODEL}")
        except (ImportError, RuntimeError, ValueError) as e:
            logger.error(f"Failed to init LLM client: {e}")
            raise

    def tag_article(self, article: dict) -> Optional[dict]:
        """单篇标签提取"""
        try:
            content = article.get("content", "")[:4000]
            published = article.get("published", "")
            if hasattr(published, "isoformat"):
                published = published.isoformat()
            else:
                published = str(published) if published else ""

            prompt = TAG_PROMPT.format(
                title=article.get("title", ""),
                published=published,
                content=content,
            )

            response = self._client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1500,
            )

            text = response.choices[0].message.content
            result = self._safe_parse_json(text)
            return result

        except (RuntimeError, ValueError, ConnectionError) as e:
            logger.error(f"Article {article.get('id')} tagging failed: {e}")
            return None

    def tag_articles(self, articles: List[dict]) -> List[Optional[dict]]:
        """批量标签提取（同步串行，控制速率）"""
        results = []
        for i, art in enumerate(articles):
            logger.info(f"Tagging {i+1}/{len(articles)}: id={art.get('id')} {art.get('title', '')[:30]}...")
            result = self.tag_article(art)
            results.append(result)
            # 每5篇暂停1秒，控制API速率
            if i % 5 == 4:
                time.sleep(1)
        return results

    def _safe_parse_json(self, text: str) -> Optional[dict]:
        """安全解析LLM输出的JSON"""
        if not text:
            return None
        # 尝试提取JSON块
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if not json_match:
            return None
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            # 尝试修复常见JSON错误
            fixed = text.replace("'", '"').replace('\n', ' ')
            json_match2 = re.search(r'\{.*\}', fixed, re.DOTALL)
            if json_match2:
                try:
                    return json.loads(json_match2.group())
                except:
                    pass
            return None


def ensure_extractions_table(conn):
    """创建 article_extractions 表（如果不存在）"""
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS business.article_extractions (
        id SERIAL PRIMARY KEY,
        article_id INTEGER NOT NULL,
        key VARCHAR(100) NOT NULL,
        value TEXT NOT NULL,
        unit VARCHAR(50),
        context TEXT,
        time_ref VARCHAR(50),
        source VARCHAR(20) DEFAULT 'llm',
        extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        confidence_score NUMERIC(4,2) DEFAULT 0.8
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ext_article ON business.article_extractions(article_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ext_key ON business.article_extractions(key)")
    conn.commit()


def save_tags_to_db(conn, article_id: int, tags: dict):
    """保存标签到数据库"""
    now = datetime.now().isoformat()
    cur = conn.cursor()

    # 1. 情感标签
    sentiment = tags.get("sentiment", {})
    score = sentiment.get("score", 0)
    emotion = sentiment.get("emotion", "中性")
    confidence = sentiment.get("confidence", 0.5)

    cur.execute(
        """UPDATE business.wechat_articles SET
            sentiment_score = %s,
            emotion_tag = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s""",
        (score, emotion, article_id),
    )

    # 2. 资产标签
    assets = tags.get("assets", [])
    asset_str = ",".join(assets) if assets else ""

    # 3. 事件标签
    events = tags.get("events", [])
    event_str = ",".join(events) if events else ""

    # 4. 基金关联
    funds = tags.get("funds", [])
    related_codes = []
    for f in funds:
        code = f.get("code", "")
        if code and len(code) == 6 and code.isdigit():
            related_codes.append(code)

    cur.execute(
        """UPDATE business.wechat_articles SET
            asset_tags = %s,
            event_tags = %s,
            related_funds = %s
        WHERE id = %s""",
        (asset_str, event_str, json.dumps(related_codes) if related_codes else None, article_id),
    )

    # 5. 写入 article_fund_tags
    for code in related_codes:
        cur.execute(
            """INSERT INTO business.article_fund_tags (article_id, fund_code)
               VALUES (%s, %s)
               ON CONFLICT (article_id, fund_code) DO NOTHING""",
            (article_id, code),
        )

    # 6. 结构化数据提取
    ensure_extractions_table(conn)
    for ext in tags.get("extractions", []):
        cur.execute(
            """INSERT INTO business.article_extractions
                (article_id, key, value, unit, context, time_ref, source, extracted_at, confidence_score)
            VALUES (%s, %s, %s, %s, %s, %s, 'llm', %s, 0.8)""",
            (
                article_id,
                ext.get("key", ""),
                ext.get("value", ""),
                ext.get("unit", ""),
                ext.get("context", ""),
                ext.get("time_ref", ""),
                now,
            ),
        )

    conn.commit()


def load_checkpoint() -> dict:
    try:
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"last_processed": 0, "stats": {}}


def save_checkpoint(idx: int, stats: dict):
    os.makedirs(os.path.dirname(CHECKPOINT_FILE), exist_ok=True)
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_processed": idx, "stats": stats}, f, ensure_ascii=False, indent=2)


def fetch_target_articles(conn, only_untagged: bool = False, limit: Optional[int] = None) -> List[dict]:
    cur = conn.cursor()
    if only_untagged:
        # 只补打 asset_tags 或 event_tags 为空的文章
        sql = """SELECT id, source, title, published, content
            FROM business.wechat_articles
            WHERE content IS NOT NULL AND length(content) > 50
              AND (asset_tags IS NULL OR asset_tags = ''
                   OR event_tags IS NULL OR event_tags = '[]'::jsonb)
            ORDER BY id"""
    else:
        sql = """SELECT id, source, title, published, content
            FROM business.wechat_articles
            WHERE content IS NOT NULL AND length(content) > 50
            ORDER BY id"""
    if limit:
        sql += f" LIMIT {limit}"
    cur.execute(sql)
    return [dict(r) for r in cur.fetchall()]


class BatchRetagJob:
    """批量补打标签作业"""

    def __init__(self):
        self.engine = LLMTagEngine()
        self.stats = {"total": 0, "processed": 0, "success": 0, "failed": 0, "start_time": None}

    def run(self, only_untagged: bool = False, limit: Optional[int] = None):
        self.stats["start_time"] = datetime.now().isoformat()
        with get_conn() as conn:
            articles = fetch_target_articles(conn, only_untagged=only_untagged, limit=limit)
            self.stats["total"] = len(articles)
            logger.info(f"Batch retag start: {len(articles)} articles")

            checkpoint = load_checkpoint()
            start_idx = checkpoint.get("last_processed", 0)

            for i, article in enumerate(articles[start_idx:], start=start_idx):
                if i % 10 == 0:
                    save_checkpoint(i, self.stats)
                    logger.info(f"Progress: {i}/{len(articles)} ({i/len(articles)*100:.1f}%)")

                tags = self.engine.tag_article(article)
                if tags:
                    save_tags_to_db(conn, article["id"], tags)
                    self.stats["success"] += 1
                else:
                    self.stats["failed"] += 1

                self.stats["processed"] += 1

                if i % 5 == 4:
                    time.sleep(1)

            save_checkpoint(len(articles), self.stats)
            logger.info(
                f"Batch retag complete: success={self.stats['success']}, failed={self.stats['failed']}"
            )
        return self.stats


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    job = BatchRetagJob()
    # 默认先跑未标签的文章
    stats = job.run(only_untagged=True)
    logger.info(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
