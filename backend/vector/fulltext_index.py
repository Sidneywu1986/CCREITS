"""
Fulltext Search - PostgreSQL fulltext fallback when Milvus is unavailable
"""
from ai_db.models import AnnouncementContent, SocialHotspot, Article


class FulltextSearch:
    """PostgreSQL fulltext fallback when Milvus is unavailable"""

    @staticmethod
    async def search_announcements(query: str, top_k: int = 5):
        results = await AnnouncementContent.filter(
            content_text__icontains=query
        ).limit(top_k).all()
        return results

    @staticmethod
    async def search_hotspots(query: str, top_k: int = 5):
        results = await SocialHotspot.filter(
            title__icontains=query
        ).limit(top_k).all()
        return results

    @staticmethod
    async def search_articles(query: str, top_k: int = 5):
        results = await Article.filter(
            title__icontains=query
        ).limit(top_k).all()
        return results