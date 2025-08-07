"""NEXUS Search Service — Main Application."""

import logging
import sys
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Query as QueryParam
from pydantic import BaseModel, Field

from app.config import get_settings
from app.search_engine import semantic_search

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("search-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 {settings.service_name} v{settings.version} starting")
    logger.info(f"ChromaDB: {settings.chroma_host}:{settings.chroma_port}")
    yield
    logger.info(f"🛑 {settings.service_name} shutting down")


app = FastAPI(
    title="NEXUS Search Service",
    description="Semantic code search powered by vector similarity",
    version=settings.version,
    lifespan=lifespan,
)


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    repo_id: Optional[str] = None
    top_k: int = Field(default=10, ge=1, le=50)
    file_type: Optional[str] = None


@app.get("/health")
async def health() -> dict:
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": settings.version,
    }


@app.post("/search", summary="Semantic code search", tags=["search"])
async def search(request: SearchRequest) -> dict:
    """Search code using natural language. Returns ranked results by similarity."""
    return semantic_search(
        query=request.query,
        repo_id=request.repo_id,
        top_k=request.top_k,
        file_type=request.file_type,
    )


@app.get("/search", summary="Semantic search via GET", tags=["search"])
async def search_get(
    q: str = QueryParam(..., min_length=1, description="Search query"),
    repo_id: Optional[str] = None,
    top_k: int = QueryParam(default=10, ge=1, le=50),
) -> dict:
    """GET endpoint for browser-friendly search."""
    return semantic_search(query=q, repo_id=repo_id, top_k=top_k)
