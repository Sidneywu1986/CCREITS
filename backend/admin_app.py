"""
兼容层 — 旧入口 admin_app.py
所有路由已迁移至 backend/admin/routes/
新架构入口: backend/admin/app.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 从新架构导入 FastAPI app（含 lifespan + 全部路由）
from admin.app import app

# 导出原有 lifespan 依赖（兼容旧代码）
from admin.utils import lifespan, DB_URL, DB_DSN
from admin.utils import sign_cookie, verify_cookie, get_admin_user
