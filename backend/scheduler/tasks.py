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
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from sync_from_wemprss_api import main as sync_main
        sync_main()
        logger.info("[Scheduler] Article sync completed")
    except Exception as e:
        logger.error(f"[Scheduler] Article sync failed: {e}")

    try:
        from migrate_fund_tags import main as tag_main
        tag_main()
        logger.info("[Scheduler] Fund tags updated")
    except Exception as e:
        logger.error(f"[Scheduler] Fund tags failed: {e}")

    try:
        from migrate_vectors_to_milvus import main as vec_main
        vec_main()
        logger.info("[Scheduler] Vector import completed")
    except Exception as e:
        logger.error(f"[Scheduler] Vector import failed: {e}")

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
