"""NEXUS Embedding Service — Main Application."""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.kafka_handler import get_consumer
from app.vector_store import get_collection

settings = get_settings()

# ─── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("embedding-service")


# ─── Lifespan ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 {settings.service_name} v{settings.version} starting")
    logger.info(f"Model: {settings.model_name} (dim={settings.embedding_dim})")
    logger.info(f"ChromaDB: {settings.chroma_host}:{settings.chroma_port}")

    consumer = get_consumer()
    consumer.start()

    yield

    consumer.stop()
    logger.info(f"🛑 {settings.service_name} shutting down")


# ─── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="NEXUS Embedding Service",
    description="Code embedding generation and vector storage",
    version=settings.version,
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict:
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": settings.version,
        "model": settings.model_name,
    }


@app.get("/stats")
async def stats() -> dict:
    """Get embedding collection statistics."""
    try:
        collection = get_collection()
        count = collection.count()
        return {
            "collection": settings.chroma_collection,
            "total_embeddings": count,
            "model": settings.model_name,
            "embedding_dim": settings.embedding_dim,
        }
    except Exception as e:
        return {"error": str(e)}
