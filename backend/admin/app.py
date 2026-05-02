"""
Admin Application — refactored from monolithic admin_app.py
Multi-layer architecture: routes → services → models
"""
from fastapi import FastAPI
from contextlib import asynccontextmanager

from .utils import lifespan
from .routes import (
    auth, dashboard, funds, login, users, roles, permissions,
    announcements, crawlers, logs, alerts, integrity, other, health
)


@asynccontextmanager
async def lifespan_wrapper(app: FastAPI):
    # Start article sync scheduler (30 min interval)
    try:
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from scheduler.tasks import start_scheduler
        start_scheduler(interval_minutes=30)
    except Exception as e:
        import logging
        logging.getLogger("admin").warning(f"Scheduler start failed: {e}")

    async with lifespan(app):
        yield


app = FastAPI(lifespan=lifespan_wrapper, title="REITs Admin")

# ── Auth (split: HTML + API) ──
app.include_router(auth.router, prefix="", tags=["admin-auth"])
app.include_router(auth.api_router, prefix="/api/v1/auth", tags=["auth"])

# ── Login pages ──
app.include_router(login.router, prefix="", tags=["admin-login"])

# ── Dashboard ──
app.include_router(dashboard.router, prefix="/api/v1", tags=["dashboard"])

# ── Funds ──
app.include_router(funds.router, prefix="", tags=["funds"])

# ── Users / Roles / Permissions ──
app.include_router(users.router, prefix="", tags=["users"])
app.include_router(roles.router, prefix="", tags=["roles"])
app.include_router(permissions.router, prefix="", tags=["permissions"])

# ── Announcements ──
app.include_router(announcements.router, prefix="", tags=["announcements"])

# ── Crawlers / Logs / Alerts / Integrity ──
app.include_router(crawlers.router, prefix="", tags=["crawlers"])
app.include_router(logs.router, prefix="", tags=["logs"])
app.include_router(alerts.router, prefix="", tags=["alerts"])
app.include_router(integrity.router, prefix="", tags=["integrity"])

# ── Other / Utility ──
app.include_router(other.router, prefix="", tags=["other"])

# ── Health & Metrics ──
app.include_router(health.router, prefix="", tags=["health"])
