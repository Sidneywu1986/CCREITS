#!/usr/bin/env python3
"""
分红日历 API 接口
提供REITs分红日历的RESTful API
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date
import os
import sys

# 添加项目根目录到路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.config import settings
from core.db import get_conn

router = APIRouter(prefix="/api/dividend-calendar", tags=["dividend-calendar"])


class DividendCalendarItem(BaseModel):
    """分红日历数据模型"""
    id: int
    fund_code: str
    fund_name: Optional[str] = None
    dividend_date: str  # 分红日期
    dividend_amount: float  # 分红金额（每份）
    record_date: Optional[str] = None  # 权益登记日
    ex_dividend_date: Optional[str] = None  # 除息日
    exchange: Optional[str] = None  # 交易所
    created_at: Optional[str] = None


class DividendCalendarResponse(BaseModel):
    """分红日历响应模型"""
    success: bool
    data: List[DividendCalendarItem]
    total: int
    message: Optional[str] = None


def get_db_connection():
    """获取数据库连接（兼容旧接口，实际走 PostgreSQL）"""
    return get_conn()


@router.get("/list", response_model=DividendCalendarResponse)
async def get_dividend_calendar(
    fund_codes: Optional[List[str]] = Query(None, description="基金代码列表"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    exchange: Optional[str] = Query(None, description="交易所 (SSE/SZSE)"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """
    获取分红日历列表

    - **fund_codes**: 基金代码列表，如 ['508001', '180101']
    - **start_date**: 开始日期，如 '2024-01-01'
    - **end_date**: 结束日期，如 '2024-12-31'
    - **exchange**: 交易所，SSE（上交所）或 SZSE（深交所）
    - **page**: 页码，从1开始
    - **page_size**: 每页数量，1-100
    """
    try:
        with get_conn() as conn:
            cursor = conn.cursor()

            # 构建查询条件
            conditions = []
            params = []

            if fund_codes:
                placeholders = ','.join(['%s' for _ in fund_codes])
                conditions.append(f"d.fund_code IN ({placeholders})")
                params.extend(fund_codes)

            if start_date:
                conditions.append("d.dividend_date >= %s")
                params.append(start_date)

            if end_date:
                conditions.append("d.dividend_date <= %s")
                params.append(end_date)

            if exchange:
                conditions.append("f.exchange = %s")
                params.append(exchange)

            # 构建WHERE子句
            where_clause = " AND ".join(conditions)
            if where_clause:
                where_clause = "WHERE " + where_clause

            # 查询总数
            count_sql = f"""
                SELECT COUNT(*) as total
                FROM business.dividends d
                LEFT JOIN business.funds f ON d.fund_code = f.fund_code
                {where_clause}
            """
            cursor.execute(count_sql, params)
            total = cursor.fetchone()['total']

            # 查询数据
            offset = (page - 1) * page_size
            data_sql = f"""
                SELECT
                    d.id,
                    d.fund_code,
                    f.fund_name,
                    d.dividend_date,
                    d.dividend_amount,
                    d.record_date,
                    d.ex_dividend_date,
                    f.exchange,
                    d.created_at
                FROM business.dividends d
                LEFT JOIN business.funds f ON d.fund_code = f.fund_code
                {where_clause}
                ORDER BY d.dividend_date DESC, d.fund_code
                LIMIT %s OFFSET %s
            """
            params.extend([page_size, offset])

            cursor.execute(data_sql, params)
            rows = cursor.fetchall()

            # 转换为响应模型
            data = []
            for row in rows:
                data.append(DividendCalendarItem(
                    id=row['id'],
                    fund_code=row['fund_code'],
                    fund_name=row['fund_name'],
                    dividend_date=str(row['dividend_date']),
                    dividend_amount=row['dividend_amount'],
                    record_date=str(row['record_date']) if row['record_date'] else None,
                    ex_dividend_date=str(row['ex_dividend_date']) if row['ex_dividend_date'] else None,
                    exchange=row['exchange'],
                    created_at=str(row['created_at']) if row['created_at'] else None
                ))

        return DividendCalendarResponse(
            success=True,
            data=data,
            total=total,
            message="获取分红日历成功"
        )

    except Exception:
        logger.exception("获取分红日历失败")
        return DividendCalendarResponse(
            success=False,
            data=[],
            total=0,
            message="获取分红日历失败，请稍后重试"
        )


@router.get("/upcoming", response_model=DividendCalendarResponse)
async def get_upcoming_dividends(
    days: int = Query(30, ge=1, le=365, description="未来天数"),
    fund_codes: Optional[List[str]] = Query(None, description="基金代码列表")
):
    """
    获取未来N天内的分红信息

    - **days**: 未来天数，1-365
    - **fund_codes**: 基金代码列表，如 ['508001', '180101']
    """
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        end_date = (datetime.now() + datetime.timedelta(days=days)).strftime('%Y-%m-%d')

        return await get_dividend_calendar(
            fund_codes=fund_codes,
            start_date=today,
            end_date=end_date
        )

    except Exception:
        logger.exception("获取近期分红失败")
        return DividendCalendarResponse(
            success=False,
            data=[],
            total=0,
            message="获取近期分红失败，请稍后重试"
        )


@router.get("/{fund_code}", response_model=DividendCalendarResponse)
async def get_fund_dividends(
    fund_code: str,
    limit: int = Query(20, ge=1, le=100, description="返回数量")
):
    """
    获取指定基金的分红历史

    - **fund_code**: 基金代码
    - **limit**: 返回数量，1-100
    """
    try:
        with get_conn() as conn:
            cursor = conn.cursor()

            sql = """
                SELECT
                    d.id,
                    d.fund_code,
                    f.fund_name,
                    d.dividend_date,
                    d.dividend_amount,
                    d.record_date,
                    d.ex_dividend_date,
                    f.exchange,
                    d.created_at
                FROM business.dividends d
                LEFT JOIN business.funds f ON d.fund_code = f.fund_code
                WHERE d.fund_code = %s
                ORDER BY d.dividend_date DESC
                LIMIT %s
            """

            cursor.execute(sql, [fund_code, limit])
            rows = cursor.fetchall()

            data = []
            for row in rows:
                data.append(DividendCalendarItem(
                    id=row['id'],
                    fund_code=row['fund_code'],
                    fund_name=row['fund_name'],
                    dividend_date=str(row['dividend_date']),
                    dividend_amount=row['dividend_amount'],
                    record_date=str(row['record_date']) if row['record_date'] else None,
                    ex_dividend_date=str(row['ex_dividend_date']) if row['ex_dividend_date'] else None,
                    exchange=row['exchange'],
                    created_at=str(row['created_at']) if row['created_at'] else None
                ))

        return DividendCalendarResponse(
            success=True,
            data=data,
            total=len(data),
            message=f"获取基金{fund_code}分红历史成功"
        )

    except Exception:
        logger.exception(f"获取基金{fund_code}分红历史失败")
        return DividendCalendarResponse(
            success=False,
            data=[],
            total=0,
            message="获取基金分红历史失败，请稍后重试"
        )


@router.get("/stats/summary")
async def get_dividend_stats(
    year: Optional[int] = Query(None, description="年份，如2024")
):
    """
    获取分红统计信息

    - **year**: 年份，如2024。不指定则返回全部年份统计
    """
    try:
        with get_conn() as conn:
            cursor = conn.cursor()

            if year:
                # 按基金统计指定年份的分红
                sql = """
                    SELECT
                        d.fund_code,
                        f.fund_name,
                        f.exchange,
                        COUNT(*) as dividend_count,
                        SUM(d.dividend_amount) as total_dividend,
                        AVG(d.dividend_amount) as avg_dividend,
                        MAX(d.dividend_amount) as max_dividend,
                        MIN(d.dividend_amount) as min_dividend
                    FROM business.dividends d
                    LEFT JOIN business.funds f ON d.fund_code = f.fund_code
                    WHERE EXTRACT(YEAR FROM d.dividend_date) = %s
                    GROUP BY d.fund_code, f.fund_name, f.exchange
                    ORDER BY total_dividend DESC
                """
                cursor.execute(sql, [str(year)])
            else:
                # 按年份统计
                sql = """
                    SELECT
                        EXTRACT(YEAR FROM d.dividend_date)::text as year,
                        COUNT(*) as dividend_count,
                        SUM(d.dividend_amount) as total_dividend,
                        AVG(d.dividend_amount) as avg_dividend,
                        COUNT(DISTINCT d.fund_code) as fund_count
                    FROM business.dividends d
                    GROUP BY year
                    ORDER BY year DESC
                """
                cursor.execute(sql)

            rows = cursor.fetchall()

        return {
            "success": True,
            "data": [dict(row) for row in rows],
            "message": "获取分红统计成功"
        }

    except Exception:
        logger.exception("获取分红统计失败")
        return {
            "success": False,
            "data": [],
            "message": "获取分红统计失败，请稍后重试"
        }