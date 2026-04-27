#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一数据库连接模块
支持 PostgreSQL（主）和 SQLite（降级兼容）
"""

import os
import logging
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# 优先从环境变量/配置读取
from core.config import settings

DB_TYPE = os.getenv("DB_TYPE", settings.DB_TYPE).lower()

# PostgreSQL DSN
PG_DSN = os.getenv(
    "DATABASE_URL",
    f"postgresql://{settings.PG_CONFIG['user']}:{settings.PG_CONFIG['password']}"
    f"@{settings.PG_CONFIG['host']}:{settings.PG_CONFIG['port']}"
    f"/{settings.PG_CONFIG['database']}"
)

# SQLite 降级路径
SQLITE_PATH = os.getenv("SQLITE_PATH", settings.SQLITE_PATH)


def _get_pg_dsn() -> str:
    """获取 PostgreSQL 连接串"""
    return PG_DSN


def _get_sqlite_path() -> str:
    """获取 SQLite 路径"""
    return SQLITE_PATH


# ============================================================
# 同步连接（psycopg2 / sqlite3）
# ============================================================

@contextmanager
def get_conn():
    """
    获取数据库连接（自动根据 DB_TYPE 选择 PostgreSQL 或 SQLite）
    用法:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT ...")
    """
    if DB_TYPE == "postgres":
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            conn = psycopg2.connect(_get_pg_dsn(), cursor_factory=RealDictCursor)
            try:
                yield conn
            finally:
                conn.close()
        except ImportError:
            logger.error("缺少 psycopg2，请安装: pip install psycopg2-binary")
            raise
    else:
        import sqlite3
        conn = sqlite3.connect(_get_sqlite_path(), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()


@contextmanager
def get_cursor():
    """获取游标（自动提交/回滚）"""
    with get_conn() as conn:
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()


def execute(sql: str, params: tuple = ()) -> int:
    """执行 INSERT/UPDATE/DELETE，返回影响行数"""
    with get_cursor() as cur:
        cur.execute(sql, params)
        return cur.rowcount


def fetchone(sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
    """查询单条记录"""
    with get_cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        if row is None:
            return None
        if DB_TYPE == "postgres":
            return dict(row)
        return dict(row)


def fetchall(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """查询多条记录"""
    with get_cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        if DB_TYPE == "postgres":
            return [dict(r) for r in rows]
        return [dict(r) for r in rows]


def fetchval(sql: str, params: tuple = ()) -> Any:
    """查询单个值"""
    row = fetchone(sql, params)
    if row is None:
        return None
    return next(iter(row.values()))


# ============================================================
# 参数占位符兼容（? → %s）
# ============================================================

def adapt_sql(sql: str) -> str:
    """
    将 SQLite 风格 SQL 适配为 PostgreSQL
    - ? → %s
    - `column` → "column" (PostgreSQL 不需要反引号，但保留兼容)
    """
    if DB_TYPE == "postgres":
        # 替换 ? 为 %s（注意不替换字符串内的 ?）
        # 简单实现：逐个替换不在字符串内的 ?
        result = []
        in_string = False
        string_char = None
        i = 0
        while i < len(sql):
            ch = sql[i]
            if ch in ("'", '"'):
                if not in_string:
                    in_string = True
                    string_char = ch
                elif string_char == ch:
                    # 检查转义
                    if i + 1 < len(sql) and sql[i + 1] == ch:
                        result.append(ch)
                        i += 1
                    else:
                        in_string = False
                        string_char = None
                result.append(ch)
            elif ch == "?" and not in_string:
                result.append("%s")
            else:
                result.append(ch)
            i += 1
        return "".join(result)
    return sql


# ============================================================
# Schema 前缀自动处理
# ============================================================

def table_name(name: str, schema: str = "business") -> str:
    """
    获取带 schema 的表名
    SQLite 不支持 schema，自动去除
    """
    if DB_TYPE == "postgres":
        return f'"{schema}"."{name}"'
    return f'"{name}"'


# ============================================================
# 异步连接（asyncpg）- 供 FastAPI / Tortoise 使用
# ============================================================

async def get_asyncpg_pool():
    """获取 asyncpg 连接池（用于 Tortoise ORM）"""
    import asyncpg
    return await asyncpg.create_pool(dsn=_get_pg_dsn())


# ============================================================
# 兼容旧代码的快捷导入
# ============================================================

# 旧代码中常见的 DB_PATH 变量，现在提供兼容
DB_PATH = _get_sqlite_path() if DB_TYPE == "sqlite" else PG_DSN
