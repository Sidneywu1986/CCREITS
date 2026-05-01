#!/usr/bin/env python3
"""重新校准 wechat_articles 情感标签，重点修复极端值"""
import sys
sys.path.insert(0, sys.path[0] + '/..')
from engine.sentiment import SentimentEngine
import logging
logger = logging.getLogger(__name__)

engine = SentimentEngine()
logger.info("开始重打极端值文章 (score=0, ±1.0)...")
count = engine.batch_tag_articles(retag_extremes=True)
logger.info(f"完成，共处理 {count} 篇文章")
