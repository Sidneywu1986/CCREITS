"""
Health check and monitoring endpoints
"""
import time
from datetime import datetime, timezone
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

try:
    import psutil
except ImportError:
    psutil = None

router = APIRouter(tags=["health"])

# Simple in-memory metrics (replace with prometheus in production)
_request_stats = {"total": 0, "errors": 0, "start_time": time.time()}


@router.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Track request counts and errors."""
    _request_stats["total"] += 1
    try:
        response = await call_next(request)
        if response.status_code >= 500:
            _request_stats["errors"] += 1
        return response
    except Exception:
        _request_stats["errors"] += 1
        raise


@router.get("/health")
async def health_check():
    """System health: DB, Redis, Milvus."""
    checks = {}
    overall = "healthy"

    # Database
    try:
        from core.db_pool import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT 1 as ok")
            checks["database"] = "ok" if row and row["ok"] == 1 else "fail"
    except Exception as e:
        checks["database"] = f"fail: {e}"
        overall = "degraded"

    # Redis
    try:
        from core.cache import get_redis
        r = get_redis()
        r.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"fail: {e}"
        overall = "degraded"

    # Milvus
    try:
        from vector.milvus_client import get_milvus_client
        client = get_milvus_client()
        checks["milvus"] = "ok" if client.is_healthy() else "fail"
    except Exception as e:
        checks["milvus"] = f"fail: {e}"

    status_code = 200 if overall == "healthy" else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": overall,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": checks,
        },
    )


@router.get("/metrics")
async def metrics():
    """Basic operational metrics."""
    uptime = time.time() - _request_stats["start_time"]
    result = {
        "uptime_seconds": round(uptime, 2),
        "requests": {
            "total": _request_stats["total"],
            "errors": _request_stats["errors"],
            "error_rate": round(_request_stats["errors"] / max(_request_stats["total"], 1), 4),
        },
    }
    if psutil:
        result["system"] = {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory": {
                "total_gb": round(psutil.virtual_memory().total / (1024 ** 3), 2),
                "used_gb": round(psutil.virtual_memory().used / (1024 ** 3), 2),
                "percent": psutil.virtual_memory().percent,
            },
            "disk": {
                "total_gb": round(psutil.disk_usage("/").total / (1024 ** 3), 2),
                "used_gb": round(psutil.disk_usage("/").used / (1024 ** 3), 2),
                "percent": round(psutil.disk_usage("/").used / psutil.disk_usage("/").total * 100, 2),
            },
        }
    return result
