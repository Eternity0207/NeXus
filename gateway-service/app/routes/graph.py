"""Dependency graph query endpoints."""

import logging

import httpx
from fastapi import APIRouter, HTTPException, Query, status

from app.config import get_settings

logger = logging.getLogger("gateway-service")
router = APIRouter(prefix="/api/v1/graph", tags=["graph"])
settings = get_settings()


@router.get(
    "/{repo_id}",
    summary="Get dependency graph",
    description="Retrieve the dependency graph for a repository.",
)
async def get_graph(
    repo_id: str,
    depth: int = Query(default=2, ge=1, le=10, description="Graph traversal depth"),
    node_type: str = Query(default="all", description="Filter by node type: file, function, class, all"),
) -> dict:
    """Fetch dependency graph from graph service."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{settings.graph_service_url}/graph/{repo_id}",
                params={"depth": depth, "node_type": node_type},
            )
            response.raise_for_status()
            return response.json()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Graph service unavailable",
        )
    except httpx.HTTPStatusError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Graph not found for repo {repo_id}",
        )


@router.get(
    "/{repo_id}/node/{node_id}",
    summary="Get node details",
    description="Get details and neighbors for a specific graph node.",
)
async def get_node(repo_id: str, node_id: str) -> dict:
    """Fetch specific node details from graph service."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.graph_service_url}/graph/{repo_id}/node/{node_id}"
            )
            response.raise_for_status()
            return response.json()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Graph service unavailable",
        )
