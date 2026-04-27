#!/usr/bin/env python3
"""
给历史文章打情感标签
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.db import get_conn
from engine.sentiment import get_sentiment_engine

e = get_sentiment_engine()
count = e.batch_tag_articles()
print(f"情感打标完成：{count} 篇")

# 展示分布
with get_conn() as conn:
    cur = conn.cursor()
    cur.execute("""
        SELECT emotion_tag, COUNT(*), AVG(sentiment_score) 
        FROM business.wechat_articles 
        WHERE sentiment_score != 0 
        GROUP BY emotion_tag
    """)
    print("\n情感分布：")
    for row in cur.fetchall():
        print(f"  {row['emotion_tag']}: {row['count']}篇 (avg_score={row['avg']:.3f})")
