#!/usr/bin/env python3
"""
API适配层 - 统一前后端路径格式
使用本地SQLite数据库作为数据源
"""

import os
import sys
from pathlib import Path
from fastapi import FastAPI, Query, Body
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import datetime
import sqlite3

# 添加项目根目录到路径
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / 'services'))

from core.config import settings
from services import realtime_quotes, announcements

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

# 数据库路径 - 绝对路径
DB_PATH = r"D:\tools\消费看板5（前端）\backend\database\reits.db"


def get_db_connection():
    """获取数据库连接"""
    return sqlite3.connect(DB_PATH)


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
    """获取基金列表"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT fund_code, fund_name, exchange, ipo_date, nav, status
            FROM funds
            ORDER BY exchange, fund_code
        """)
        rows = cursor.fetchall()
        conn.close()

        funds = []
        for row in rows:
            funds.append({
                "code": row[0],
                "name": row[1],
                "exchange": row[2],
                "listing_date": row[3],
                "nav": row[4] or 0,
                "status": row[5] or "listed"
            })

        return {
            "success": True,
            "data": funds,
            "total": len(funds),
            "message": "获取基金列表成功"
        }
    except Exception as e:
        return {
            "success": False,
            "data": [],
            "message": f"获取基金列表失败: {str(e)}"
        }


@adapter_app.get("/api/funds/detail")
async def funds_detail_adapter(code: str = Query(..., description="基金代码")):
    """基金详情"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 获取基金基本信息
        cursor.execute("""
            SELECT fund_code, fund_name, full_name, exchange, ipo_date,
                   ipo_price, total_shares, nav, manager, asset_type
            FROM funds WHERE fund_code = ?
        """, (code,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return {
                "success": False,
                "data": None,
                "message": "基金不存在"
            }

        # 获取最新价格
        conn2 = get_db_connection()
        cursor2 = conn2.cursor()
        cursor2.execute("""
            SELECT trade_date, close_price, change_pct, volume, premium_rate
            FROM fund_prices
            WHERE fund_code = ?
            ORDER BY trade_date DESC LIMIT 1
        """, (code,))
        price_row = cursor2.fetchone()
        conn2.close()

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
                "scale": (row[5] * row[6] / 100000000) if row[5] and row[6] else 0,
                "manager": row[8],
                "asset_type": row[9],
            },
            "message": "获取基金详情成功"
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"获取基金详情失败: {str(e)}"
        }


@adapter_app.get("/api/funds/price-history")
async def price_history_adapter(
    code: str = Query(..., description="基金代码"),
    time_range: str = Query("daily", description="时间范围: minute/daily/weekly")
):
    """价格历史"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 根据range确定日期范围
        today = datetime.date.today()
        if time_range == "minute":
            days = 1
        elif time_range == "weekly":
            days = 90
        else:
            days = 30

        start_date = (today - datetime.timedelta(days=days)).strftime('%Y-%m-%d')

        cursor.execute("""
            SELECT trade_date, open_price, high_price, low_price,
                   close_price, volume, amount, change_pct
            FROM fund_prices
            WHERE fund_code = ? AND trade_date >= ?
            ORDER BY trade_date ASC
        """, (code, start_date))

        rows = cursor.fetchall()
        conn.close()

        history = []
        for row in rows:
            history.append({
                "date": row[0],
                "open": row[1] or 0,
                "high": row[2] or 0,
                "low": row[3] or 0,
                "price": row[4] or 0,
                "volume": row[5] or 0,
                "amount": row[6] or 0,
                "change": row[7] or 0
            })

        return {
            "success": True,
            "data": history,
            "message": f"获取价格历史成功 ({len(history)}条)"
        }
    except Exception as e:
        return {
            "success": False,
            "data": [],
            "message": f"获取价格历史失败: {str(e)}"
        }


@adapter_app.get("/api/funds/related")
async def related_funds_adapter(
    sector: str = Query(None, description="板块名称"),
    excludeCode: str = Query(None, description="排除的基金代码")
):
    """相关基金（同板块）"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 获取所有基金
        cursor.execute("""
            SELECT fund_code, fund_name, exchange, asset_type
            FROM funds
            WHERE fund_code != ? OR ? IS NULL
            ORDER BY fund_code
            LIMIT 20
        """, (excludeCode or "", excludeCode))

        rows = cursor.fetchall()
        conn.close()

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
    except Exception as e:
        return {
            "success": False,
            "data": [],
            "message": f"获取相关基金失败: {str(e)}"
        }


@adapter_app.get("/api/funds/financial")
async def financial_data_adapter(code: str = Query(..., description="基金代码")):
    """财务数据"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 获取基金信息作为财务数据
        cursor.execute("""
            SELECT fund_code, fund_name, nav, total_shares, ipo_price
            FROM funds WHERE fund_code = ?
        """, (code,))
        row = cursor.fetchone()
        conn.close()

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
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"获取财务数据失败: {str(e)}"
        }


@adapter_app.get("/api/funds/operation")
async def operation_data_adapter(code: str = Query(..., description="基金代码")):
    """运营数据"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT fund_code, fund_name, asset_type, underlying_assets
            FROM funds WHERE fund_code = ?
        """, (code,))
        row = cursor.fetchone()
        conn.close()

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
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"获取运营数据失败: {str(e)}"
        }


@adapter_app.get("/api/funds/dividends")
async def dividends_adapter(code: str = Query(..., description="基金代码")):
    """分红数据"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT dividend_date, dividend_amount, record_date, ex_dividend_date
            FROM dividends
            WHERE fund_code = ?
            ORDER BY dividend_date DESC
            LIMIT 10
        """, (code,))

        rows = cursor.fetchall()
        conn.close()

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
    except Exception as e:
        return {
            "success": False,
            "data": [],
            "message": f"获取分红数据失败: {str(e)}"
        }


# ==================== 分红日历端点 ====================

@adapter_app.get("/api/dividend-calendar/list")
async def dividend_calendar_list():
    """获取所有分红记录"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT d.id, d.fund_code, f.fund_name, d.dividend_date,
                   d.dividend_amount, d.record_date, d.ex_dividend_date
            FROM dividends d
            LEFT JOIN funds f ON d.fund_code = f.fund_code
            ORDER BY d.dividend_date DESC
            LIMIT 100
        """)

        rows = cursor.fetchall()
        conn.close()

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
            "message": f"获取分红日历成功 ({len(dividends)}条)"
        }
    except Exception as e:
        return {
            "success": False,
            "data": [],
            "total": 0,
            "message": f"获取分红日历失败: {str(e)}"
        }


@adapter_app.get("/api/dividend-calendar/stats/summary")
async def dividend_stats_summary():
    """获取分红统计摘要"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 总分红次数
        cursor.execute("SELECT COUNT(*) FROM dividends")
        total_count = cursor.fetchone()[0]

        # 总分红金额
        cursor.execute("SELECT COALESCE(SUM(dividend_amount), 0) FROM dividends")
        total_amount = cursor.fetchone()[0]

        # 今年分红次数
        cursor.execute("""
            SELECT COUNT(*) FROM dividends
            WHERE strftime('%Y', dividend_date) = strftime('%Y', 'now')
        """)
        year_count = cursor.fetchone()[0]

        # 今年分红金额
        cursor.execute("""
            SELECT COALESCE(SUM(dividend_amount), 0) FROM dividends
            WHERE strftime('%Y', dividend_date) = strftime('%Y', 'now')
        """)
        year_amount = cursor.fetchone()[0]

        # 待实施分红（ex_dividend_date > today）
        cursor.execute("""
            SELECT COUNT(*) FROM dividends
            WHERE ex_dividend_date > date('now')
        """)
        pending_count = cursor.fetchone()[0]

        conn.close()

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
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"获取分红统计失败: {str(e)}"
        }


@adapter_app.get("/api/dividend-calendar/upcoming")
async def dividend_upcoming(days: int = Query(30, description="未来天数")):
    """获取即将分红的基金"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        future_date = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime('%Y-%m-%d')

        cursor.execute("""
            SELECT d.id, d.fund_code, f.fund_name, d.dividend_date,
                   d.dividend_amount, d.record_date, d.ex_dividend_date
            FROM dividends d
            LEFT JOIN funds f ON d.fund_code = f.fund_code
            WHERE d.ex_dividend_date >= date('now')
              AND d.ex_dividend_date <= ?
            ORDER BY d.ex_dividend_date ASC
            LIMIT 20
        """, (future_date,))

        rows = cursor.fetchall()
        conn.close()

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
    except Exception as e:
        return {
            "success": False,
            "data": [],
            "total": 0,
            "message": f"获取即将分红失败: {str(e)}"
        }


# ==================== 市场指数端点 ====================

def get_sh_index_from_sina():
    """从新浪获取上证指数"""
    try:
        import requests
        headers = {'Referer': 'https://finance.sina.com.cn'}
        r = requests.get('https://hq.sinajs.cn/list=sh000001', headers=headers, timeout=5)
        r.encoding = 'gbk'
        data = r.text
        if '"' in data:
            parts = data.split('"')[1].split(',')
            if len(parts) > 3:
                price = float(parts[3])
                prev = float(parts[2])
                change_pct = ((price - prev) / prev * 100) if prev > 0 else 0
                return {
                    "value": round(price, 2),
                    "change": round(price - prev, 3),
                    "changePercent": round(change_pct, 2)
                }
    except Exception as e:
        print(f"获取上证指数失败: {e}")
    return None


@adapter_app.get("/api/market-indices/list")
async def market_indices_list():
    """获取市场指数列表"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 从market_indices表读取数据（由Node爬虫写入）
        cursor.execute("SELECT code, name, value, change, change_percent, source, updated_at FROM market_indices")
        rows = cursor.fetchall()
        conn.close()

        if rows and len(rows) > 0:
            indices = []
            now = datetime.datetime.now().isoformat()
            for row in rows:
                code, name, value, change, change_percent, source, updated_at = row
                # 补充上证指数实时数据
                if code == 'sh_index':
                    sh_data = get_sh_index_from_sina()
                    if sh_data:
                        value = sh_data["value"]
                        change = sh_data["change"]
                        change_percent = sh_data["changePercent"]
                        source = "sina"
                        updated_at = now
                indices.append({
                    "code": code,
                    "name": name,
                    "value": value,
                    "change": change,
                    "changePercent": change_percent,
                    "source": source,
                    "updateTime": updated_at or now
                })

            return {
                "success": True,
                "data": indices,
                "message": "获取市场指数成功"
            }

        # 如果表为空，返回默认占位值
        return {
            "success": True,
            "data": [
                {"code": "reits_total", "name": "中证REITs全收益", "value": 1013.78, "change": 0, "changePercent": 0, "source": "待更新", "updateTime": datetime.datetime.now().isoformat()},
                {"code": "bond_yield", "name": "10年期国债收益率", "value": 1.83, "change": 0, "changePercent": 0, "source": "待更新", "updateTime": datetime.datetime.now().isoformat()},
                {"code": "sh_index", "name": "上证指数", "value": 4051.43, "change": 0, "changePercent": 0, "source": "sina", "updateTime": datetime.datetime.now().isoformat()},
                {"code": "dividend", "name": "中证红利", "value": 5712.79, "change": 0, "changePercent": 0, "source": "待更新", "updateTime": datetime.datetime.now().isoformat()}
            ],
            "message": "使用默认占位值"
        }

    except Exception as e:
        return {
            "success": False,
            "data": [],
            "message": f"获取市场指数失败: {str(e)}"
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

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT trade_date, AVG(close_price) as avg_price, AVG(change_pct) as avg_change
            FROM fund_prices
            WHERE trade_date >= ?
            GROUP BY trade_date
            ORDER BY trade_date ASC
        """, (start_date,))

        rows = cursor.fetchall()
        conn.close()

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
    except Exception as e:
        return {
            "success": False,
            "data": [],
            "message": f"获取指数历史失败: {str(e)}"
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
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM funds")
        total_indices = cursor.fetchone()[0] or 0

        cursor.execute("""
            SELECT COUNT(*) FROM fund_prices
            WHERE trade_date = (SELECT MAX(trade_date) FROM fund_prices)
              AND change_pct > 0
        """)
        up_count = cursor.fetchone()[0] or 0

        cursor.execute("""
            SELECT COUNT(*) FROM fund_prices
            WHERE trade_date = (SELECT MAX(trade_date) FROM fund_prices)
              AND change_pct < 0
        """)
        down_count = cursor.fetchone()[0] or 0

        cursor.execute("""
            SELECT AVG(change_pct) FROM fund_prices
            WHERE trade_date = (SELECT MAX(trade_date) FROM fund_prices)
        """)
        avg_change = cursor.fetchone()[0] or 0

        conn.close()

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
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"获取市场概况失败: {str(e)}"
        }


# ==================== 实时行情端点 ====================

@adapter_app.get("/api/quotes/realtime")
async def get_realtime_quotes():
    """获取所有REITs实时行情（从新浪财经API）"""
    try:
        quotes = realtime_quotes.fetch_all_reits_quotes()

        return {
            "success": True,
            "data": quotes,
            "total": len(quotes),
            "timestamp": datetime.datetime.now().isoformat(),
            "message": f"获取实时行情成功 ({len(quotes)}只)"
        }
    except Exception as e:
        return {
            "success": False,
            "data": [],
            "total": 0,
            "message": f"获取实时行情失败: {str(e)}"
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
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"获取行情失败: {str(e)}"
        }


# ==================== 公告数据端点 ====================

@adapter_app.get("/api/announcements")
async def announcements_list(
    limit: int = Query(100, description="返回条数"),
    category: str = Query(None, description="分类筛选"),
    code: str = Query(None, description="基金代码筛选"),
    days: int = Query(None, description="最近天数筛选")
):
    """获取公告列表"""
    try:
        # 获取缓存数据
        if category:
            data = announcements.get_announcements_by_category(category, limit)
        elif code:
            data = announcements.get_announcements_by_fund(code, limit)
        else:
            data = announcements.get_cached_announcements(limit)

        # 按天数筛选
        if days:
            import datetime
            cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y-%m-%d')
            data = [d for d in data if d.get('publish_date', '') >= cutoff]

        return {
            "success": True,
            "data": data,
            "total": len(data),
            "message": f"获取公告成功 ({len(data)}条)"
        }
    except Exception as e:
        return {
            "success": False,
            "data": [],
            "message": f"获取公告失败: {str(e)}"
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
    except Exception as e:
        return {
            "success": False,
            "data": [],
            "message": f"获取最新公告失败: {str(e)}"
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
    except Exception as e:
        return {
            "success": False,
            "data": {},
            "message": f"爬取失败: {str(e)}"
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
        conn = get_db_connection()
        cursor = conn.cursor()

        # 验证状态流转规则
        cursor.execute("SELECT status FROM announcements WHERE id = ?", (announcement_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
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
            conn.close()
            return {
                "success": False,
                "message": f"不允许的状态流转: {current_status} → {status}"
            }

        # 更新状态
        cursor.execute("""
            UPDATE announcements
            SET status = ?, status_changed_at = datetime('now'), status_changed_by = ?
            WHERE id = ?
        """, (status, changed_by, announcement_id))

        conn.commit()
        conn.close()

        return {
            "success": True,
            "message": f"状态已更新: {current_status} → {status}"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"更新失败: {str(e)}"
        }


# ==================== 健康检查 ====================

@adapter_app.get("/health")
async def health_check():
    """健康检查"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM funds")
        fund_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM fund_prices")
        price_count = cursor.fetchone()[0]
        conn.close()

        return {
            "status": "ok",
            "service": "api-adapter",
            "database": "connected",
            "funds_count": fund_count,
            "prices_count": price_count,
            "timestamp": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "service": "api-adapter",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.datetime.now().isoformat()
        }


if __name__ == "__main__":
    print(f"API adapter layer starting on port {settings.PORT}")
    print(f"Database: {DB_PATH}")
    print(f"Funds: {settings.PORT} | Prices: loaded")
    uvicorn.run(
        "api_adapter:adapter_app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level="info"
    )
