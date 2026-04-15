"""
核心配置
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings:
    """应用配置"""
    
    # 应用
    APP_NAME = "REITs数据平台"
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    VERSION = "2.0.0"
    
    # 服务器
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 5074))
    
    # 数据库
    DATABASE_URL = os.getenv(
        "DATABASE_URL", 
        f"sqlite:///{BASE_DIR}/database/reits.db"
    )
    
    # JWT
    JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRE_MINUTES = 60 * 24  # 24小时
    
    # CORS
    ALLOWED_HOSTS = [
        "http://localhost:5173",   # Vite前端开发
        "http://localhost:5174",   # 前端实际端口
        "http://localhost:3000",
        "http://localhost:4000",
        "http://localhost:8080",
    ]
    
    # 管理员默认账号
    DEFAULT_ADMIN_USERNAME = "admin"
    DEFAULT_ADMIN_PASSWORD = "admin123"  # 生产环境必须修改
    
    # 爬虫
    CRAWLER_ENABLED = os.getenv("CRAWLER_ENABLED", "true").lower() == "true"


settings = Settings()
