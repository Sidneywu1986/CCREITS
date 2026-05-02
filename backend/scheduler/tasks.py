"""
后台定时任务
- 每30分钟：同步文章、清洗、标签、向量化、Milvus同步
- 每天08:00：晨间通讯社
- 每天13:00：午间悄悄话
"""
import os
import sys
import threading
import logging
import schedule
import time
import asyncio
import psycopg2
from datetime import datetime

logger = logging.getLogger("scheduler")


# =============================================================================
# 1. 文章同步流水线 (每30分钟)
# =============================================================================

def run_sync_pipeline():
    """完整的同步流水线"""
    logger.info("[Scheduler] Starting sync pipeline...")
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

    try:
        from database.task_lock import task_lock
        from core.db import get_conn
        _run_sync_pipeline_locked(get_conn)
    except (ImportError, RuntimeError, ValueError) as e:
        logger.error(f"[Scheduler] Sync pipeline failed: {e}")


def _run_sync_pipeline_locked(get_conn):
    with task_lock('python_scheduler_pipeline', get_conn):
        # 1. 同步新文章
        try:
            from sync_from_wemprss_api import main as sync_main
            sync_main()
            logger.info("[Scheduler] Article sync completed")
        except (ImportError, RuntimeError, ValueError) as e:
            logger.error(f"[Scheduler] Article sync failed: {e}")

        # 2. 自动清洗脏数据
        try:
            from scripts.auto_clean_dirty import main as clean_main
            clean_main()
            logger.info("[Scheduler] Auto clean completed")
        except (ImportError, RuntimeError, ValueError) as e:
            logger.error(f"[Scheduler] Auto clean failed: {e}")

        # 3. 基金标签匹配
        logger.info("[Scheduler] Fund tag migration skipped")

        # 4. LLM 增量标签
        try:
            from engine.llm_tagger import BatchRetagJob
            job = BatchRetagJob()
            stats = job.run(only_untagged=True, limit=20)
            logger.info(f"[Scheduler] LLM tagging: {stats}")
        except (ImportError, RuntimeError, ValueError) as e:
            logger.error(f"[Scheduler] LLM tagging failed: {e}")

        # 5. TF-IDF 增量向量化
        try:
            from scripts.vectorize_articles import main as tfidf_main
            import sys
            old_argv = sys.argv
            sys.argv = ["vectorize_articles.py"]
            tfidf_main()
            sys.argv = old_argv
            logger.info("[Scheduler] TF-IDF vectorization completed")
        except (ImportError, RuntimeError, ValueError) as e:
            logger.error(f"[Scheduler] TF-IDF vectorization failed: {e}")

        # 6. TF-IDF 同步到 Milvus
        try:
            from scripts.sync_tfidf_to_milvus import sync as tfidf_sync
            tfidf_sync()
            logger.info("[Scheduler] TF-IDF Milvus sync completed")
        except (ImportError, RuntimeError, ValueError) as e:
            logger.error(f"[Scheduler] TF-IDF Milvus sync failed: {e}")

        logger.info("[Scheduler] Sync pipeline finished")


# =============================================================================
# 2. Agents 剧场秀定时触发
# =============================================================================

def run_morning_news():
    """每天08:00 晨间通讯社"""
    logger.info("[Agents] Running morning news...")
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    try:
        from agents.morning_news import get_morning_engine
        from core.db import get_conn
        engine = get_morning_engine()
        result = asyncio.run(engine.run_morning_broadcast())
        logger.info(f"[Agents] Morning news generated: {result.get('bulletin', {}).get('has_news', False)}")
        # 保存到数据库
        with get_conn() as conn:
            cur = conn.cursor()
            import json
            cur.execute('''
                INSERT INTO business.agent_shows (slot_id, slot_name, content, show_date)
                VALUES (%s, %s, %s, CURRENT_DATE)
                ON CONFLICT (slot_id, show_date) DO UPDATE
                SET content = EXCLUDED.content, created_at = CURRENT_TIMESTAMP
            ''', ('morning_news', '🌍 晨间通讯社', json.dumps(result)))
            conn.commit()
    except (ImportError, RuntimeError, psycopg2.Error, ValueError) as e:
        logger.error(f"[Agents] Morning news failed: {e}")


def run_lunch_whisper():
    """每天13:00 午间悄悄话"""
    logger.info("[Agents] Running lunch whisper...")
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    try:
        from agents.lunch_whisper import get_lunch_whisper
        from core.db import get_conn
        engine = get_lunch_whisper()
        morning_summary = ""
        result = asyncio.run(engine.generate_topic(morning_summary))
        logger.info(f"[Agents] Lunch whisper topic: {result.get('topic', '')}")
        # 保存到数据库
        with get_conn() as conn:
            cur = conn.cursor()
            import json
            cur.execute('''
                INSERT INTO business.agent_shows (slot_id, slot_name, content, show_date)
                VALUES (%s, %s, %s, CURRENT_DATE)
                ON CONFLICT (slot_id, show_date) DO UPDATE
                SET content = EXCLUDED.content, created_at = CURRENT_TIMESTAMP
            ''', ('lunch', '🌿 午间悄悄话', json.dumps(result)))
            conn.commit()
    except (ImportError, RuntimeError, psycopg2.Error, ValueError) as e:
        logger.error(f"[Agents] Lunch whisper failed: {e}")


def run_afternoon_show():
    """每天14:00 午盘热点剧场"""
    logger.info("[Agents] Afternoon show started")
    # TODO: 集成 supervisor 自动对戏


def run_morning_show():
    """每天09:30 早盘热点剧场"""
    logger.info("[Agents] Morning show started")
    # TODO: 集成 supervisor 自动对戏


# =============================================================================
# 3. 公告同步 (每4小时增量同步)
# =============================================================================

def run_announcement_sync():
    """增量同步：只同步最近7天的新公告"""
    logger.info("[Scheduler] Starting incremental announcement sync (last 7 days)...")
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    try:
        from crawlers.cninfo_db_sync import sync_single_fund
        from crawlers.cninfo_crawler import CNInfoCrawler
        from datetime import datetime, timedelta
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        total_inserted = 0
        total_skipped = 0
        success_count = 0
        
        for code in sorted(CNInfoCrawler.REIT_CODE_MAPPING.keys()):
            try:
                result = sync_single_fund(
                    code,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if result['success']:
                    total_inserted += result['inserted']
                    total_skipped += result['skipped']
                    success_count += 1
                else:
                    logger.warning(f"[Scheduler] {code} sync returned error: {result.get('error')}")
            except Exception as e:
                logger.error(f"[Scheduler] {code} sync failed: {e}")
        
        logger.info(
            f"[Scheduler] Incremental sync done: {success_count}/{len(CNInfoCrawler.REIT_CODE_MAPPING)} "
            f"funds, inserted={total_inserted}, skipped={total_skipped}"
        )
    except (ImportError, RuntimeError, psycopg2.Error, ValueError) as e:
        logger.error(f"[Scheduler] Announcement sync failed: {e}")


# =============================================================================
# 启动调度器
# =============================================================================

def start_scheduler(interval_minutes: int = 30):
    """启动后台调度线程"""
    # 文章同步：每30分钟
    schedule.every(interval_minutes).minutes.do(run_sync_pipeline)
    logger.info(f"[Scheduler] Sync pipeline every {interval_minutes}min")

    # Agents 剧场秀：固定时间点
    schedule.every().day.at("08:00").do(run_morning_news)
    schedule.every().day.at("09:30").do(run_morning_show)
    schedule.every().day.at("13:00").do(run_lunch_whisper)
    schedule.every().day.at("14:00").do(run_afternoon_show)
    logger.info("[Scheduler] Agents shows: 08:00(morning_news) 09:30(morning) 13:00(lunch) 14:00(afternoon)")

    # 公告同步：每4小时
    schedule.every(4).hours.do(run_announcement_sync)
    logger.info("[Scheduler] Announcement sync every 4 hours")

    def loop():
        while True:
            schedule.run_pending()
            time.sleep(1)

    t = threading.Thread(target=loop, daemon=True, name="SchedulerThread")
    t.start()
    logger.info("[Scheduler] Background thread started")
