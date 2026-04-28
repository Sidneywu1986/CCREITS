#!/usr/bin/env python3
"""
PostgreSQL advisory lock 封装 - Python 版
用于调度器任务互斥
"""
import hashlib
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)


def _hash_task_name(name: str) -> int:
    """将任务名映射为 32 位整数锁 key"""
    h = hashlib.md5(name.encode()).hexdigest()
    return int(h[:8], 16)


@contextmanager
def task_lock(task_name: str, conn_factory=None):
    """
    上下文管理器：获取 advisory lock，任务完成后释放

    用法:
        from database.task_lock import task_lock
        from core.db import get_conn

        with task_lock('article_sync', get_conn):
            run_sync_pipeline()
    """
    key = _hash_task_name(task_name)

    def _acquire_and_yield(conn_ctx):
        with conn_ctx as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT pg_advisory_lock(%s)", (key,))
            logger.info(f"[Lock] 获取成功: {task_name} (key={key})")
            try:
                yield conn
            finally:
                cursor.execute("SELECT pg_advisory_unlock(%s)", (key,))
                logger.info(f"[Lock] 释放: {task_name} (key={key})")

    if conn_factory is None:
        from core.db import get_conn
        yield from _acquire_and_yield(get_conn)
    else:
        yield from _acquire_and_yield(conn_factory())
