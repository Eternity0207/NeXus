"""ChromaDB client for storing and querying code embeddings."""

from __future__ import annotations

import logging
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import get_settings

logger = logging.getLogger("embedding-service")
settings = get_settings()

_client: Optional[chromadb.HttpClient] = None
_collection = None


def get_chroma_client() -> chromadb.HttpClient:
    """Get or create the ChromaDB HTTP client."""
    global _client
    if _client is None:
        try:
            _client = chromadb.HttpClient(
                host=settings.chroma_host,
                port=settings.chroma_port,
            )
            # Test connection
            _client.heartbeat()
            logger.info(f"Connected to ChromaDB at {settings.chroma_host}:{settings.chroma_port}")
        except Exception as e:
            logger.warning(f"ChromaDB unavailable ({e}), using ephemeral client")
            _client = chromadb.EphemeralClient()
    return _client


def get_collection():
    """Get or create the code embeddings collection."""
    global _collection
    if _collection is None:
        client = get_chroma_client()
        _collection = client.get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"description": "NEXUS code embeddings"},
        )
        logger.info(f"Using collection: {settings.chroma_collection}")
    return _collection


def store_embeddings(
    chunk_ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict],
) -> int:
    """Store embeddings in ChromaDB.

    Args:
        chunk_ids: Unique IDs for each chunk.
        embeddings: Vector embeddings.
        documents: Original text content.
        metadatas: Metadata dicts for each chunk.

    Returns:
        Number of embeddings stored.
    """
    if not chunk_ids:
        return 0

    collection = get_collection()

    try:
        # ChromaDB upsert handles both insert and update
        collection.upsert(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info(f"Stored {len(chunk_ids)} embeddings in ChromaDB")
        return len(chunk_ids)
    except Exception as e:
        logger.error(f"Failed to store embeddings: {e}")
        return 0


def query_similar(
    query_embedding: list[float],
    n_results: int = 10,
    where_filter: Optional[dict] = None,
) -> dict:
    """Query ChromaDB for similar code chunks.

    Args:
        query_embedding: Query vector.
        n_results: Number of results to return.
        where_filter: Optional metadata filter.

    Returns:
        ChromaDB query results dict.
    """
    collection = get_collection()

    kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
    }
    if where_filter:
        kwargs["where"] = where_filter

    return collection.query(**kwargs)
