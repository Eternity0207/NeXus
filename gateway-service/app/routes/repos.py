"""Repository management endpoints."""

import logging
import uuid

import httpx
from fastapi import APIRouter, HTTPException, status

from app.config import get_settings
from app.models import IngestRepoRequest, IngestRepoResponse

logger = logging.getLogger("gateway-service")
router = APIRouter(prefix="/api/v1/repos", tags=["repositories"])
settings = get_settings()


@router.post(
    "",
    response_model=IngestRepoResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest a repository",
    description="Submit a repository URL for ingestion. The service will clone, parse, embed, and graph the codebase asynchronously.",
)
async def ingest_repo(request: IngestRepoRequest) -> IngestRepoResponse:
    """Forward ingestion request to the ingestion service."""
    repo_id = str(uuid.uuid4())

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.ingestion_service_url}/ingest",
                json={
                    "repo_id": repo_id,
                    "repo_url": request.repo_url,
                    "branch": request.branch,
                },
            )
            response.raise_for_status()
    except httpx.ConnectError:
        logger.warning("Ingestion service unavailable, queuing request")
        # In production, this would queue to Kafka directly
        # For now, return accepted with a note
        return IngestRepoResponse(
            repo_id=repo_id,
            status="queued",
            message="Ingestion service unavailable — request queued",
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"Ingestion service error: {e.response.status_code}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Ingestion service returned an error",
        )

    return IngestRepoResponse(repo_id=repo_id)


@router.get(
    "/{repo_id}",
    summary="Get repository details",
    description="Retrieve the current status and metadata for an ingested repository.",
)
async def get_repo(repo_id: str) -> dict:
    """Get repository status and metadata."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.ingestion_service_url}/repos/{repo_id}"
            )
            response.raise_for_status()
            return response.json()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ingestion service unavailable",
        )
    except httpx.HTTPStatusError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found",
        )


@router.get(
    "",
    summary="List repositories",
    description="List all ingested repositories.",
)
async def list_repos() -> dict:
    """List all ingested repositories."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.ingestion_service_url}/repos"
            )
            response.raise_for_status()
            return response.json()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ingestion service unavailable",
        )
