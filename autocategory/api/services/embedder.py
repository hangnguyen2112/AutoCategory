"""
Embedding service – dùng HuggingFace Sentence Transformers (local)
Model: Alibaba-NLP/gte-multilingual-base (768 dimensions)
No API key required - runs locally
Runs on GPU (CUDA) if available, falls back to CPU automatically.
"""
from __future__ import annotations

import asyncio
import logging
import os
from threading import Lock

import torch
from sentence_transformers import SentenceTransformer
from config import settings
from services.result_cache import cache

logger = logging.getLogger(__name__)

_model: SentenceTransformer | None = None
_model_lock = Lock()


def model_name() -> str:
    return os.getenv("EMBEDDING_MODEL", "Alibaba-NLP/gte-multilingual-base")


def _get_device() -> str:
    """Auto-detect best available device: CUDA GPU > CPU."""
    if torch.cuda.is_available():
        device = "cuda"
        gpu_name = torch.cuda.get_device_name(0)
        vram_gb = torch.cuda.get_device_properties(0).total_memory / 1024 ** 3
        logger.info(f"GPU detected: {gpu_name} ({vram_gb:.1f} GB VRAM) — using CUDA")
    else:
        device = "cpu"
        logger.warning("No CUDA GPU detected — falling back to CPU")
    return device


def _get_model() -> SentenceTransformer:
    """Load model singleton (lazy initialization)."""
    global _model
    with _model_lock:
        if _model is None:
            name = model_name()
            device = _get_device()
            logger.info(f"Loading embedding model: {name} on {device}")
            _model = SentenceTransformer(name, trust_remote_code=True, device=device)
            logger.info(f"Model loaded successfully. Dimension: {_model.get_sentence_embedding_dimension()}")
    return _model


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed một list text, trả về list vector."""
    loop = asyncio.get_event_loop()

    def encode():
        model = _get_model()
        return model.encode(texts, convert_to_numpy=True)
    
    # Run encoding in thread pool to avoid blocking
    embeddings = await loop.run_in_executor(
        None, encode
    )
    
    # Convert numpy arrays to lists
    result = [emb.tolist() for emb in embeddings]
    
    if not result:
        raise ValueError(f"Model returned empty embeddings for {len(texts)} texts")
    
    return result


async def embed_single(text: str) -> list[float]:
    """Embed single text, return vector."""
    async def compute():
        vectors = await embed_texts([text])
        return vectors[0]
    return await cache.get_or_compute("embeddings", [model_name(), text],
                                      settings.cache_embedding_ttl, compute)
