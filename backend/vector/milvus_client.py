#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Milvus Client - Vector Database Client
"""
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

# Singleton instance
_milvus_client_instance: Optional['MilvusClient'] = None


class MilvusClient:
    """Milvus vector database client"""

    def __init__(self, host: str = "localhost", port: int = 19530):
        self.host = host
        self.port = port
        self._connected = False
        self._client = None
        self._collection = None

    def connect(self) -> bool:
        """Connect to Milvus server"""
        try:
            from pymilvus import connections
            connections.connect(host=self.host, port=self.port, alias="default")
            self._connected = True
            logger.info(f"Connected to Milvus at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.warning(f"Failed to connect to Milvus: {e}")
            self._connected = False
            return False

    def disconnect(self):
        """Disconnect from Milvus server"""
        try:
            from pymilvus import connections
            if connections.has_connection("default"):
                connections.disconnect("default")
            self._connected = False
            self._client = None
            self._collection = None
            logger.info("Disconnected from Milvus")
        except Exception as e:
            logger.warning(f"Error disconnecting from Milvus: {e}")

    def is_healthy(self) -> bool:
        """Check Milvus health - returns True if healthy, False otherwise"""
        try:
            from pymilvus import connections
            if not connections.has_connection("default"):
                self.connect()
            if connections.has_connection("default"):
                # Try a simple operation
                from pymilvus import utility
                return utility.has_collection("_health_check")
            return False
        except Exception as e:
            logger.warning(f"Milvus health check failed: {e}")
            return False

    def create_collection_if_not_exists(self, collection_name: str, dimension: int = 1536) -> bool:
        """Create collection if not exists with specified dimension"""
        try:
            from pymilvus import connections, utility, Collection, CollectionSchema, FieldSchema, DataType

            if not connections.has_connection("default"):
                self.connect()

            # Define schema
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=2000),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dimension)
            ]
            schema = CollectionSchema(fields=fields, description=f"Collection {collection_name}")

            if not utility.has_collection(collection_name):
                collection = Collection(name=collection_name, schema=schema)
                # Create index
                index_params = {
                    "index_type": "IVF_FLAT",
                    "metric_type": "IP",
                    "params": {"nlist": 128}
                }
                collection.create_index(field_name="embedding", index_params=index_params)
                logger.info(f"Created collection: {collection_name}")
            else:
                collection = Collection(name=collection_name)
                logger.info(f"Collection already exists: {collection_name}")

            self._collection = collection
            return True
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            return False

    def insert(self, collection_name: str, data: List[dict]) -> List[int]:
        """Insert data into collection. Each dict should have 'content' and 'embedding' keys."""
        try:
            from pymilvus import Collection

            if not connections.has_connection("default"):
                self.connect()

            collection = Collection(name=collection_name)
            # Extract embeddings and contents
            embeddings = [d["embedding"] for d in data]
            contents = [d["content"] for d in data]
            # pymilvus expects rows: list of lists with [[id, content, embedding], ...] or auto-id [[content, embedding], ...]
            rows = [[content, embedding] for content, embedding in zip(contents, embeddings)]
            result = collection.insert(rows)
            collection.flush()
            logger.info(f"Inserted {len(data)} records into {collection_name}")
            return result.primary_keys
        except Exception as e:
            logger.error(f"Failed to insert: {e}")
            return []

    def search(self, collection_name: str, query_vector: List[float], top_k: int = 5) -> List[List]:
        """Search vectors using ANN search with IP metric. Accepts a single query_vector."""
        try:
            from pymilvus import Collection

            if not connections.has_connection("default"):
                self.connect()

            collection = Collection(name=collection_name)
            collection.load()

            search_params = {"metric_type": "IP", "params": {"nprobe": 10}}

            results = collection.search(
                data=[query_vector],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                output_fields=["id", "content"]
            )

            # Format results
            formatted = []
            for hits in results:
                formatted.append([
                    {"id": hit.id, "distance": hit.distance, "content": hit.entity.get("content", "")}
                    for hit in hits
                ])
            return formatted
        except Exception as e:
            logger.error(f"Failed to search: {e}")
            return []

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


def get_milvus_client() -> MilvusClient:
    """Get singleton MilvusClient instance"""
    global _milvus_client_instance
    if _milvus_client_instance is None:
        _milvus_client_instance = MilvusClient()
    return _milvus_client_instance
