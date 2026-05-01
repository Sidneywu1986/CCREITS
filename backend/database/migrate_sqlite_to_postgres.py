#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite → PostgreSQL 数据迁移脚本
用法:
    python migrate_sqlite_to_postgres.py

环境变量:
    SQLITE_PATH      - SQLite 数据库路径 (默认: ../database/reits.db)
    POSTGRES_DSN     - PostgreSQL 连接串 (默认: postgresql://postgres:postgres@localhost:5432/reits)
    DRY_RUN          - 仅预览，不写入 (默认: false)
"""

import os
import sys
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# 配置
SQLITE_PATH = os.getenv("SQLITE_PATH", str(Path(__file__).parent / "reits.db"))
POSTGRES_DSN = os.getenv("POSTGRES_DSN")
if not POSTGRES_DSN:
    pg_user = os.getenv("PG_USER", "postgres")
    pg_password = os.getenv("PG_PASSWORD", "")
    pg_host = os.getenv("PG_HOST", "localhost")
    pg_port = os.getenv("PG_PORT", "5432")
    pg_db = os.getenv("PG_DATABASE", "reits")
    if pg_password:
        POSTGRES_DSN = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"
    else:
        POSTGRES_DSN = f"postgresql://{pg_user}@{pg_host}:{pg_port}/{pg_db}"
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

# 表映射: (sqlite_table, postgres_table, schema, column_mapping)
# column_mapping: {sqlite_col: postgres_col}
TABLE_MAPPINGS = [
    # 基础业务表
    (
        "funds",
        "funds",
        "business",
        {
            "code": "fund_code",
            "name": "fund_name",
            "sector": "sector",
            "sector_name": "sector_name",
            "manager": "manager",
            "listing_date": "listing_date",
            "scale": "scale",
            "nav": "nav",
            "debt_ratio": "debt_ratio",
            "property_type": "property_type",
            "remaining_years": "remaining_years",
            "circulating_shares": "circulating_shares",
            "institution_hold": "institution_hold",
            "created_at": "created_at",
            "updated_at": "updated_at",
        }
    ),
    (
        "quotes",
        "quotes",
        "business",
        {
            "id": "id",
            "fund_code": "fund_code",
            "price": "price",
            "change_percent": "change_percent",
            "change_amount": "change_amount",
            "volume": "volume",
            "premium": "premium",
            "yield": "yield",
            "market_cap": "market_cap",
            "updated_at": "updated_at",
            "created_at": "created_at",
        }
    ),
    (
        "price_history",
        "price_history",
        "business",
        {
            "id": "id",
            "fund_code": "fund_code",
            "date": "trade_date",
            "open": "open_price",
            "close": "close_price",
            "high": "high_price",
            "low": "low_price",
            "volume": "volume",
            "created_at": "created_at",
        }
    ),
    (
        "announcements",
        "announcements",
        "business",
        {
            "id": "id",
            "fund_code": "fund_code",
            "title": "title",
            "category": "category",
            "summary": "summary",
            "publish_date": "publish_date",
            "source_url": "source_url",
            "pdf_url": "pdf_url",
            "exchange": "exchange",
            "confidence": "confidence",
            "is_read": "is_read",
            "created_at": "created_at",
        }
    ),
    (
        "dividends",
        "dividends",
        "business",
        {
            "id": "id",
            "fund_code": "fund_code",
            "dividend_date": "dividend_date",
            "dividend_amount": "dividend_amount",
            "record_date": "record_date",
            "ex_dividend_date": "ex_dividend_date",
            "created_at": "created_at",
        }
    ),
    (
        "daily_data",
        "price_history",
        "business",
        {
            "id": "id",
            "fund_code": "fund_code",
            "trade_date": "trade_date",
            "open_price": "open_price",
            "close_price": "close_price",
            "high": "high_price",
            "low": "low_price",
            "volume": "volume",
            "amount": "amount",
            "created_at": "created_at",
        }
    ),
    (
        "market_indices",
        "market_indices",
        "business",
        {
            "code": "code",
            "name": "name",
            "value": "value",
            "change": "change_value",
            "change_percent": "change_percent",
            "source": "source",
            "updated_at": "updated_at",
            "created_at": "created_at",
        }
    ),
    (
        "data_sources",
        "data_sources",
        "business",
        {
            "id": "id",
            "data_type": "data_type",
            "source_name": "source_name",
            "source_url": "source_url",
            "last_updated": "last_updated",
            "update_count": "update_count",
            "status": "status",
            "error_msg": "error_msg",
            "created_at": "created_at",
        }
    ),
    (
        "update_logs",
        "update_logs",
        "business",
        {
            "id": "id",
            "data_type": "data_type",
            "source": "source",
            "status": "status",
            "records_count": "records_count",
            "duration_ms": "duration_ms",
            "error_msg": "error_msg",
            "created_at": "created_at",
        }
    ),
    # 兼容 fund_analysis.py 查询的 fund_prices 表
    (
        "fund_prices",
        "fund_prices",
        "business",
        {
            "id": "id",
            "fund_code": "fund_code",
            "trade_date": "trade_date",
            "close_price": "close_price",
            "change_pct": "change_pct",
            "volume": "volume",
            "premium_rate": "premium_rate",
            "yield": "yield",
            "created_at": "created_at",
        }
    ),
    # 微信文章表
    (
        "wechat_articles",
        "wechat_articles",
        "business",
        {
            "id": "id",
            "title": "title",
            "content": "content",
            "link": "link",
            "author": "author",
            "source": "source",
            "published": "published",
            "category": "category",
            "sentiment_score": "sentiment_score",
            "emotion_tag": "emotion_tag",
            "event_tags": "event_tags",
            "related_funds": "related_funds",
            "content_hash": "content_hash",
            "is_processed": "is_processed",
            "created_at": "created_at",
        }
    ),
]


def get_sqlite_columns(conn, table_name):
    """获取SQLite表的所有列名"""
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cursor.fetchall()}


def get_pg_columns(pg_cur, schema, table_name):
    """获取PostgreSQL表的所有列名"""
    pg_cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        """,
        (schema, table_name)
    )
    return {row[0] for row in pg_cur.fetchall()}


def convert_value(val, pg_col):
    """类型转换: SQLite值 → PostgreSQL值"""
    if val is None:
        return None

    # 处理整数类型的布尔转换
    if pg_col in ["is_read", "is_active", "is_superuser", "is_important",
                  "is_processed", "email_verified", "data_verified",
                  "compliance_defect_flag", "abnormal_volatility_flag",
                  "maintenance_cost_spike_flag", "cooperation_agreement"]:
        return bool(val)

    # JSONB 字段处理
    if pg_col in ["event_tags", "related_funds", "missing_certificates",
                  "correction_detail", "risk_flags", "comparable_cases"]:
        if isinstance(val, str):
            return val  # PostgreSQL会自动解析JSON字符串
        return None

    return val


def migrate_table(sqlite_conn, pg_cur, sqlite_table, pg_table, schema, col_map):
    """迁移单张表"""
    sqlite_cols = get_sqlite_columns(sqlite_conn, sqlite_table)
    pg_cols = get_pg_columns(pg_cur, schema, pg_table)

    # 过滤掉SQLite中不存在或PostgreSQL中不存在的列
    valid_map = {
        sk: pv for sk, pv in col_map.items()
        if sk in sqlite_cols and pv in pg_cols
    }

    if not valid_map:
        logger.warning(f"  [{sqlite_table}] → [{schema}.{pg_table}] 无有效列映射，跳过")
        return 0

    # 读取SQLite数据
    cols = ", ".join(valid_map.keys())
    rows = sqlite_conn.execute(f"SELECT {cols} FROM {sqlite_table}").fetchall()

    if not rows:
        logger.info(f"  [{sqlite_table}] → [{schema}.{pg_table}] 源表为空，跳过")
        return 0

    # 构建INSERT语句
    pg_col_list = ", ".join(valid_map.values())
    placeholders = ", ".join(["%s"] * len(valid_map))

    insert_sql = f'INSERT INTO {schema}."{pg_table}" ({pg_col_list}) VALUES ({placeholders})'

    # ON CONFLICT处理（针对有唯一约束的表）
    if pg_table in ["funds", "market_indices"]:
        pass  # 这些表有主键冲突时跳过

    count = 0
    errors = 0

    for row in rows:
        try:
            values = []
            for i, (sk, pv) in enumerate(valid_map.items()):
                val = convert_value(row[i], pv)
                values.append(val)

            if DRY_RUN:
                count += 1
                continue

            pg_cur.execute(insert_sql, values)
            count += 1

            # 每1000条提交一次
            if count % 1000 == 0:
                pg_cur.connection.commit()
                logger.info(f"  已迁移 {count} 条...")

        except Exception as e:
            errors += 1
            if errors <= 5:
                logger.warning(f"  插入失败 (pk={row[0] if row else None}): {e}")
            elif errors == 6:
                logger.warning("  后续错误将静默处理...")

    if not DRY_RUN:
        pg_cur.connection.commit()

    logger.info(f"  [{sqlite_table}] → [{schema}.{pg_table}] 迁移完成: {count} 条" + (f", 失败: {errors} 条" if errors > 0 else ""))
    return count


def main():
    logger.info("=" * 60)
    logger.info("SQLite → PostgreSQL 数据迁移")
    logger.info("=" * 60)
    logger.info(f"SQLite:  {SQLITE_PATH}")
    logger.info(f"PostgreSQL: {POSTGRES_DSN.replace(':5432/', ':***/')}")
    logger.info(f"DRY_RUN: {DRY_RUN}")

    # 检查SQLite文件
    if not os.path.exists(SQLITE_PATH):
        logger.error(f"SQLite数据库不存在: {SQLITE_PATH}")
        sys.exit(1)

    # 连接SQLite
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row

    # 获取SQLite所有表
    sqlite_tables = {
        row[0] for row in sqlite_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    logger.info(f"SQLite表: {', '.join(sorted(sqlite_tables))}")

    # 连接PostgreSQL
    try:
        import psycopg2
        pg_conn = psycopg2.connect(POSTGRES_DSN)
        pg_cur = pg_conn.cursor()
        logger.info("PostgreSQL连接成功")
    except ImportError:
        logger.error("缺少psycopg2，请安装: pip install psycopg2-binary")
        sys.exit(1)
    except Exception as e:
        logger.error(f"PostgreSQL连接失败: {e}")
        sys.exit(1)

    # 执行迁移
    total = 0
    for sqlite_table, pg_table, schema, col_map in TABLE_MAPPINGS:
        if sqlite_table not in sqlite_tables:
            logger.info(f"[{sqlite_table}] SQLite中不存在，跳过")
            continue

        count = migrate_table(sqlite_conn, pg_cur, sqlite_table, pg_table, schema, col_map)
        total += count

    # 关闭连接
    sqlite_conn.close()
    pg_cur.close()
    pg_conn.close()

    logger.info("=" * 60)
    if DRY_RUN:
        logger.info(f"[DRY RUN] 预览完成，共 {total} 条记录待迁移")
    else:
        logger.info(f"迁移完成，共 {total} 条记录")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
