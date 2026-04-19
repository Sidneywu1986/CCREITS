#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Embedding Service - Multi-provider text embedding
Supports: baidu, qianfan, openai
"""
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

# Singleton instance
_embedding_service_instance: Optional['EmbeddingService'] = None


class EmbeddingService:
    """Text embedding service with multi-provider support"""

    PROVIDERS = ["baidu", "qianfan", "openai"]

    def __init__(self, provider: str, api_key: str, model: str = "embedding-v1", dimension: int = 1536):
        if provider not in self.PROVIDERS:
            raise ValueError(f"Provider must be one of {self.PROVIDERS}")

        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.dimension = dimension
        self._client = None

    def _get_client(self):
        """Get or initialize the embedding client"""
        if self._client is None:
            if self.provider == "baidu":
                self._client = self._init_baidu_client()
            elif self.provider == "qianfan":
                self._client = self._init_qianfan_client()
            elif self.provider == "openai":
                self._client = self._init_openai_client()
        return self._client

    def _init_baidu_client(self):
        """Initialize Baidu AI client"""
        try:
            from baidu_aip import AipNlp
            return AipNlp(app_id=self.api_key.split(':')[0] if ':' in self.api_key else '',
                          api_key=self.api_key,
                          secret_key='')
        except ImportError:
            logger.warning("baidu-aip not installed, using mock client")
            return None

    def _init_qianfan_client(self):
        """Initialize Qianfan client"""
        try:
            import qianfan
            return qianfan.Embedding(self.api_key)
        except ImportError:
            logger.warning("qianfan not installed, using mock client")
            return None

    def _init_openai_client(self):
        """Initialize OpenAI client"""
        try:
            import openai
            return openai
        except ImportError:
            logger.warning("openai not installed, using mock client")
            return None

    def embed_text(self, text: str) -> List[float]:
        """Embed a single text into vector"""
        try:
            if self.provider == "baidu":
                return self._embed_baidu(text)
            elif self.provider == "qianfan":
                return self._embed_qianfan(text)
            elif self.provider == "openai":
                return self._embed_openai(text)
        except Exception as e:
            logger.error(f"Embedding failed for provider {self.provider}: {e}")
            raise

    def _mock_embedding(self) -> List[float]:
        return [0.01 * i for i in range(self.dimension)]

    def _embed_baidu(self, text: str) -> List[float]:
        """Baidu embedding"""
        if self._client is None:
            return self._mock_embedding()

        try:
            result = self._client.embedding(text)
            if result.get('error_msg'):
                raise Exception(result['error_msg'])
            return result['data'][0]['embedding']
        except Exception as e:
            logger.error(f"Baidu embedding error: {e}")
            raise

    def _embed_qianfan(self, text: str) -> List[float]:
        """Qianfan embedding"""
        if self._client is None:
            return self._mock_embedding()

        try:
            resp = self._client.do(model=self.model, input=text)
            return resp['data'][0]['embedding']
        except Exception as e:
            logger.error(f"Qianfan embedding error: {e}")
            raise

    def _embed_openai(self, text: str) -> List[float]:
        """OpenAI embedding"""
        if self._client is None:
            return self._mock_embedding()

        try:
            resp = self._client.Embedding.create(
                model=self.model,
                input=text,
                api_key=self.api_key
            )
            return resp['data'][0]['embedding']
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            raise

    def batch_embed(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts"""
        return [self.embed_text(text) for text in texts]

    def __enter__(self):
        self._get_client()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._client = None


def get_embedding_service() -> EmbeddingService:
    """Get singleton EmbeddingService instance"""
    global _embedding_service_instance
    if _embedding_service_instance is None:
        # Default provider - can be configured via environment
        import os
        provider = os.environ.get("EMBEDDING_PROVIDER", "baidu")
        api_key = os.environ.get("EMBEDDING_API_KEY", "test")
        model = os.environ.get("EMBEDDING_MODEL", "embedding-v1")
        dimension = int(os.environ.get("EMBEDDING_DIMENSION", "1536"))
        _embedding_service_instance = EmbeddingService(provider, api_key, model, dimension)
    return _embedding_service_instance
