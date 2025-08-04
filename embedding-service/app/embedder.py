"""Embedding model wrapper using sentence-transformers."""

from __future__ import annotations

import logging
from typing import Optional

from app.config import get_settings

logger = logging.getLogger("embedding-service")
settings = get_settings()

# Lazy-loaded model instance
_model = None


def _load_model():
    """Lazy-load the sentence-transformers model."""
    global _model
    if _model is None:
        logger.info(f"Loading embedding model: {settings.model_name}")
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(settings.model_name)
            logger.info(f"Model loaded: {settings.model_name} (dim={settings.embedding_dim})")
        except ImportError:
            logger.warning(
                "sentence-transformers not installed, using fallback hash embeddings"
            )
            _model = "fallback"
    return _model


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate vector embeddings for a batch of text strings.

    Args:
        texts: List of code/text strings to embed.

    Returns:
        List of embedding vectors (list of floats).
    """
    if not texts:
        return []

    model = _load_model()

    if model == "fallback":
        return _fallback_embeddings(texts)

    try:
        embeddings = model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return embeddings.tolist()
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        return _fallback_embeddings(texts)


def generate_single_embedding(text: str) -> list[float]:
    """Generate embedding for a single text string."""
    results = generate_embeddings([text])
    return results[0] if results else []


def _fallback_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate deterministic hash-based embeddings as a fallback.

    Not semantically meaningful, but keeps the pipeline running
    when sentence-transformers is unavailable.
    """
    import hashlib

    embeddings = []
    for text in texts:
        hash_bytes = hashlib.sha256(text.encode()).digest()
        # Convert to float vector of the expected dimension
        vector = []
        for i in range(settings.embedding_dim):
            byte_val = hash_bytes[i % len(hash_bytes)]
            vector.append((byte_val / 255.0) * 2 - 1)  # Normalize to [-1, 1]
        embeddings.append(vector)

    return embeddings
