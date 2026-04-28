"""
后台定时任务 - 每30分钟自动同步文章、打标签、导入向量
"""
import os
import sys
import threading
import logging
import schedule
import time
from datetime import datetime

logger = logging.getLogger("scheduler")


def run_sync_pipeline():
    """完整的同步流水线"""
    logger.info("[Scheduler] Starting sync pipeline...")
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

    # 获取任务锁，防止并发执行
    try:
        from database.task_lock import task_lock
        from core.db import get_conn
        _run_sync_pipeline_locked(get_conn)
    except Exception as e:
        logger.error(f"[Scheduler] Sync pipeline failed to acquire lock or execute: {e}")


def _run_sync_pipeline_locked(get_conn):
    with task_lock('python_scheduler_pipeline', get_conn):
        # 1. 同步新文章
        try:
            from sync_from_wemprss_api import main as sync_main
            sync_main()
            logger.info("[Scheduler] Article sync completed")
        except Exception as e:
            logger.error(f"[Scheduler] Article sync failed: {e}")

        # 2. 基金标签匹配
        logger.info("[Scheduler] Fund tag migration skipped (script not implemented)")

        # 3. LLM 增量标签（新文章自动打 asset/event 标签）
        try:
            from engine.llm_tagger import BatchRetagJob
            job = BatchRetagJob()
            stats = job.run(only_untagged=True, limit=20)
            logger.info(f"[Scheduler] LLM incremental tagging: {stats}")
        except Exception as e:
            logger.error(f"[Scheduler] LLM tagging failed: {e}")

        # 4. 向量导入（BGE-M3 → Milvus）
        try:
            from scripts.migrate_vectors_bge import migrate as vec_main
            vec_main()
            logger.info("[Scheduler] BGE-M3 vector import completed")
        except Exception as e:
            logger.error(f"[Scheduler] BGE-M3 vector import failed: {e}")

        logger.info("[Scheduler] Sync pipeline finished")


def start_scheduler(interval_minutes: int = 30):
    """启动后台调度线程"""
    schedule.every(interval_minutes).minutes.do(run_sync_pipeline)
    logger.info(f"[Scheduler] Registered every {interval_minutes} minutes")

    def loop():
        while True:
            schedule.run_pending()
            time.sleep(1)

    t = threading.Thread(target=loop, daemon=True, name="SchedulerThread")
    t.start()
    logger.info("[Scheduler] Background thread started")
