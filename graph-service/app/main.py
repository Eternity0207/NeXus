"""NEXUS Graph Service — Main Application.

Consumes file.parsed events to build Neo4j dependency graphs.
Exposes REST APIs for graph queries.
"""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, status

from app.config import get_settings
from app.neo4j_client import init_schema, close_driver
from app.kafka_handler import get_consumer
from app.queries import get_repo_graph, get_node_details, get_file_dependencies, get_repo_stats

settings = get_settings()

# ─── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("graph-service")


# ─── Lifespan ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 {settings.service_name} v{settings.version} starting")

    # Initialize Neo4j schema
    try:
        init_schema()
    except Exception as e:
        logger.warning(f"Neo4j schema init failed (may not be running): {e}")

    # Start Kafka consumer
    consumer = get_consumer()
    consumer.start()

    yield

    consumer.stop()
    close_driver()
    logger.info(f"🛑 {settings.service_name} shutting down")


# ─── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="NEXUS Graph Service",
    description="Dependency graph construction and query API",
    version=settings.version,
    lifespan=lifespan,
)


# ─── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> dict:
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": settings.version,
    }


@app.get(
    "/graph/{repo_id}",
    summary="Get repository dependency graph",
    tags=["graph"],
)
async def get_graph(
    repo_id: str,
    depth: int = Query(default=2, ge=1, le=10),
    node_type: str = Query(default="all"),
) -> dict:
    """Retrieve the dependency graph for a repository."""
    try:
        return get_repo_graph(repo_id, depth, node_type)
    except Exception as e:
        logger.error(f"Graph query failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Graph query failed: {str(e)}",
        )


@app.get(
    "/graph/{repo_id}/node/{node_id}",
    summary="Get node details with neighbors",
    tags=["graph"],
)
async def get_node(repo_id: str, node_id: str) -> dict:
    """Get details for a specific graph node."""
    result = get_node_details(repo_id, node_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Node not found",
        )
    return result


@app.get(
    "/graph/{repo_id}/file-deps",
    summary="Get file-level dependencies",
    tags=["graph"],
)
async def file_deps(
    repo_id: str,
    file_path: str = Query(..., description="File path to analyze"),
) -> dict:
    """Get imports and importers for a specific file."""
    return get_file_dependencies(repo_id, file_path)


@app.get(
    "/graph/{repo_id}/stats",
    summary="Get graph statistics",
    tags=["graph"],
)
async def graph_stats(repo_id: str) -> dict:
    """Get aggregate node/edge counts for a repository."""
    return get_repo_stats(repo_id)
