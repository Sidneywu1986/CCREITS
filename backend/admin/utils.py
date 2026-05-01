"""
Admin utilities — shared across routes and services
"""

import os
import sys
import re
import hmac
import hashlib
from typing import Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from fastapi import Request
from core.config import settings

# ── Database ──
DB_TYPE = getattr(settings, 'DB_TYPE', 'postgres')
pg = settings.PG_CONFIG
DB_URL = f"postgres://{pg['user']}:{pg['password']}@{pg['host']}:{pg['port']}/{pg['database']}"

TORTOISE_ORM = {
    "connections": {"default": DB_URL},
    "apps": {
        "models": {
            "models": ["admin_models"],
            "default_connection": "default",
        },
    },
}

# ── SQL helpers ──
def sql_placeholders(sql: str) -> str:
    """SQLite ? → PostgreSQL $1,$2..."""
    cnt = [0]
    def repl(m):
        cnt[0] += 1
        return f'${cnt[0]}'
    return re.sub(r'\?', repl, sql)

# ── Cookie security ──
def sign_cookie(value: str) -> str:
    secret = getattr(settings, 'JWT_SECRET', '')
    if not secret:
        return value
    sig = hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{value}:{sig}"

def verify_cookie(signed_value: str) -> Optional[str]:
    if not signed_value or ":" not in signed_value:
        return None
    value, sig = signed_value.rsplit(":", 1)
    secret = getattr(settings, 'JWT_SECRET', '')
    if not secret:
        return None
    expected = hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()[:16]
    if hmac.compare_digest(sig, expected):
        return value
    return None

def get_admin_user(request: Request) -> Optional[str]:
    signed = request.cookies.get("admin_user")
    return verify_cookie(signed)

# ── Logging ──
import logging
logger = logging.getLogger(__name__)

# ── Templates ──
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

_templates = None
def get_templates():
    global _templates
    if _templates is None:
        from fastapi.templating import Jinja2Templates
        _templates = Jinja2Templates(directory=TEMPLATES_DIR)
    return _templates

# ── Lifespan (Tortoise ORM init) ──
from contextlib import asynccontextmanager
from fastapi import FastAPI

DB_PATH = os.path.join(BASE_DIR, "data", "admin.db")

@asynccontextmanager
async def lifespan(app: FastAPI):
    from tortoise import Tortoise
    from passlib.hash import bcrypt

    if DB_TYPE == 'sqlite':
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    await Tortoise.init(
        db_url=DB_URL,
        modules={"models": ["admin_models"]},
        _enable_global_fallback=True
    )

    await Tortoise.generate_schemas(safe=True)

    from admin_models import UserAdmin
    count = await UserAdmin.filter(username="admin").count()
    if count == 0:
        await UserAdmin.create(
            username="admin",
            email="admin@example.com",
            password_hash=bcrypt.hash("admin123"),
            is_active=True,
            is_superuser=True,
        )
        logger.info("默认管理员: admin / admin123")
    else:
        logger.info(f"管理员账号已存在: {count} 个")

    logger.info(f"数据库已初始化: {DB_URL.replace(pg.get('password', ''), '***')}")

    yield

    await Tortoise.close_connections()
