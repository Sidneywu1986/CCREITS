#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Milvus Client - Vector Database Client
Supports: Milvus Server (Docker) and Milvus Lite (local file)
"""
from typing import List, Optional, Dict, Any
import logging
import os

logger = logging.getLogger(__name__)

# Singleton instance
_milvus_client_instance: Optional['MilvusClient'] = None


class MilvusClient:
    """Milvus vector database client (Lite + Server dual mode)"""

    def __init__(self, uri: str = "./milvus_reits.db", collection: str = "reit_wechat_articles"):
        self.uri = uri
        self.collection_name = collection
        self._client = None
        self._dim = int(os.environ.get("EMBEDDING_DIMENSION", "1024"))

    def connect(self) -> bool:
        """Connect to Milvus (Lite or Server)"""
        try:
            from pymilvus import MilvusClient as PyMilvusClient
            self._client = PyMilvusClient(self.uri)
            logger.info(f"Connected to Milvus at {self.uri}")
            return True
        except (RuntimeError, ConnectionError, ValueError) as e:
            logger.warning(f"Failed to connect to Milvus: {e}")
            return False

    def disconnect(self):
        """Disconnect"""
        self._client = None

    def is_healthy(self) -> bool:
        """Check if connected"""
        return self._client is not None

    def ensure_collection(self, dim: Optional[int] = None):
        """Create collection if not exists"""
        if dim:
            self._dim = dim

        if not self._client:
            raise RuntimeError("Milvus not connected")

        if self._client.has_collection(self.collection_name):
            logger.info(f"Collection {self.collection_name} exists")
            return

        from pymilvus import DataType

        schema = self._client.create_schema(
            auto_id=True,
            enable_dynamic_field=False,
        )
        schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
        schema.add_field(field_name="article_id", datatype=DataType.INT64)
        schema.add_field(field_name="source", datatype=DataType.VARCHAR, max_length=200)
        schema.add_field(field_name="title", datatype=DataType.VARCHAR, max_length=500)
        schema.add_field(field_name="publish_date", datatype=DataType.VARCHAR, max_length=20)
        schema.add_field(field_name="chunk_index", datatype=DataType.INT64)
        schema.add_field(field_name="chunk_text", datatype=DataType.VARCHAR, max_length=4000)
        schema.add_field(field_name="embedding", datatype=DataType.FLOAT_VECTOR, dim=self._dim)

        index_params = self._client.prepare_index_params()
        index_params.add_index(
            field_name="embedding",
            index_type="IVF_FLAT",
            metric_type="COSINE",
            params={"nlist": 128}
        )

        self._client.create_collection(
            collection_name=self.collection_name,
            schema=schema,
            index_params=index_params
        )
        logger.info(f"Collection {self.collection_name} created, dim={self._dim}")

    def insert(self, data: List[Dict[str, Any]]) -> bool:
        """Insert vectors"""
        if not self._client:
            return False
        try:
            self._client.insert(collection_name=self.collection_name, data=data)
            return True
        except (RuntimeError, ConnectionError, ValueError) as e:
            logger.error(f"Insert error: {e}")
            return False

    def search(self, vector: List[float], top_k: int = 5, filter_expr: str = "") -> List[Dict]:
        """Search similar vectors"""
        if not self._client:
            return []
        try:
            res = self._client.search(
                collection_name=self.collection_name,
                data=[vector],
                limit=top_k,
                output_fields=["article_id", "source", "title", "chunk_text", "publish_date"],
                filter=filter_expr
            )
            results = []
            for hits in res:
                for hit in hits:
                    results.append({
                        "id": hit.get("id"),
                        "article_id": hit["entity"].get("article_id"),
                        "source": hit["entity"].get("source"),
                        "title": hit["entity"].get("title"),
                        "chunk_text": hit["entity"].get("chunk_text"),
                        "publish_date": hit["entity"].get("publish_date"),
                        "distance": hit.get("distance", 0),
                    })
            return results
        except (RuntimeError, ConnectionError, ValueError) as e:
            logger.error(f"Search error: {e}")
            return []

    def delete_by_article_ids(self, article_ids: List[int]) -> bool:
        """Delete vectors by article_id"""
        if not self._client:
            return False
        try:
            ids_str = ",".join(str(i) for i in article_ids)
            self._client.delete(
                collection_name=self.collection_name,
                filter=f"article_id in [{ids_str}]"
            )
            return True
        except (RuntimeError, ConnectionError, ValueError) as e:
            logger.error(f"Delete error: {e}")
            return False


def get_milvus_client() -> Optional[MilvusClient]:
    """Get singleton MilvusClient instance"""
    global _milvus_client_instance
    if _milvus_client_instance is None:
        # Load .env if not already loaded
        from dotenv import load_dotenv
        load_dotenv()
        uri = os.environ.get("MILVUS_URI", "./milvus_reits.db")
        collection = os.environ.get("MILVUS_COLLECTION", "reit_wechat_articles")
        _milvus_client_instance = MilvusClient(uri, collection)
    return _milvus_client_instance
