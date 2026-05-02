"""
Asyncpg connection pool — singleton, initialized on first use.
"""
import asyncpg

_pool = None


async def get_pool() -> asyncpg.Pool:
    """Return the global connection pool (async lazy init)."""
    global _pool
    if _pool is None:
        from core.config import settings
        pg = settings.PG_CONFIG
        dsn = (
            f"postgres://{pg['user']}:{pg['password']}"
            f"@{pg['host']}:{pg['port']}/{pg['database']}"
        )
        _pool = await asyncpg.create_pool(
            dsn,
            min_size=2,
            max_size=10,
            command_timeout=30,
            server_settings={"jit": "off"},
        )
    return _pool


async def close_pool():
    """Close the global pool — call during shutdown."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
