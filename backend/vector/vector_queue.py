"""
Vector Queue Processor - Async vectorization worker
"""
import asyncio
import logging
from typing import List

logger = logging.getLogger(__name__)


class VectorQueueProcessor:
    """Async vectorization queue processor with retry logic"""

    def __init__(self, batch_size: int = 10, max_retries: int = 3):
        self.batch_size = batch_size
        self.max_retries = max_retries

    async def process_pending(self) -> int:
        """Process pending vectorization records. Returns count of processed records."""
        from backend.ai_db.models import VectorPending
        from backend.vector.milvus_client import get_milvus_client
        from backend.vector.embedding_service import get_embedding_service

        # Fetch pending records
        pending_records = await VectorPending.filter(status="pending").limit(self.batch_size).all()
        processed_count = 0

        for record in pending_records:
            try:
                # Mark as processing
                record.status = "processing"
                await record.save()

                # Vectorize based on content type
                if record.content_type == "announcement":
                    await self._vectorize_announcement(record)
                elif record.content_type == "hotspot":
                    await self._vectorize_hotspot(record)
                elif record.content_type == "article":
                    await self._vectorize_article(record)

                # Mark as done
                record.status = "done"
                record.processed_at = asyncio.get_event_loop().time()
                await record.save()
                processed_count += 1

            except Exception as e:
                logger.error(f"Vectorization failed for {record.content_type}:{record.content_id}: {e}")
                record.retry_count += 1
                record.error_message = str(e)[:500]
                if record.retry_count >= self.max_retries:
                    record.status = "failed"
                else:
                    record.status = "pending"
                await record.save()

        return processed_count

    async def _vectorize_announcement(self, record) -> None:
        """Vectorize announcement content"""
        from backend.ai_db.models import AnnouncementContent
        from backend.vector.milvus_client import get_milvus_client
        from backend.vector.embedding_service import get_embedding_service

        contents = await AnnouncementContent.filter(announcement_id=int(record.content_id)).all()
        if not contents:
            return

        milvus = get_milvus_client()
        embed_service = get_embedding_service()

        if milvus.connect():
            milvus.create_collection_if_not_exists("announcement_contents", dim=1536)

            for content in contents:
                embedding = embed_service.embed_text(content.content_text or "")
                milvus.insert("announcement_contents", [{
                    "content": content.content_text or "",
                    "embedding": embedding
                }])

    async def _vectorize_hotspot(self, record) -> None:
        """Vectorize social hotspot"""
        from backend.ai_db.models import SocialHotspot
        from backend.vector.milvus_client import get_milvus_client
        from backend.vector.embedding_service import get_embedding_service

        hotspot = await SocialHotspot.filter(id=int(record.content_id)).first()
        if not hotspot:
            return

        milvus = get_milvus_client()
        embed_service = get_embedding_service()

        if milvus.connect():
            milvus.create_collection_if_not_exists("social_hotspots", dim=1536)

            text = f"{hotspot.title or ''}\n{hotspot.content or ''}"
            embedding = embed_service.embed_text(text)
            milvus.insert("social_hotspots", [{
                "content": text,
                "embedding": embedding
            }])

    async def _vectorize_article(self, record) -> None:
        """Vectorize article content"""
        from backend.ai_db.models import Article
        from backend.vector.milvus_client import get_milvus_client
        from backend.vector.embedding_service import get_embedding_service

        article = await Article.filter(id=int(record.content_id)).first()
        if not article:
            return

        milvus = get_milvus_client()
        embed_service = get_embedding_service()

        if milvus.connect():
            milvus.create_collection_if_not_exists("articles", dim=1536)

            text = f"{article.title or ''}\n{article.content or ''}"
            embedding = embed_service.embed_text(text)
            milvus.insert("articles", [{
                "content": text,
                "embedding": embedding
            }])


async def run_vector_queue_worker(interval_seconds: int = 5):
    """Background worker that processes the vector queue"""
    processor = VectorQueueProcessor()

    while True:
        try:
            processed = await processor.process_pending()
            if processed > 0:
                logger.info(f"Vector queue processed {processed} records")
        except Exception as e:
            logger.error(f"Vector queue worker error: {e}")

        await asyncio.sleep(interval_seconds)
