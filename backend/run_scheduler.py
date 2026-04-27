#!/usr/bin/env python3
"""
后台调度守护进程 — 每30分钟自动同步文章、向量化、打标签
用法: nohup python3 run_scheduler.py &
"""
import time
import logging
from scheduler.tasks import start_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("scheduler_daemon")

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("Starting scheduler daemon (interval: 30min)")
    logger.info("=" * 50)
    
    start_scheduler(interval_minutes=30)
    
    # 保持进程运行
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Scheduler daemon stopped")
