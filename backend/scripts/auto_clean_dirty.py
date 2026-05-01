#!/usr/bin/env python3
"""
自动清洗脏数据脚本
检测标准：
  1. content 长度 > 100KB
  2. 或 HTML 标签占比 > 30%
清洗后：
  - 提取正文 → 更新 content
  - 删除旧向量
  - 标记 vectorized = FALSE
  - 自动重新向量化
  - 同步到 Milvus
"""

import os
import sys
import re
import logging
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.db import get_conn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("auto_clean")

# 白名单：微信/公众号文章正常使用的 HTML 标签（不计入脏数据检测）
NORMAL_TAGS = {
    'p', 'br', 'span', 'div', 'strong', 'b', 'em', 'i', 'u', 's', 'a',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'ul', 'ol', 'li',
    'pre', 'code', 'section', 'article', 'figure', 'figcaption', 'img',
    'video', 'audio', 'source', 'track', 'sub', 'sup', 'del', 'ins',
    'hr', 'center', 'font', 'small', 'big', 'strike', 'tt', 'mark',
}
# 异常标签：出现这些说明是完整 HTML 页面而非正文
ABNORMAL_TAG_RE = re.compile(
    r'<(/?)(html|head|body|script|style|iframe|meta|link|title|form|input|'
    r'button|select|option|textarea|table|tr|td|th|tbody|thead|tfoot|'
    r'nav|header|footer|aside|canvas|svg|embed|object|param|applet|'
    r'frame|frameset|noframes|base|basefont|col|colgroup|datalist|'
    r'fieldset|legend|label|optgroup|output|progress|meter|details|'
    r'summary|dialog|menu|menuitem|template|slot|element)'
    r'(?:\s[^>]*)?>',
    re.IGNORECASE
)


def is_dirty(content: str) -> bool:
    """判断内容是否为脏数据"""
    if not content:
        return False
    # 标准1：长度超过 100KB
    if len(content) > 100000:
        return True
    # 标准2：异常 HTML 标签（非正文标签）占比超过 20%
    abnormal_tags = ABNORMAL_TAG_RE.finditer(content)
    abnormal_chars = sum(len(m.group(0)) for m in abnormal_tags)
    if len(content) > 1000 and abnormal_chars / len(content) > 0.2:
        return True
    return False


def extract_text(html: str) -> str:
    """从 HTML 中提取正文"""
    soup = BeautifulSoup(html, 'lxml')
    # 优先微信正文选择器
    content_div = soup.select_one('#js_content') or soup.select_one('#img-content')
    if content_div:
        text = content_div.get_text(separator='\n', strip=True)
    else:
        # 兜底：清理 script/style 后取文本
        for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
            tag.decompose()
        text = soup.get_text(separator='\n', strip=True)
    # 清理空行
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    text = '\n'.join(lines)
    # 截断到 30KB
    if len(text) > 30000:
        text = text[:30000]
    return text


def find_dirty_articles():
    """查找所有脏数据文章"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, source, title, content, LENGTH(content) as len
            FROM business.wechat_articles
            WHERE content IS NOT NULL AND LENGTH(content) > 1000
            ORDER BY id
        """)
        dirty = []
        for row in cur.fetchall():
            if is_dirty(row['content']):
                dirty.append(dict(row))
        return dirty


def clean_article(article_id: int, new_content: str):
    """清洗单篇文章：更新 content，删除旧向量，标记未向量化"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE business.wechat_articles SET content = %s, vectorized = FALSE WHERE id = %s",
            (new_content, article_id)
        )
        cur.execute("DELETE FROM business.article_vectors WHERE article_id = %s", (article_id,))
        conn.commit()


def delete_article(article_id: int):
    """删除无法修复的文章"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM business.article_vectors WHERE article_id = %s", (article_id,))
        cur.execute("DELETE FROM business.wechat_articles WHERE id = %s", (article_id,))
        conn.commit()


def run_vectorize():
    """运行增量向量化"""
    logger.info("[AutoClean] Running vectorization...")
    from scripts.vectorize_articles import main
    import sys
    old_argv = sys.argv
    sys.argv = ["vectorize_articles.py"]
    try:
        main()
    finally:
        sys.argv = old_argv


def sync_milvus():
    """同步到 Milvus"""
    logger.info("[AutoClean] Syncing to Milvus...")
    from scripts.sync_tfidf_to_milvus import sync
    sync()


def main():
    logger.info("=" * 60)
    logger.info("Auto Clean Dirty Articles")
    logger.info("=" * 60)

    dirty = find_dirty_articles()
    logger.info(f"Found {len(dirty)} dirty articles")

    if not dirty:
        logger.info("No dirty articles, all clean!")
        return

    fixed = 0
    deleted = 0
    for art in dirty:
        try:
            new_text = extract_text(art['content'])
            if len(new_text) < 100:
                logger.warning(f"  ID {art['id']} too short after extract ({len(new_text)} chars), deleting")
                delete_article(art['id'])
                deleted += 1
                continue

            clean_article(art['id'], new_text)
            logger.info(f"  ID {art['id']} | {art['source']} | {art['len']} -> {len(new_text)} chars")
            fixed += 1
        except Exception as e:
            logger.error(f"  ID {art['id']} failed: {e}")

    logger.info(f"Cleaned: {fixed} fixed, {deleted} deleted")

    # 重新向量化
    run_vectorize()

    # 同步到 Milvus
    sync_milvus()

    logger.info("=" * 60)
    logger.info("Auto clean complete!")


if __name__ == "__main__":
    main()
