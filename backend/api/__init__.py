"""
AI API Routes
"""
from .chat_reits import router as chat_reits_router
from .chat_announcement import router as chat_announcement_router
from .research import router as research_router

__all__ = [
    "chat_reits_router",
    "chat_announcement_router",
    "research_router",
]