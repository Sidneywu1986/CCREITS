#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Embedding Service - Multi-provider text embedding
Supports: baidu, qianfan, openai, deepseek, local (transformers)
"""
from typing import List, Optional
import logging
import os

logger = logging.getLogger(__name__)

# Singleton instance
_embedding_service_instance: Optional['EmbeddingService'] = None


class EmbeddingService:
    """Text embedding service with multi-provider support"""

    PROVIDERS = ["baidu", "qianfan", "openai", "deepseek", "local"]

    def __init__(self, provider: str, api_key: str = "", model: str = "embedding-v1",
                 dimension: int = 1536, base_url: Optional[str] = None):
        if provider not in self.PROVIDERS:
            raise ValueError(f"Provider must be one of {self.PROVIDERS}")

        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.dimension = dimension
        self.base_url = base_url
        self._client = None
        self._local_tokenizer = None
        self._local_model = None

    def _get_client(self):
        """Get or initialize the embedding client"""
        if self._client is None:
            if self.provider == "baidu":
                self._client = self._init_baidu_client()
            elif self.provider == "qianfan":
                self._client = self._init_qianfan_client()
            elif self.provider in ("openai", "deepseek"):
                self._client = self._init_openai_client()
            elif self.provider == "local":
                self._init_local_model()
        return self._client

    def _init_baidu_client(self):
        try:
            from baidu_aip import AipNlp
            return AipNlp(app_id=self.api_key.split(':')[0] if ':' in self.api_key else '',
                          api_key=self.api_key, secret_key='')
        except ImportError:
            logger.warning("baidu-aip not installed")
            return None

    def _init_qianfan_client(self):
        try:
            import qianfan
            return qianfan.Embedding(self.api_key)
        except ImportError:
            logger.warning("qianfan not installed")
            return None

    def _init_openai_client(self):
        try:
            import openai
            kwargs = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            return openai.OpenAI(**kwargs)
        except ImportError:
            logger.warning("openai not installed")
            return None
        except (ImportError, RuntimeError, ValueError) as e:
            logger.warning(f"OpenAI client init failed: {e}")
            return None

    def _init_local_model(self):
        """Load local transformers model for embedding"""
        try:
            from transformers import AutoTokenizer, AutoModel
            import torch
            logger.info(f"Loading local model: {self.model}...")
            self._local_tokenizer = AutoTokenizer.from_pretrained(self.model)
            self._local_model = AutoModel.from_pretrained(self.model)
            # Move to CPU (no GPU assumed)
            self._local_model.eval()
            # Infer dimension from model config
            if hasattr(self._local_model.config, 'hidden_size'):
                self.dimension = self._local_model.config.hidden_size
            logger.info(f"Local model loaded, dim={self.dimension}")
        except (ImportError, RuntimeError, OSError, ValueError) as e:
            logger.error(f"Failed to load local model: {e}")
            raise

    def embed_text(self, text: str) -> List[float]:
        try:
            self._get_client()
            if self.provider == "baidu":
                return self._embed_baidu(text)
            elif self.provider == "qianfan":
                return self._embed_qianfan(text)
            elif self.provider in ("openai", "deepseek"):
                return self._embed_openai(text)
            elif self.provider == "local":
                return self._embed_local(text)
        except (RuntimeError, ValueError, TypeError) as e:
            logger.error(f"Embedding failed for provider {self.provider}: {e}")
            raise

    def _mock_embedding(self) -> List[float]:
        return [0.01 * i for i in range(self.dimension)]

    def _embed_baidu(self, text: str) -> List[float]:
        if self._client is None:
            return self._mock_embedding()
        result = self._client.embedding(text)
        if result.get('error_msg'):
            raise Exception(result['error_msg'])
        return result['data'][0]['embedding']

    def _embed_qianfan(self, text: str) -> List[float]:
        if self._client is None:
            return self._mock_embedding()
        resp = self._client.do(model=self.model, input=text)
        return resp['data'][0]['embedding']

    def _embed_openai(self, text: str) -> List[float]:
        if self._client is None:
            return self._mock_embedding()
        resp = self._client.embeddings.create(
            model=self.model,
            input=text[:8000]
        )
        return resp.data[0].embedding

    def _embed_local(self, text: str) -> List[float]:
        """Local transformers embedding (mean pooling)"""
        import torch
        import torch.nn.functional as F

        # Tokenize
        inputs = self._local_tokenizer(
            text, return_tensors="pt",
            truncation=True, max_length=512, padding=True
        )

        # Forward
        with torch.no_grad():
            outputs = self._local_model(**inputs)

        # Mean pooling
        attention_mask = inputs['attention_mask']
        token_embeddings = outputs.last_hidden_state
        input_mask_expanded = attention_mask.unsqueeze(-1).float()
        sum_embeddings = (token_embeddings * input_mask_expanded).sum(dim=1)
        embeddings = sum_embeddings / input_mask_expanded.sum(dim=1).clamp(min=1e-9)

        # Normalize
        embeddings = F.normalize(embeddings, p=2, dim=1)
        return embeddings[0].tolist()

    def batch_embed(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(text) for text in texts]

    def __enter__(self):
        self._get_client()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._client = None


def get_embedding_service() -> Optional[EmbeddingService]:
    """Get singleton EmbeddingService instance"""
    global _embedding_service_instance
    if _embedding_service_instance is None:
        provider = os.environ.get("EMBEDDING_PROVIDER", "local")
        api_key = os.environ.get("EMBEDDING_API_KEY", "")
        model = os.environ.get("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
        dimension = int(os.environ.get("EMBEDDING_DIMENSION", "512"))
        base_url = os.environ.get("EMBEDDING_BASE_URL", "")

        if provider in ("openai", "deepseek") and not api_key:
            logger.warning("EMBEDDING_API_KEY not set, using local provider")
            provider = "local"

        _embedding_service_instance = EmbeddingService(
            provider, api_key, model, dimension,
            base_url=base_url if base_url else None
        )
    return _embedding_service_instance
