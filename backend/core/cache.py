"""
Redis cache wrapper — singleton, lazy init.
"""
import os
import json
from typing import Optional, Any

_redis = None


def get_redis():
    """Return Redis client (sync). For async see aioredis."""
    global _redis
    if _redis is None:
        import redis
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", 6379))
        db = int(os.getenv("REDIS_DB", 0))
        _redis = redis.Redis(
            host=host, port=port, db=db,
            socket_connect_timeout=2,
            socket_timeout=2,
            decode_responses=True,
        )
    return _redis


def cache_get(key: str) -> Optional[Any]:
    """Get cached value (JSON decoded)."""
    try:
        r = get_redis()
        data = r.get(key)
        if data:
            return json.loads(data)
    except Exception:
        pass
    return None


def cache_set(key: str, value: Any, ttl: int = 300) -> bool:
    """Set cache value (JSON encoded) with TTL in seconds."""
    try:
        r = get_redis()
        r.setex(key, ttl, json.dumps(value, default=str))
        return True
    except Exception:
        return False


def cache_delete(key: str) -> bool:
    try:
        r = get_redis()
        r.delete(key)
        return True
    except Exception:
        return False


def cache_delete_pattern(pattern: str) -> bool:
    try:
        r = get_redis()
        for k in r.scan_iter(match=pattern):
            r.delete(k)
        return True
    except Exception:
        return False
