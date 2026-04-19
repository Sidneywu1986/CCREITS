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

    # AI PostgreSQL数据库
    AI_DB_CONFIG = {
        "connections": {
            "default": {
                "engine": "tortoise.backends.asyncpg",
                "credentials": {
                    "host": os.getenv("AI_DB_HOST", "localhost"),
                    "port": int(os.getenv("AI_DB_PORT", 5432)),
                    "user": os.getenv("AI_DB_USER", "postgres"),
                    "password": os.getenv("AI_DB_PASSWORD", "postgres"),
                    "database": os.getenv("AI_DB_NAME", "ai_db"),
                }
            }
        },
        "apps": {
            "ai_db": {
                "models": ["ai_db.models", "aerich.models"],
                "default_connection": "default",
            }
        }
    }

    # Milvus向量数据库配置
    MILVUS_CONFIG = {
        "host": os.getenv("MILVUS_HOST", "localhost"),
        "port": int(os.getenv("MILVUS_PORT", 19530)),
        "user": os.getenv("MILVUS_USER", ""),
        "password": os.getenv("MILVUS_PASSWORD", ""),
    }

    # Embedding配置（国产API）
    EMBEDDING_CONFIG = {
        "provider": os.getenv("EMBEDDING_PROVIDER", "zhipu"),
        "api_key": os.getenv("EMBEDDING_API_KEY", ""),
        "model": os.getenv("EMBEDDING_MODEL", "embedding-3"),
        "batch_size": int(os.getenv("EMBEDDING_BATCH_SIZE", 100)),
    }

    # LLM配置（分层模型）
    LLM_CONFIG = {
        "deepseek": {
            "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
            "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        },
        "gpt_4o_mini": {
            "api_key": os.getenv("OPENAI_API_KEY", ""),
            "model": "gpt-4o-mini",
            "base_url": "https://api.openai.com/v1",
        },
        "gpt_4o": {
            "api_key": os.getenv("OPENAI_API_KEY", ""),
            "model": "gpt-4o",
            "base_url": "https://api.openai.com/v1",
        },
    }

    # 爬虫调度器配置
    CRAWLER_SCHEDULER_CONFIG = {
        "enabled": os.getenv("CRAWLER_SCHEDULER_ENABLED", "true").lower() == "true",
        "interval": int(os.getenv("CRAWLER_SCHEDULER_INTERVAL", 3600)),
    }


settings = Settings()
