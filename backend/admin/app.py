"""
Admin Application — refactored from monolithic admin_app.py
Multi-layer architecture: routes → services → models
"""
from fastapi import FastAPI
from contextlib import asynccontextmanager

from .utils import lifespan
from .routes import (
    auth, dashboard, funds, login, users, roles, permissions,
    announcements, crawlers, logs, alerts, integrity, other
)


@asynccontextmanager
async def lifespan_wrapper(app: FastAPI):
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
