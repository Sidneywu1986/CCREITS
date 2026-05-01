#!/usr/bin/env python3
"""
BGE-M3 语义编码器（纯 transformers，无 sentence-transformers 依赖）
支持多语言、长文本、1024维密集向量
"""

import os
import sys
import logging
import time
from typing import List, Optional
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel

logger = logging.getLogger("bge_embedder")

# 中国网络加速：默认使用 hf-mirror
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")


class BGEEmbedder:
    """BGE-M3 embedder: 1024-dim dense vectors"""

    MODEL_NAME = "BAAI/bge-m3"
    DIM = 1024

    def __init__(self, device: Optional[str] = None, cache_dir: Optional[str] = None):
        if device:
            self.device = device
        elif torch.cuda.is_available():
            self.device = "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            self.device = "mps"
        else:
            self.device = "cpu"
        self.cache_dir = cache_dir
        self._tokenizer = None
        self._model = None
        self.max_length = 8192
        self._load_model()

    def _resolve_model_path(self) -> str:
        """Resolve the actual model path, checking local caches first."""
        # 1. Check ModelScope cache (China-friendly mirror)
        modelscope_path = os.path.expanduser("~/.cache/modelscope/hub/BAAI/bge-m3")
        modelscope_weights = os.path.join(modelscope_path, "pytorch_model.bin")
        if os.path.exists(modelscope_weights):
            logger.info(f"Using ModelScope cached model at {modelscope_path}")
            return modelscope_path

        # 2. Check HuggingFace local cache
        try:
            from huggingface_hub import snapshot_download
            local_path = snapshot_download(
                repo_id=self.MODEL_NAME,
                cache_dir=self.cache_dir,
                local_files_only=True,
            )
            logger.info(f"Using HuggingFace cached model at {local_path}")
            return local_path
        except (ImportError, OSError, RuntimeError):
            pass

        # 3. Try online download via ModelScope first, then HF
        try:
            from modelscope import snapshot_download as ms_snapshot_download
            logger.info("Downloading model via ModelScope...")
            modelscope_path = ms_snapshot_download("BAAI/bge-m3", cache_dir=os.path.expanduser("~/.cache/modelscope/hub"))
            logger.info(f"Model downloaded to {modelscope_path}")
            return modelscope_path
        except (ImportError, OSError, RuntimeError) as e:
            logger.warning(f"ModelScope download failed: {e}")

        # 4. Fallback to HuggingFace online (with mirror)
        logger.info("Downloading model via HuggingFace...")
        return self.MODEL_NAME

    def _load_model(self):
        logger.info(f"Loading BGE-M3 on {self.device} (cache: {self.cache_dir or 'default'})...")
        t0 = time.time()
        
        model_path = self._resolve_model_path()
        
        kwargs = {"trust_remote_code": True}
        if self.cache_dir:
            kwargs["cache_dir"] = self.cache_dir

        self._tokenizer = AutoTokenizer.from_pretrained(model_path, **kwargs)
        self._model = AutoModel.from_pretrained(model_path, **kwargs).to(self.device)
        self._model.eval()
        elapsed = time.time() - t0
        logger.info(f"BGE-M3 loaded in {elapsed:.1f}s, dim={self.DIM}")

    @torch.no_grad()
    def encode(
        self,
        texts: List[str],
        batch_size: int = 8,
        show_progress: bool = False,
    ) -> np.ndarray:
        """
        Encode texts to 1024-dim normalized vectors.
        Returns: ndarray of shape (len(texts), 1024), dtype=float32
        """
        if not texts:
            return np.zeros((0, self.DIM), dtype=np.float32)

        all_embeddings = []
        total = len(texts)

        for i in range(0, total, batch_size):
            batch = texts[i : i + batch_size]

            inputs = self._tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=self.max_length,
                return_tensors="pt",
            ).to(self.device)

            outputs = self._model(**inputs)
            # [CLS] token embedding
            embeddings = outputs.last_hidden_state[:, 0]
            # L2 normalize for cosine similarity
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
            all_embeddings.append(embeddings.cpu().numpy())

            if show_progress and (i // batch_size) % 10 == 0:
                logger.info(f"Encoded {min(i + batch_size, total)}/{total}")

        return np.vstack(all_embeddings).astype(np.float32)

    def encode_query(self, query: str) -> np.ndarray:
        """查询编码（加指令前缀，提升检索质量）"""
        instruction = "为这个句子生成表示以用于检索相关文章："
        return self.encode([f"{instruction} {query}"], batch_size=1)[0]

    def encode_documents(self, docs: List[str], batch_size: int = 8) -> np.ndarray:
        """文档编码（不加前缀）"""
        return self.encode(docs, batch_size=batch_size)


# ---------- 全局单例 ----------
_embedder_instance: Optional[BGEEmbedder] = None


def get_embedder(device: Optional[str] = None) -> BGEEmbedder:
    global _embedder_instance
    if _embedder_instance is None:
        _embedder_instance = BGEEmbedder(device=device)
    return _embedder_instance


def clear_embedder():
    global _embedder_instance
    if _embedder_instance is not None:
        del _embedder_instance._model
        del _embedder_instance._tokenizer
        _embedder_instance = None
        import gc
        gc.collect()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    embedder = get_embedder()
    test_texts = [
        "数据中心REITs前景分析",
        "IDC基础设施投资机会",
        "产业园出租率持续下滑",
        "高速公路REITs分红方案",
    ]
    vecs = embedder.encode(test_texts, batch_size=2, show_progress=True)
    logger.info(f"Shape: {vecs.shape}, dtype: {vecs.dtype}")
    logger.info(f"Norms: {np.linalg.norm(vecs, axis=1)}")
    q = embedder.encode_query("数据中心REITs前景")
    sims = np.dot(vecs, q)
    logger.info(f"Query similarities: {sims}")
