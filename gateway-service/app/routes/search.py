"""Semantic search endpoints."""

import logging

import httpx
from fastapi import APIRouter, HTTPException, status

from app.config import get_settings
from app.models import SearchRequest, SearchResponse

logger = logging.getLogger("gateway-service")
router = APIRouter(prefix="/api/v1/search", tags=["search"])
settings = get_settings()


@router.post(
    "",
    response_model=SearchResponse,
    summary="Semantic code search",
    description="Search code using natural language queries. Results are ranked by semantic similarity.",
)
async def search_code(request: SearchRequest) -> SearchResponse:
    """Forward search request to the search service."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.search_service_url}/search",
                json=request.model_dump(),
            )
            response.raise_for_status()
            data = response.json()
            return SearchResponse(**data)
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search service unavailable",
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail="Search service error",
        )
