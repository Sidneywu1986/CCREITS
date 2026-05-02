#!/usr/bin/env python3
"""
API适配层 - 统一前后端路径格式
使用PostgreSQL数据库作为数据源
"""

import os
import sys
import re
from typing import Optional
from pathlib import Path
from fastapi import FastAPI, Query, Body, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import datetime
import logging

logger = logging.getLogger(__name__)

# Tortoise ORM for PostgreSQL (ai_db)
try:
    from tortoise.contrib.fastapi import register_tortoise
    TORTOISE_AVAILABLE = True
except ImportError:
    TORTOISE_AVAILABLE = False

# 添加项目根目录到路径
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / 'services'))

from core.config import settings
from core.db import get_conn
from services import realtime_quotes, announcements

# 覆盖 core.db.get_conn: api_adapter 使用普通 cursor（兼容 row[0] 索引访问）
import contextlib
import logging
import psycopg2
import requests
from core.db import _get_pg_dsn

@contextlib.contextmanager
def get_conn():
    """API adapter 专用数据库连接（使用默认 cursor，返回元组）"""
    conn = psycopg2.connect(_get_pg_dsn())
    try:
        yield conn
    finally:
        conn.close()

# 十年期国债收益率缓存
_BOND_CACHE = None
_BOND_CACHE_TIME = 0
_BOND_CACHE_TTL = 300  # 5分钟缓存

# 市场指数缓存
_INDICES_CACHE = None
_INDICES_CACHE_TIME = 0
_INDICES_CACHE_TTL = 60  # 1分钟缓存

def get_bond_yield():
    """从AKShare获取十年期国债收益率（带缓存），带5秒超时防卡死"""
    global _BOND_CACHE, _BOND_CACHE_TIME
    import time
    now = time.time()
    if _BOND_CACHE is not None and (now - _BOND_CACHE_TIME) < _BOND_CACHE_TTL:
        return _BOND_CACHE
    try:
        import concurrent.futures
        import akshare as ak
        
        def _fetch():
            df = ak.bond_zh_us_rate()
            latest = df.iloc[-1]
            date_str = str(latest.iloc[0])
            col = [c for c in df.columns if '10' in str(c) and '中国' in str(c) and '-' not in str(c)][0]
            value = float(latest[col])
            prev = df.iloc[-2]
            prev_value = float(prev[col])
            change = round(value - prev_value, 4)
            change_pct = round((change / prev_value) * 100, 2) if prev_value else 0
            return {
                'date': date_str,
                'value': value,
                'change': change,
                'changePercent': change_pct
            }
        
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(_fetch)
        try:
            result = future.result(timeout=5)
            _BOND_CACHE = result
            _BOND_CACHE_TIME = now
            return result
        except concurrent.futures.TimeoutError:
            pass
        finally:
            executor.shutdown(wait=False)
    except (RuntimeError, OSError):
        pass
    # 超时或异常时返回旧缓存（如果有）
    if _BOND_CACHE is not None:
        return _BOND_CACHE
    return None

# 创建API适配层应用
adapter_app = FastAPI(
    title="REITs API Adapter",
    description="统一前端API路径到后端服务的适配层",
    version="1.0.0"
)

# CORS配置
adapter_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== 速率限制中间件 ==========
import time
from collections import defaultdict

class RateLimiter:
    """基于内存的滑动窗口速率限制器（单实例有效；多实例部署需配合 Redis）"""
    def __init__(self):
        self._store = defaultdict(list)

    def is_allowed(self, key: str, max_requests: int, window: int = 60) -> bool:
        now = time.time()
        self._store[key] = [t for t in self._store[key] if now - t < window]
        if len(self._store[key]) >= max_requests:
            return False
        self._store[key].append(now)
        return True

_rate_limiter = RateLimiter()

@adapter_app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    client_ip = request.client.host if request.client else "unknown"
    if path.startswith("/api/ai/"):
        if not _rate_limiter.is_allowed(f"ai:{client_ip}", max_requests=30):
            raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")
    elif path.startswith("/api/"):
        if not _rate_limiter.is_allowed(f"api:{client_ip}", max_requests=120):
            raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")
    return await call_next(request)

# AI API 路由注册
from api import chat_reits_router, chat_announcement_router, research_router, search_router, fund_analysis_router
from api.agents_show import router as agents_show_router
from api.ws_chat import router as ws_chat_router
from api.schedule import router as schedule_router

adapter_app.include_router(chat_reits_router)
adapter_app.include_router(chat_announcement_router)
adapter_app.include_router(research_router)
adapter_app.include_router(search_router)
adapter_app.include_router(ws_chat_router)
adapter_app.include_router(fund_analysis_router)
adapter_app.include_router(schedule_router)
adapter_app.include_router(agents_show_router)

# Register Tortoise ORM for PostgreSQL (ai_db)
if TORTOISE_AVAILABLE:
    try:
        register_tortoise(
            adapter_app,
            config=settings.AI_DB_CONFIG,
            generate_schemas=False,  # Tables already exist
            add_exception_handlers=True,
        )
        logger.info("[Tortoise] Registered ai_db (PostgreSQL)")
    except (ImportError, RuntimeError, ConnectionError) as e:
        logger.exception("Tortoise registration failed")
        logger.error("[Tortoise] Registration failed")

# 启动后台定时任务（每30分钟同步一次）
try:
    from scheduler.tasks import start_scheduler
    start_scheduler(interval_minutes=30)
    logger.info("[Scheduler] Auto-sync every 30 minutes enabled")
except (ImportError, RuntimeError) as e:
    logger.exception("Scheduler start failed")
    logger.error("[Scheduler] Failed to start")

# 数据库路径 - 基于项目根目录的动态路径


# ==================== 缓存系统 ====================
import time
from functools import wraps

# 内存缓存: {key: (value, expire_at)}
_memory_cache: dict = {}

def cache_get(key: str):
    """获取缓存值，过期返回None"""
    if key in _memory_cache:
        value, expire_at = _memory_cache[key]
        if time.time() < expire_at:
            return value
        del _memory_cache[key]
    return None

def cache_set(key: str, value, ttl: int = 60):
    """设置缓存，ttl单位秒"""
    _memory_cache[key] = (value, time.time() + ttl)

def cache_clear(pattern: str = ""):
    """清除缓存，空字符串清除全部"""
    global _memory_cache
    if not pattern:
        _memory_cache.clear()
    else:
        _memory_cache = {k: v for k, v in _memory_cache.items() if pattern not in k}


def convert_code_to_org_id(code: str) -> str:
    """转换基金代码到CNInfo orgId格式"""
    if code.startswith('5'):
        # 上交所: gssz05XXXXX
        return f"gssz05{code}"
    else:
        # 深交所: gszsXXXXXX
        return f"gszs{code}"


# ==================== API端点实现 ====================

@adapter_app.get("/api/funds/list")
async def get_funds_list():
    """获取基金列表（带缓存，TTL=60秒）"""
    cache_key = "funds:list"
    cached = cache_get(cache_key)
    if cached is not None:
        return {
            "success": True,
            "data": cached["data"],
            "total": cached["total"],
            "message": "获取基金列表成功（缓存）",
            "cached": True
        }

    try:
        with get_conn() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT fund_code, fund_name, exchange, ipo_date, nav, dividend_yield, status,
                               sector, sector_name, scale, market_cap, property_type, remaining_years,
                               debt_ratio, premium_rate, listing_date
                        FROM business.funds
                        ORDER BY exchange, fund_code
                    """)
                    rows = cursor.fetchall()

        funds = []
        for row in rows:
            funds.append({
                "code": row[0],
                "name": row[1],
                "exchange": row[2],
                "listing_date": row[3],
                "nav": row[4] or 0,
                "yield": row[5] or 0,
                "dividend_yield": row[5] or 0,
                "status": row[6] or "listed",
                "sector": row[7] or "",
                "sectorName": row[8] or "",
                "scale": row[9] or 0,
                "marketCap": row[10] or 0,
                "propertyType": row[11] or "",
                "remainingYears": row[12] or "",
                "debt": row[13] or 0,
                "premium": row[14] or 0,
                "listing_date": row[15] or row[3] or ""
            })

        result = {
            "success": True,
            "data": funds,
            "total": len(funds),
            "message": "获取基金列表成功",
            "cached": False
        }
        cache_set(cache_key, {"data": funds, "total": len(funds)}, ttl=60)
        return result
    except Exception:
        logger.exception("获取基金列表失败，请稍后重试")
        return {
            "success": False,
            "data": [],
            "message": "获取基金列表失败，请稍后重试"
        }


@adapter_app.get("/api/funds/detail")
async def funds_detail_adapter(code: str = Query(..., description="基金代码")):
    """基金详情"""
    try:
        with get_conn() as conn:
                    cursor = conn.cursor()
            
                    # 获取基金基本信息
                    cursor.execute("""
                        SELECT fund_code, fund_name, full_name, exchange, ipo_date,
                               ipo_price, total_shares, nav, dividend_yield, manager, asset_type
                        FROM business.funds WHERE fund_code = %s
                    """, (code,))
                    row = cursor.fetchone()

        if not row:
            return {
                "success": False,
                "data": None,
                "message": "基金不存在"
            }

        # 获取最新价格
        with get_conn() as conn2:
                    cursor2 = conn2.cursor()
                    cursor2.execute("""
                        SELECT trade_date, close_price, change_pct, volume, premium_rate
                        FROM business.fund_prices
                        WHERE fund_code = %s
                        ORDER BY trade_date DESC LIMIT 1
                    """, (code,))
                    price_row = cursor2.fetchone()

        return {
            "success": True,
            "data": {
                "code": row[0],
                "name": row[1],
                "full_name": row[2],
                "exchange": row[3],
                "listing_date": row[4],
                "price": price_row[1] if price_row else row[6],
                "change_percent": price_row[2] if price_row else 0,
                "volume": price_row[3] if price_row else 0,
                "premium_rate": price_row[4] if price_row else 0,
                "nav": row[7],
                "yield": row[8] or 0,
                "dividend_yield": row[8] or 0,
                "scale": (row[5] * row[6] / 100000000) if row[5] and row[6] else 0,
                "manager": row[9],
                "asset_type": row[10],
            },
            "message": "获取基金详情成功"
        }
    except Exception:
        logger.exception("获取基金详情失败，请稍后重试")
        return {
            "success": False,
            "data": None,
            "message": "获取基金详情失败，请稍后重试"
        }


@adapter_app.get("/api/funds/sectors")
async def get_sectors_list():
    """获取板块分类列表（带缓存，TTL=300秒）"""
    cache_key = "funds:sectors"
    cached = cache_get(cache_key)
    if cached is not None:
        return {
            "success": True,
            "data": cached,
            "message": "获取板块列表成功（缓存）",
            "cached": True
        }

    try:
        with get_conn() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT DISTINCT sector_name FROM business.funds
                        WHERE sector_name IS NOT NULL AND sector_name != ''
                        ORDER BY sector_name
                    """)
                    rows = cursor.fetchall()

        sectors = [row[0] for row in rows]
        cache_set(cache_key, sectors, ttl=300)
        return {
            "success": True,
            "data": sectors,
            "message": f"获取板块列表成功（{len(sectors)}个板块）",
            "cached": False
        }
    except Exception:
        logger.exception("获取板块列表失败，请稍后重试")
        return {
            "success": False,
            "data": [],
            "message": "获取板块列表失败，请稍后重试"
        }


@adapter_app.get("/api/funds/price-history")
async def price_history_adapter(
    code: str = Query(..., description="基金代码"),
    time_range: str = Query("daily", description="时间范围: minute/daily/weekly")
):
    """价格历史"""
    try:
        with get_conn() as conn:
                    cursor = conn.cursor()
            
                    # daily 返回全部历史记录；weekly 也查询全部，然后在 Python 中做周K聚合
                    if time_range == "minute":
                        start_date = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
                        cursor.execute("""
                            SELECT trade_date, open_price, high_price, low_price,
                                   close_price, volume, amount, daily_return
                            FROM business.price_history
                            WHERE fund_code = %s AND trade_date >= %s
                            ORDER BY trade_date ASC
                        """, (code, start_date))
                    else:
                        # daily/weekly 均查询全部历史，由前端或下方聚合逻辑处理
                        cursor.execute("""
                            SELECT trade_date, open_price, high_price, low_price,
                                   close_price, volume, amount, daily_return
                            FROM business.price_history
                            WHERE fund_code = %s
                            ORDER BY trade_date ASC
                        """, (code,))
            
                    rows = cursor.fetchall()

        # 构建日K原始数据
        daily = []
        for row in rows:
            daily.append({
                "date": row[0],
                "open": row[1] or 0,
                "high": row[2] or 0,
                "low": row[3] or 0,
                "price": row[4] or 0,
                "volume": row[5] or 0,
                "amount": row[6] or 0,
                "change": row[7] or 0
            })

        # weekly：对日K做周K聚合
        if time_range == "weekly" and daily:
            from collections import OrderedDict
            weeks = OrderedDict()
            for item in daily:
                dt = item["date"]
                if not isinstance(dt, datetime.date):
                    dt = datetime.datetime.strptime(str(dt), "%Y-%m-%d").date()
                iso_year, iso_week, _ = dt.isocalendar()
                key = f"{iso_year}-W{iso_week:02d}"
                if key not in weeks:
                    weeks[key] = {
                        "dates": [],
                        "open": item["open"],
                        "high": item["high"],
                        "low": item["low"],
                        "close": item["price"],
                        "volume": 0,
                        "amount": 0,
                    }
                w = weeks[key]
                w["dates"].append(item["date"])
                w["high"] = max(w["high"], item["high"])
                w["low"] = min(w["low"], item["low"])
                w["close"] = item["price"]  # 最后一天的收盘价
                w["volume"] += item["volume"] or 0
                w["amount"] += item["amount"] or 0

            history = []
            prev_close = None
            for key, w in weeks.items():
                week_end = max(w["dates"])
                if prev_close is not None and prev_close > 0:
                    change = round((w["close"] - prev_close) / prev_close * 100, 2)
                else:
                    change = 0
                history.append({
                    "date": week_end,
                    "open": w["open"],
                    "high": w["high"],
                    "low": w["low"],
                    "price": w["close"],
                    "volume": w["volume"],
                    "amount": w["amount"],
                    "change": change,
                })
                prev_close = w["close"]
        else:
            history = daily

        return {
            "success": True,
            "data": history,
            "message": f"获取价格历史成功 ({len(history)}条)"
        }
    except Exception:
        logger.exception("获取价格历史失败，请稍后重试")
        return {
            "success": False,
            "data": [],
            "message": "获取价格历史失败，请稍后重试"
        }


@adapter_app.get("/api/funds/related")
async def related_funds_adapter(
    sector: str = Query(None, description="板块名称"),
    excludeCode: str = Query(None, description="排除的基金代码")
):
    """相关基金（同板块）"""
    try:
        with get_conn() as conn:
                    cursor = conn.cursor()
            
                    # 获取所有基金
                    cursor.execute("""
                        SELECT fund_code, fund_name, exchange, asset_type
                        FROM business.funds
                        WHERE fund_code != %s OR %s IS NULL
                        ORDER BY fund_code
                        LIMIT 20
                    """, (excludeCode or "", excludeCode))
            
                    rows = cursor.fetchall()

        related = []
        for row in rows:
            related.append({
                "code": row[0],
                "name": row[1],
                "exchange": row[2],
                "sector": row[3] or "other"
            })

        return {
            "success": True,
            "data": related,
            "message": f"获取相关基金成功 ({len(related)}只)"
        }
    except Exception:
        logger.exception("获取相关基金失败，请稍后重试")
        return {
            "success": False,
            "data": [],
            "message": "获取相关基金失败，请稍后重试"
        }


@adapter_app.get("/api/funds/financial")
async def financial_data_adapter(code: str = Query(..., description="基金代码")):
    """财务数据"""
    try:
        with get_conn() as conn:
                    cursor = conn.cursor()
            
                    # 获取基金信息作为财务数据
                    cursor.execute("""
                        SELECT fund_code, fund_name, nav, total_shares, ipo_price
                        FROM business.funds WHERE fund_code = %s
                    """, (code,))
                    row = cursor.fetchone()

        if not row:
            return {
                "success": False,
                "data": None,
                "message": "基金不存在"
            }

        return {
            "success": True,
            "data": {
                "fund_code": row[0],
                "fund_name": row[1],
                "nav": row[2] or 0,
                "total_shares": row[3] or 0,
                "ipo_price": row[4] or 0,
                "report_date": datetime.date.today().strftime('%Y-%m-%d')
            },
            "message": "获取财务数据成功"
        }
    except Exception:
        logger.exception("获取财务数据失败，请稍后重试")
        return {
            "success": False,
            "data": None,
            "message": "获取财务数据失败，请稍后重试"
        }


@adapter_app.get("/api/funds/operation")
async def operation_data_adapter(code: str = Query(..., description="基金代码")):
    """运营数据"""
    try:
        with get_conn() as conn:
                    cursor = conn.cursor()
            
                    cursor.execute("""
                        SELECT fund_code, fund_name, asset_type, underlying_assets
                        FROM business.funds WHERE fund_code = %s
                    """, (code,))
                    row = cursor.fetchone()

        if not row:
            return {
                "success": False,
                "data": None,
                "message": "基金不存在"
            }

        return {
            "success": True,
            "data": {
                "fund_code": row[0],
                "fund_name": row[1],
                "asset_type": row[2] or "未知",
                "underlying_assets": row[3] or "未知",
                "report_date": datetime.date.today().strftime('%Y-%m-%d')
            },
            "message": "获取运营数据成功"
        }
    except Exception:
        logger.exception("获取运营数据失败，请稍后重试")
        return {
            "success": False,
            "data": None,
            "message": "获取运营数据失败，请稍后重试"
        }


@adapter_app.get("/api/funds/dividends")
async def dividends_adapter(code: str = Query(..., description="基金代码")):
    """分红数据"""
    try:
        with get_conn() as conn:
                    cursor = conn.cursor()
            
                    cursor.execute("""
                        SELECT dividend_date, dividend_amount, record_date, ex_dividend_date
                        FROM business.dividends
                        WHERE fund_code = %s
                        ORDER BY dividend_date DESC
                        LIMIT 10
                    """, (code,))
            
                    rows = cursor.fetchall()

        dividends = []
        for row in rows:
            dividends.append({
                "dividend_date": row[0],
                "amount": row[1] or 0,
                "record_date": row[2],
                "ex_date": row[3]
            })

        return {
            "success": True,
            "data": dividends,
            "message": f"获取分红数据成功 ({len(dividends)}条)"
        }
    except Exception:
        logger.exception("获取分红数据失败，请稍后重试")
        return {
            "success": False,
            "data": [],
            "message": "获取分红数据失败，请稍后重试"
        }


# ==================== 分红日历端点 ====================

@adapter_app.get("/api/dividend-calendar/list")
async def dividend_calendar_list(
    start_date: str = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(None, description="结束日期 YYYY-MM-DD"),
    page_size: int = Query(500, description="返回条数", ge=1, le=2000),
):
    """获取所有分红记录（支持日期范围和条数限制）"""
    try:
        with get_conn() as conn:
                    cursor = conn.cursor()

                    conditions = []
                    params = []
                    if start_date:
                        conditions.append("d.dividend_date >= %s")
                        params.append(start_date)
                    if end_date:
                        conditions.append("d.dividend_date <= %s")
                        params.append(end_date)

                    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            
                    cursor.execute(f"""
                        SELECT d.id, d.fund_code, f.fund_name, d.dividend_date,
                               d.dividend_amount, d.record_date, d.ex_dividend_date
                        FROM business.dividends d
                        LEFT JOIN business.funds f ON d.fund_code = f.fund_code
                        {where_clause}
                        ORDER BY d.dividend_date DESC
                        LIMIT %s
                    """, (*params, page_size))
            
                    rows = cursor.fetchall()

        dividends = []
        for row in rows:
            dividends.append({
                "id": row[0],
                "fund_code": row[1],
                "fund_name": row[2] or row[1],
                "dividend_date": str(row[3]) if row[3] else None,
                "dividend_amount": float(row[4]) if row[4] else 0,
                "record_date": str(row[5]) if row[5] else None,
                "ex_dividend_date": str(row[6]) if row[6] else None,
            })

        return {
            "success": True,
            "data": dividends,
            "total": len(dividends),
            "message": f"获取分红日历成功 ({len(dividends)}条)"
        }
    except Exception:
        logger.exception("获取分红日历失败，请稍后重试")
        return {
            "success": False,
            "data": [],
            "total": 0,
            "message": "获取分红日历失败，请稍后重试"
        }


@adapter_app.get("/api/dividends")
async def dividends_list(
    fund_code: str = Query(None, description="基金代码筛选"),
    page: int = Query(1, description="页码", ge=1),
    page_size: int = Query(50, description="每页条数", ge=1, le=500),
):
    """获取分红记录列表（支持分页和基金筛选）"""
    try:
        with get_conn() as conn:
            cursor = conn.cursor()

            conditions = []
            params = []
            if fund_code:
                conditions.append("d.fund_code = %s")
                params.append(fund_code)

            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

            # 查询数据
            cursor.execute(f"""
                SELECT d.id, d.fund_code, f.fund_name, d.dividend_date,
                       d.dividend_amount, d.dividend_per_share, d.record_date,
                       d.ex_dividend_date, d.dividend_payment_date
                FROM business.dividends d
                LEFT JOIN business.funds f ON d.fund_code = f.fund_code
                {where_clause}
                ORDER BY d.dividend_date DESC
                LIMIT %s OFFSET %s
            """, (*params, page_size, (page - 1) * page_size))

            rows = cursor.fetchall()

            dividends = []
            for row in rows:
                dividends.append({
                    "id": row[0],
                    "fund_code": row[1],
                    "fund_name": row[2] or row[1],
                    "dividend_date": row[3],
                    "dividend_amount": float(row[4]) if row[4] else 0,
                    "dividend_per_share": float(row[5]) if row[5] else 0,
                    "record_date": row[6],
                    "ex_dividend_date": row[7],
                    "dividend_payment_date": row[8],
                })

            # 查询总数
            cursor.execute(f"""
                SELECT COUNT(*) FROM business.dividends d {where_clause}
            """, params)
            total = cursor.fetchone()[0]

        return {
            "success": True,
            "data": dividends,
            "total": total,
            "page": page,
            "page_size": page_size,
            "message": f"获取分红记录成功 ({len(dividends)}条)"
        }
    except Exception:
        logger.exception("获取分红记录失败")
        return {
            "success": False,
            "data": [],
            "total": 0,
            "message": "获取分红记录失败"
        }


@adapter_app.get("/api/dividends/stats")
async def dividends_stats():
    """获取分红统计信息"""
    try:
        with get_conn() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM business.dividends")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT COALESCE(SUM(dividend_amount), 0) FROM business.dividends")
            total_amount = float(cursor.fetchone()[0])

            cursor.execute("""
                SELECT COUNT(DISTINCT fund_code) FROM business.dividends
            """)
            funds_with_dividends = cursor.fetchone()[0]

            cursor.execute("""
                SELECT EXTRACT(YEAR FROM dividend_date)::int as year,
                       COUNT(*), COALESCE(SUM(dividend_amount), 0)
                FROM business.dividends
                GROUP BY year ORDER BY year DESC
            """)
            by_year = {}
            for row in cursor.fetchall():
                by_year[row[0]] = {"count": row[1], "amount": float(row[2])}

        return {
            "success": True,
            "data": {
                "total": total,
                "total_amount": round(total_amount, 4),
                "funds_with_dividends": funds_with_dividends,
                "by_year": by_year,
            },
            "message": "获取分红统计成功"
        }
    except Exception:
        logger.exception("获取分红统计失败")
        return {
            "success": False,
            "data": None,
            "message": "获取分红统计失败"
        }


@adapter_app.get("/api/dividend-calendar/stats/summary")
async def dividend_stats_summary():
    """获取分红统计摘要"""
    try:
        with get_conn() as conn:
                    cursor = conn.cursor()
            
                    # 总分红次数
                    cursor.execute("SELECT COUNT(*) FROM business.dividends")
                    total_count = cursor.fetchone()[0]
            
                    # 总分红金额
                    cursor.execute("SELECT COALESCE(SUM(dividend_amount), 0) FROM business.dividends")
                    total_amount = cursor.fetchone()[0]
            
                    # 今年分红次数
                    cursor.execute("""
                        SELECT COUNT(*) FROM business.dividends
                        WHERE EXTRACT(YEAR FROM dividend_date) = EXTRACT(YEAR FROM CURRENT_DATE)
                    """)
                    year_count = cursor.fetchone()[0]
            
                    # 今年分红金额
                    cursor.execute("""
                        SELECT COALESCE(SUM(dividend_amount), 0) FROM business.dividends
                        WHERE EXTRACT(YEAR FROM dividend_date) = EXTRACT(YEAR FROM CURRENT_DATE)
                    """)
                    year_amount = cursor.fetchone()[0]
            
                    # 待实施分红（ex_dividend_date > today）
                    cursor.execute("""
                        SELECT COUNT(*) FROM business.dividends
                        WHERE ex_dividend_date > CURRENT_DATE
                    """)
                    pending_count = cursor.fetchone()[0]
            

        return {
            "success": True,
            "data": {
                "total_count": total_count,
                "total_amount": round(total_amount, 2),
                "year_count": year_count,
                "year_amount": round(year_amount, 2),
                "pending_count": pending_count
            },
            "message": "获取分红统计成功"
        }
    except Exception:
        logger.exception("获取分红统计失败，请稍后重试")
        return {
            "success": False,
            "data": None,
            "message": "获取分红统计失败，请稍后重试"
        }


@adapter_app.get("/api/dividend-calendar/upcoming")
async def dividend_upcoming(days: int = Query(30, description="未来天数")):
    """获取即将分红的基金"""
    try:
        with get_conn() as conn:
                    cursor = conn.cursor()
            
                    future_date = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime('%Y-%m-%d')
            
                    cursor.execute("""
                        SELECT d.id, d.fund_code, f.fund_name, d.dividend_date,
                               d.dividend_amount, d.record_date, d.ex_dividend_date
                        FROM business.dividends d
                        LEFT JOIN business.funds f ON d.fund_code = f.fund_code
                        WHERE d.ex_dividend_date >= CURRENT_DATE
                          AND d.ex_dividend_date <= %s
                        ORDER BY d.ex_dividend_date ASC
                        LIMIT 20
                    """, (future_date,))
            
                    rows = cursor.fetchall()

        dividends = []
        for row in rows:
            dividends.append({
                "id": row[0],
                "fund_code": row[1],
                "fund_name": row[2] or row[1],
                "dividend_date": row[3],
                "dividend_amount": row[4] or 0,
                "record_date": row[5],
                "ex_dividend_date": row[6]
            })

        return {
            "success": True,
            "data": dividends,
            "total": len(dividends),
            "message": f"获取即将分红成功 ({len(dividends)}条)"
        }
    except Exception:
        logger.exception("获取即将分红失败，请稍后重试")
        return {
            "success": False,
            "data": [],
            "total": 0,
            "message": "获取即将分红失败，请稍后重试"
        }


# ==================== 市场指数端点 ====================

def parse_sina_index(data: str) -> Optional[dict]:
    """解析新浪指数数据"""
    try:
        match = re.search(r'"([^"]+)"', data)
        if not match:
            return None
        parts = match.group(1).split(',')
        if len(parts) < 4:
            return None
        price = float(parts[3]) if parts[3] else 0
        prev = float(parts[2]) if parts[2] else 0
        # 盘前/盘后 price 为 0 时回退使用 prev
        is_pre = (price == 0 and prev > 0)
        display_price = prev if is_pre else price
        change = 0.0 if is_pre else (price - prev)
        change_pct = 0.0 if is_pre else ((change / prev * 100) if prev > 0 else 0)
        return {
            "value": round(display_price, 2),
            "change": round(change, 3),
            "changePercent": round(change_pct, 2)
        }
    except:
        return None


def get_all_indices_from_sina() -> dict:
    """从新浪获取市场指数实时数据（不含中证REITs和中证红利，需从其他源获取）"""
    try:
        import requests
        headers = {'Referer': 'https://finance.sina.com.cn', 'User-Agent': 'Mozilla/5.0'}
        # 新浪指数代码:
        # sh000001=上证指数, sz399001=深证指数
        # 注: sz399639不是中证REITs，sz399638是中证小盘不是中证红利
        # 中证红利(000922)新浪不支持，需从东方财富获取
        codes = 'sh000001,sz399001'
        r = requests.get(f'https://hq.sinajs.cn/list={codes}', headers=headers, timeout=5)
        r.encoding = 'gbk'

        indices = {}
        for line in r.text.split('\n'):
            if '=' in line:
                code_match = re.search(r'hq_str_(\w+)="', line)
                if code_match:
                    code = code_match.group(1)
                    data = parse_sina_index(line)
                    if data:
                        indices[code] = data
        return indices
    except (requests.RequestException, ValueError, KeyError):
        logger.exception("获取新浪指数失败")
        return {}


def get_dividend_index_from_eastmoney() -> dict:
    """从东方财富获取中证红利指数实时数据"""
    try:
        import requests
        url = 'https://push2.eastmoney.com/api/qt/stock/get'
        params = {
            'secid': '1.000922',
            'fields': 'f43,f44,f45,f57,f58,f60,f170'
        }
        r = requests.get(url, params=params, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        data = r.json()
        if data.get('data'):
            d = data['data']
            price = (d.get('f43') or 0) / 100
            prev = (d.get('f60') or 0) / 100
            change_pct = (d.get('f170') or 0) / 100
            # 盘前/盘后 price 为 0 时回退使用 prev
            is_pre = (price == 0 and prev > 0)
            display_price = prev if is_pre else price
            change = 0.0 if is_pre else (display_price - prev)
            change_pct = 0.0 if is_pre else change_pct
            if display_price > 0:
                return {
                    "value": round(display_price, 2),
                    "change": round(change, 3),
                    "changePercent": round(change_pct, 2)
                }
        return None
    except (requests.RequestException, json.JSONDecodeError, KeyError, ValueError, TypeError):
        logger.exception("获取东方财富中证红利失败")
        return None


def calculate_reits_index() -> dict:
    """基于成分股实时行情计算中证REITs模拟指数"""
    try:
        with get_conn() as conn:
                    cursor = conn.cursor()
                    # 获取所有REITs最新行情（fund_prices表中最新记录）
                    cursor.execute("""
                        SELECT fp.fund_code, fp.close_price, fp.change_pct
                        FROM business.fund_prices fp
                        INNER JOIN (
                            SELECT fund_code, MAX(update_time) as max_time
                            FROM business.fund_prices
                            GROUP BY fund_code
                        ) latest ON fp.fund_code = latest.fund_code AND fp.update_time = latest.max_time
                    """)
                    quotes = cursor.fetchall()

        if not quotes:
            return None

        # 简单平均涨跌幅作为指数涨跌幅
        valid_changes = [q[2] for q in quotes if q[2] is not None]
        if not valid_changes:
            return None

        avg_change = sum(valid_changes) / len(valid_changes)
        base_value = 1028.21  # 中证REITs全收益指数最新收盘基准值
        current_value = base_value * (1 + avg_change / 100)
        change = current_value - base_value
        change_pct = avg_change

        return {
            "value": round(current_value, 2),
            "change": round(change, 3),
            "changePercent": round(change_pct, 2)
        }
    except psycopg2.Error:
        logger.exception("计算REITs指数失败")
        return None


@adapter_app.get("/api/market-indices/list")
async def market_indices_list():
    """获取市场指数列表（带1分钟缓存）"""
    global _INDICES_CACHE, _INDICES_CACHE_TIME
    import time
    now_ts = time.time()
    if _INDICES_CACHE is not None and (now_ts - _INDICES_CACHE_TIME) < _INDICES_CACHE_TTL:
        return _INDICES_CACHE
    
    try:
        # 从新浪获取实时数据
        sina_indices = get_all_indices_from_sina()
        now = datetime.datetime.now().isoformat()

        # 定义指数映射: code -> (sina_code, name)
        INDEX_MAPPING = {
            'sh_index': ('sh000001', '上证指数'),
            'sz_index': ('sz399001', '深证指数'),
        }

        # 构建返回数据
        indices = []
        for code, (sina_code, name) in INDEX_MAPPING.items():
            if sina_code in sina_indices:
                data = sina_indices[sina_code]
                indices.append({
                    "code": code,
                    "name": name,
                    "value": data["value"],
                    "change": data["change"],
                    "changePercent": data["changePercent"],
                    "source": "sina",
                    "updateTime": now
                })
            else:
                # 新浪获取失败时返回默认值
                indices.append({
                    "code": code,
                    "name": name,
                    "value": None,
                    "change": 0,
                    "changePercent": 0,
                    "source": "sina",
                    "updateTime": now
                })

        # 中证红利指数（从东方财富获取）
        dividend_data = get_dividend_index_from_eastmoney()
        if dividend_data:
            indices.append({
                "code": "dividend",
                "name": "中证红利",
                "value": dividend_data["value"],
                "change": dividend_data["change"],
                "changePercent": dividend_data["changePercent"],
                "source": "eastmoney",
                "updateTime": now
            })
        else:
            indices.append({
                "code": "dividend",
                "name": "中证红利",
                "value": None,
                "change": 0,
                "changePercent": 0,
                "source": "获取失败",
                "updateTime": now
            })

        # 中证REITs全收益指数（基于成分股计算）
        reits_data = calculate_reits_index()
        if reits_data:
            indices.append({
                "code": "reits_total",
                "name": "中证REITs全收益",
                "value": reits_data["value"],
                "change": reits_data["change"],
                "changePercent": reits_data["changePercent"],
                "source": "成分股计算",
                "updateTime": now
            })
        else:
            indices.append({
                "code": "reits_total",
                "name": "中证REITs全收益",
                "value": 1028.21,
                "change": 0,
                "changePercent": 0,
                "source": "基准值",
                "updateTime": now
            })

        # 十年期国债收益率
        bond = get_bond_yield()
        if bond:
            indices.append({
                "code": "bond_yield",
                "name": "10年期国债收益率",
                "value": bond['value'],
                "change": bond['change'],
                "changePercent": bond['changePercent'],
                "source": f"中债信息({bond['date']})",
                "updateTime": now
            })
        else:
            # 获取失败时使用默认值，避免前端显示 "--"
            indices.append({
                "code": "bond_yield",
                "name": "10年期国债收益率",
                "value": 1.83,
                "change": 0,
                "changePercent": 0,
                "source": "基准值",
                "updateTime": now
            })

        result = {
            "success": True,
            "data": indices,
            "message": f"获取市场指数成功 ({len(indices)}个)"
        }
        _INDICES_CACHE = result
        _INDICES_CACHE_TIME = now_ts
        return result

    except Exception:
        logger.exception("获取市场指数失败，请稍后重试")
        return {
            "success": False,
            "data": [],
            "message": "获取市场指数失败，请稍后重试"
        }


@adapter_app.get("/api/market-indices/history")
async def market_indices_history(
    code: str = Query(..., description="指数代码"),
    days: int = Query(30, description="天数")
):
    """获取指数历史数据"""
    try:
        today = datetime.date.today()
        start_date = (today - datetime.timedelta(days=days)).strftime('%Y-%m-%d')

        with get_conn() as conn:
                    cursor = conn.cursor()
            
                    cursor.execute("""
                        SELECT trade_date, AVG(close_price) as avg_price, AVG(change_pct) as avg_change
                        FROM business.fund_prices
                        WHERE trade_date >= %s
                        GROUP BY trade_date
                        ORDER BY trade_date ASC
                    """, (start_date,))
            
                    rows = cursor.fetchall()

        history = []
        for row in rows:
            history.append({
                "code": code,
                "date": row[0],
                "value": (row[1] or 0) * 100,
                "change": row[2] or 0,
                "changePercent": row[2] or 0
            })

        return {
            "success": True,
            "data": history,
            "message": f"获取指数历史成功 ({len(history)}条)"
        }
    except Exception:
        logger.exception("获取指数历史失败，请稍后重试")
        return {
            "success": False,
            "data": [],
            "message": "获取指数历史失败，请稍后重试"
        }


@adapter_app.get("/api/market-indices/detail")
async def market_indices_detail(code: str = Query(..., description="指数代码")):
    """获取单个指数详情"""
    # 直接返回模拟数据
    details = {
        "reits_total": {"code": "reits_total", "name": "REITs总指数", "value": 1000, "change": 0.5, "changePercent": 0.5, "source": "自计算"},
        "sh_index": {"code": "sh_index", "name": "沪深REITs", "value": 81, "change": 0, "changePercent": 0, "source": "自计算"},
        "dividend": {"code": "dividend", "name": "分红指数", "value": 1000, "change": 0.5, "changePercent": 0.5, "source": "自计算"},
        "bond_yield": {"code": "bond_yield", "name": "债券收益率", "value": 2.85, "change": -0.02, "changePercent": -0.7, "source": "中债信息网"}
    }

    if code in details:
        return {
            "success": True,
            "data": details[code],
            "message": "获取指数详情成功"
        }

    return {
        "success": False,
        "data": None,
        "message": f"未知指数: {code}"
    }


@adapter_app.get("/api/market-indices/overview")
async def market_indices_overview():
    """获取市场概况"""
    try:
        with get_conn() as conn:
                    cursor = conn.cursor()
            
                    cursor.execute("SELECT COUNT(*) FROM business.funds")
                    total_indices = cursor.fetchone()[0] or 0
            
                    cursor.execute("""
                        SELECT COUNT(*) FROM business.fund_prices
                        WHERE trade_date = (SELECT MAX(trade_date) FROM business.fund_prices)
                          AND change_pct > 0
                    """)
                    up_count = cursor.fetchone()[0] or 0
            
                    cursor.execute("""
                        SELECT COUNT(*) FROM business.fund_prices
                        WHERE trade_date = (SELECT MAX(trade_date) FROM business.fund_prices)
                          AND change_pct < 0
                    """)
                    down_count = cursor.fetchone()[0] or 0
            
                    cursor.execute("""
                        SELECT AVG(change_pct) FROM business.fund_prices
                        WHERE trade_date = (SELECT MAX(trade_date) FROM business.fund_prices)
                    """)
                    avg_change = cursor.fetchone()[0] or 0
            

        return {
            "success": True,
            "data": {
                "totalIndices": total_indices,
                "upCount": up_count,
                "downCount": down_count,
                "avgChange": avg_change
            },
            "message": "获取市场概况成功"
        }
    except Exception:
        logger.exception("获取市场概况失败，请稍后重试")
        return {
            "success": False,
            "data": None,
            "message": "获取市场概况失败，请稍后重试"
        }


# ==================== 实时行情端点 ====================

@adapter_app.get("/api/quotes/realtime")
async def get_realtime_quotes():
    """获取所有REITs实时行情（从新浪财经API），合并数据库派息率"""
    try:
        quotes = realtime_quotes.fetch_all_reits_quotes()

        # 从数据库获取派息率并合并
        try:
            with get_conn() as conn:
                            cursor = conn.cursor()
                            cursor.execute("SELECT fund_code, dividend_yield FROM business.funds WHERE dividend_yield IS NOT NULL")
                            yield_map = {row[0]: row[1] for row in cursor.fetchall()}

            for q in quotes:
                code = q.get('fund_code')
                if code in yield_map:
                    q['dividend_yield'] = yield_map[code]
                    q['yield'] = yield_map[code]
        except psycopg2.Error:
            logger.exception("合并派息率失败")

        return {
            "success": True,
            "data": quotes,
            "total": len(quotes),
            "timestamp": datetime.datetime.now().isoformat(),
            "message": f"获取实时行情成功 ({len(quotes)}只)"
        }
    except Exception:
        logger.exception("获取实时行情失败，请稍后重试")
        return {
            "success": False,
            "data": [],
            "total": 0,
            "message": "获取实时行情失败，请稍后重试"
        }


@adapter_app.get("/api/quotes/single")
async def get_single_quote(code: str = Query(..., description="基金代码")):
    """获取单个基金实时行情"""
    try:
        quotes = realtime_quotes.fetch_realtime_quote([code])
        if quotes:
            return {
                "success": True,
                "data": quotes[0],
                "message": "获取行情成功"
            }
        return {
            "success": False,
            "data": None,
            "message": f"未找到基金 {code} 的行情"
        }
    except Exception:
        logger.exception("获取行情失败，请稍后重试")
        return {
            "success": False,
            "data": None,
            "message": "获取行情失败，请稍后重试"
        }


# ==================== 公告数据端点 ====================

@adapter_app.get("/api/announcements")
async def announcements_list(
    page: int = Query(1, description="页码", ge=1),
    page_size: int = Query(50, description="每页条数", ge=1, le=500),
    fund_code: str = Query(None, description="基金代码筛选"),
    category: str = Query(None, description="分类筛选"),
    exchange: str = Query(None, description="交易所筛选: SSE/SZSE"),
    search: str = Query(None, description="标题搜索关键词"),
    start_date: str = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(None, description="结束日期 YYYY-MM-DD"),
    days: int = Query(None, description="最近天数筛选"),
    limit: int = Query(None, description="兼容旧版: 返回条数"),
):
    """获取公告列表（支持分页、筛选、搜索）"""
    try:
        # 兼容旧版 limit 参数
        if limit is not None and page_size == 50:
            page_size = limit

        # days 参数转换为日期范围
        effective_start_date = start_date
        effective_end_date = end_date
        if days:
            cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y-%m-%d')
            effective_start_date = cutoff

        offset = (page - 1) * page_size

        data = announcements.get_cached_announcements(
            limit=page_size,
            offset=offset,
            fund_code=fund_code,
            category=category,
            exchange=exchange,
            search=search,
            start_date=effective_start_date,
            end_date=effective_end_date,
        )

        total = announcements.count_cached_announcements(
            fund_code=fund_code,
            category=category,
            exchange=exchange,
            search=search,
            start_date=effective_start_date,
            end_date=effective_end_date,
        )

        return {
            "success": True,
            "data": data,
            "total": total,
            "page": page,
            "page_size": page_size,
            "message": f"获取公告成功 ({len(data)}条)"
        }
    except Exception:
        logger.exception("获取公告失败，请稍后重试")
        return {
            "success": False,
            "data": [],
            "total": 0,
            "message": "获取公告失败，请稍后重试"
        }


@adapter_app.get("/api/announcements/stats")
async def announcements_stats():
    """获取公告统计信息"""
    try:
        with get_conn() as conn:
            cursor = conn.cursor()

            # 总数
            cursor.execute("SELECT COUNT(*) FROM business.announcements")
            total = cursor.fetchone()[0]

            # 按交易所统计
            cursor.execute("""
                SELECT exchange, COUNT(*) FROM business.announcements
                WHERE exchange IS NOT NULL GROUP BY exchange
            """)
            by_exchange = {row[0] or 'UNKNOWN': row[1] for row in cursor.fetchall()}

            # 按分类统计
            cursor.execute("""
                SELECT category, COUNT(*) FROM business.announcements
                WHERE category IS NOT NULL GROUP BY category
            """)
            by_category = {row[0] or 'other': row[1] for row in cursor.fetchall()}

            # 涉及的基金数量
            cursor.execute("""
                SELECT COUNT(DISTINCT fund_code) FROM business.announcements
            """)
            funds_count = cursor.fetchone()[0]

        return {
            "success": True,
            "data": {
                "total": total,
                "by_exchange": by_exchange,
                "by_category": by_category,
                "funds_count": funds_count,
            },
            "message": "获取公告统计成功"
        }
    except Exception:
        logger.exception("获取公告统计失败，请稍后重试")
        return {
            "success": False,
            "data": None,
            "message": "获取公告统计失败，请稍后重试"
        }


@adapter_app.get("/api/announcements/quality")
async def announcements_quality():
    """获取公告数据质量报告"""
    try:
        with get_conn() as conn:
            cursor = conn.cursor()

            # 总数
            cursor.execute("SELECT COUNT(*) FROM business.announcements")
            total = cursor.fetchone()[0]

            # 缺失PDF
            cursor.execute("""
                SELECT COUNT(*) FROM business.announcements
                WHERE pdf_url IS NULL OR pdf_url = ''
            """)
            missing_pdf = cursor.fetchone()[0]

            # 分类为other（未成功分类）
            cursor.execute("""
                SELECT COUNT(*) FROM business.announcements
                WHERE category = 'other' OR category IS NULL
            """)
            missing_category = cursor.fetchone()[0]

            # 重复标题（同一基金同一标题）
            cursor.execute("""
                SELECT COUNT(*) FROM (
                    SELECT fund_code, title, COUNT(*) as cnt
                    FROM business.announcements
                    GROUP BY fund_code, title
                    HAVING COUNT(*) > 1
                ) t
            """)
            duplicate_titles = cursor.fetchone()[0]

            # 未来日期（publish_date > today）
            cursor.execute("""
                SELECT COUNT(*) FROM business.announcements
                WHERE publish_date > CURRENT_DATE
            """)
            suspicious_dates = cursor.fetchone()[0]

            # 低置信度
            cursor.execute("""
                SELECT COUNT(*) FROM business.announcements
                WHERE confidence < 80
            """)
            low_confidence = cursor.fetchone()[0]

            # 涉及的基金数量
            cursor.execute("""
                SELECT COUNT(DISTINCT fund_code) FROM business.announcements
            """)
            funds_count = cursor.fetchone()[0]

        return {
            "success": True,
            "data": {
                "total": total,
                "missing_pdf": missing_pdf,
                "missing_category": missing_category,
                "duplicate_titles": duplicate_titles,
                "suspicious_dates": suspicious_dates,
                "low_confidence": low_confidence,
                "funds_count": funds_count,
            },
            "message": "获取数据质量报告成功"
        }
    except Exception:
        logger.exception("获取数据质量报告失败")
        return {
            "success": False,
            "data": None,
            "message": "获取数据质量报告失败"
        }


@adapter_app.get("/api/announcements/quality/by-fund")
async def announcements_quality_by_fund(fund_code: str = Query(..., description="基金代码")):
    """获取指定基金的数据质量报告"""
    try:
        with get_conn() as conn:
            cursor = conn.cursor()

            # 总数
            cursor.execute("""
                SELECT COUNT(*) FROM business.announcements WHERE fund_code = %s
            """, (fund_code,))
            total = cursor.fetchone()[0]

            # 缺失PDF
            cursor.execute("""
                SELECT COUNT(*) FROM business.announcements
                WHERE fund_code = %s AND (pdf_url IS NULL OR pdf_url = '')
            """, (fund_code,))
            missing_pdf = cursor.fetchone()[0]

            # 分类分布
            cursor.execute("""
                SELECT category, COUNT(*) FROM business.announcements
                WHERE fund_code = %s GROUP BY category
            """, (fund_code,))
            categories = {row[0] or 'other': row[1] for row in cursor.fetchall()}

        return {
            "success": True,
            "data": {
                "fund_code": fund_code,
                "total": total,
                "missing_pdf": missing_pdf,
                "categories": categories,
            },
            "message": f"获取基金 {fund_code} 数据质量报告成功"
        }
    except Exception:
        logger.exception("获取基金数据质量报告失败")
        return {
            "success": False,
            "data": None,
            "message": "获取基金数据质量报告失败"
        }


@adapter_app.get("/api/announcements/latest")
async def announcements_latest(
    limit: int = Query(20, description="返回条数"),
    live: bool = Query(False, description="是否实时抓取（交易时间用）")
):
    """获取最新公告（实时抓取）"""
    try:
        data = announcements.fetch_all_announcements(live=live, limit_per_stock=3)

        return {
            "success": True,
            "data": data[:limit],
            "total": min(len(data), limit),
            "message": f"获取最新公告成功"
        }
    except Exception:
        logger.exception("获取最新公告失败，请稍后重试")
        return {
            "success": False,
            "data": [],
            "message": "获取最新公告失败，请稍后重试"
        }


@adapter_app.post("/api/crawl/announcements")
async def crawl_announcements():
    """触发实时爬取所有REITs公告"""
    try:
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        def fetch_data():
            return announcements.fetch_all_announcements(live=True, limit_per_stock=5)

        with ThreadPoolExecutor(max_workers=3) as executor:
            future = executor.submit(fetch_data)
            data = future.result(timeout=120)

        return {
            "success": True,
            "data": {"count": len(data)},
            "message": f"爬取成功，共{len(data)}条公告"
        }
    except Exception:
        logger.exception("爬取失败，请稍后重试")
        return {
            "success": False,
            "data": {},
            "message": "爬取失败，请稍后重试"
        }


@adapter_app.post("/api/announcements/mark-read")
async def mark_announcement_read(announcement_id: int = Query(..., description="公告ID")):
    """标记公告已读"""
    success = announcements.mark_as_read(announcement_id)
    return {
        "success": success,
        "message": "标记已读成功" if success else "标记已读失败"
    }


# ==================== 公告状态更新 ====================

@adapter_app.put("/api/announcements/{announcement_id}/status")
async def update_announcement_status(
    announcement_id: int,
    status: str = Body(..., description="状态: draft/pending/published/archived"),
    changed_by: str = Body("system", description="操作人")
):
    """更新公告状态"""
    valid_statuses = ['draft', 'pending', 'published', 'archived']
    if status not in valid_statuses:
        return {
            "success": False,
            "message": f"无效状态。可选: {valid_statuses}"
        }

    try:
        with get_conn() as conn:
                    cursor = conn.cursor()
            
                    # 验证状态流转规则
                    cursor.execute("SELECT status FROM business.announcements WHERE id = %s", (announcement_id,))
                    row = cursor.fetchone()
                    if not row:
                        return {"success": False, "message": "公告不存在"}
            
                    current_status = row[0]
            
                    # 状态流转验证
                    valid_transitions = {
                        'draft': ['pending'],
                        'pending': ['published', 'draft'],
                        'published': ['archived'],
                        'archived': ['published']
                    }
            
                    if status not in valid_transitions.get(current_status, []):
                        return {
                            "success": False,
                            "message": f"不允许的状态流转: {current_status} → {status}"
                        }
            
                    # 更新状态
                    cursor.execute("""
                        UPDATE business.announcements
                        SET status = %s, status_changed_at = NOW(), status_changed_by = %s
                        WHERE id = %s
                    """, (status, changed_by, announcement_id))
            
                    conn.commit()

        return {
            "success": True,
            "message": f"状态已更新: {current_status} → {status}"
        }
    except Exception:
        logger.exception("更新失败，请稍后重试")
        return {
            "success": False,
            "message": "更新失败，请稍后重试"
        }


# ==================== 实时档口数据代理 ====================

@adapter_app.get("/api/quotes/orderbook")
async def get_orderbook(code: str = Query(..., description="基金代码")):
    """代理新浪5档买卖盘数据（解决CORS跨域）"""
    try:
        import requests
        prefix = 'sh' if code.startswith('5') else 'sz'
        url = f'https://hq.sinajs.cn/list={prefix}{code}'
        headers = {
            'Referer': 'https://finance.sina.com.cn/',
            'User-Agent': 'Mozilla/5.0'
        }
        r = requests.get(url, headers=headers, timeout=10)
        r.encoding = 'gbk'
        text = r.text

        raw = text.split('"')[1] if '"' in text else ''
        if not raw:
            return {'success': False, 'data': None, 'message': '获取数据失败'}

        fields = raw.split(',')
        currentPrice = float(fields[3])
        prevClose = float(fields[2])

        # 解析5档买卖盘（Sina格式：量,价,量,价...）
        # Bid: 价格[11,13,15,17,19] 量[10,12,14,16,18] (股)
        # Ask: 价格[21,23,25,27,29] 量[20,22,24,26,28]
        def safe_float(val):
            try: return float(val)
            except: return 0
        def safe_int(val):
            try: return int(float(val))
            except: return 0

        bids, asks = [], []
        for i in range(5):
            bp = safe_float(fields[11 + i * 2])
            bv = safe_int(fields[10 + i * 2])
            ap = safe_float(fields[21 + i * 2])
            av = safe_int(fields[20 + i * 2])
            if bp > 0: bids.append({'price': bp, 'vol': bv})
            if ap > 0: asks.append({'price': ap, 'vol': av})

        return {
            'success': True,
            'data': {
                'code': code,
                'currentPrice': currentPrice,
                'prevClose': prevClose,
                'change': round(currentPrice - prevClose, 3),
                'changePercent': round((currentPrice - prevClose) / prevClose * 100, 2),
                'bids': bids,
                'asks': asks,
                'time': fields[31] + ' ' + fields[32] if len(fields) > 32 else ''
            },
            'message': '获取档口数据成功'
        }
    except (IndexError, ValueError, ZeroDivisionError, TypeError) as e:
        logger.exception("获取档口数据失败")
        return {'success': False, 'data': None, 'message': '获取档口数据失败，请稍后重试'}


# ==================== 健康检查 ====================

@adapter_app.get("/health")
async def health_check():
    """健康检查"""
    try:
        with get_conn() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM business.funds")
                    fund_count = cursor.fetchone()[0]
                    cursor.execute("SELECT COUNT(*) FROM business.fund_prices")
                    price_count = cursor.fetchone()[0]

        return {
            "status": "ok",
            "service": "api-adapter",
            "database": "connected",
            "funds_count": fund_count,
            "prices_count": price_count,
            "timestamp": datetime.datetime.now().isoformat()
        }
    except psycopg2.Error as e:
        logger.exception("Health check failed")
        return {
            "status": "error",
            "service": "api-adapter",
            "database": "disconnected",
            "timestamp": datetime.datetime.now().isoformat()
        }


if __name__ == "__main__":
    logger.info(f"API adapter layer starting on port {settings.PORT}")
    logger.info("Database: PostgreSQL")
    logger.info("Funds and prices loaded")
    uvicorn.run(
        "api_adapter:adapter_app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
        log_level="info"
    )
