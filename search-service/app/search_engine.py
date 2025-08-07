"""Semantic search engine using ChromaDB vector similarity."""

from __future__ import annotations

import logging
from typing import Optional

import chromadb

from app.config import get_settings

logger = logging.getLogger("search-service")
settings = get_settings()

_client: Optional[chromadb.HttpClient] = None
_collection = None
_model = None


def _get_client():
    global _client
    if _client is None:
        try:
            _client = chromadb.HttpClient(
                host=settings.chroma_host,
                port=settings.chroma_port,
            )
            _client.heartbeat()
            logger.info(f"Connected to ChromaDB at {settings.chroma_host}:{settings.chroma_port}")
        except Exception as e:
            logger.warning(f"ChromaDB unavailable ({e}), using ephemeral")
            _client = chromadb.EphemeralClient()
    return _client


def _get_collection():
    global _collection
    if _collection is None:
        client = _get_client()
        _collection = client.get_or_create_collection(
            name=settings.chroma_collection,
        )
    return _collection


def _get_model():
    """Lazy-load embedding model for query encoding."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(settings.model_name)
            logger.info(f"Loaded query model: {settings.model_name}")
        except ImportError:
            logger.warning("sentence-transformers not available, using fallback")
            _model = "fallback"
    return _model


def _encode_query(query: str) -> list[float]:
    """Encode a search query into a vector."""
    model = _get_model()

    if model == "fallback":
        import hashlib
        hash_bytes = hashlib.sha256(query.encode()).digest()
        return [(hash_bytes[i % len(hash_bytes)] / 255.0) * 2 - 1
                for i in range(settings.embedding_dim)]

    embedding = model.encode(query, normalize_embeddings=True)
    return embedding.tolist()


def semantic_search(
    query: str,
    repo_id: Optional[str] = None,
    top_k: int = 10,
    file_type: Optional[str] = None,
) -> dict:
    """Search code using natural language queries.

    Args:
        query: Natural language search query.
        repo_id: Optional filter by repository.
        top_k: Number of results to return.
        file_type: Optional filter by chunk type (function, class, file_summary).

    Returns:
        Search results with scores and metadata.
    """
    collection = _get_collection()
    query_vector = _encode_query(query)

    # Build metadata filter
    where_filter = None
    conditions = []

    if repo_id:
        conditions.append({"repo_id": {"$eq": repo_id}})
    if file_type:
        conditions.append({"type": {"$eq": file_type}})

    if len(conditions) == 1:
        where_filter = conditions[0]
    elif len(conditions) > 1:
        where_filter = {"$and": conditions}

    # Query ChromaDB
    try:
        kwargs = {
            "query_embeddings": [query_vector],
            "n_results": min(top_k, 50),
        }
        if where_filter:
            kwargs["where"] = where_filter

        results = collection.query(**kwargs)
    except Exception as e:
        logger.error(f"ChromaDB query failed: {e}")
        return {"query": query, "results": [], "total": 0}

    # Format results
    formatted = []
    if results and results.get("documents"):
        documents = results["documents"][0]
        metadatas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(documents)
        distances = results["distances"][0] if results.get("distances") else [0.0] * len(documents)

        for doc, meta, dist in zip(documents, metadatas, distances):
            # ChromaDB returns L2 distance — convert to similarity score
            score = max(0.0, 1.0 - (dist / 2.0))

            formatted.append({
                "file_path": meta.get("file_path", "unknown"),
                "content": doc,
                "score": round(score, 4),
                "metadata": {
                    "type": meta.get("type", ""),
                    "name": meta.get("name", ""),
                    "language": meta.get("language", ""),
                    "start_line": meta.get("start_line", 0),
                    "end_line": meta.get("end_line", 0),
                },
            })

    return {
        "query": query,
        "results": formatted,
        "total": len(formatted),
    }
