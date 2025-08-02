"""NEXUS Ingestion Service — Main FastAPI Application."""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, Field

from app.config import get_settings
from app.service import ingest_repository
from app.store import repo_store
from app.producer import get_producer

settings = get_settings()

# ─── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("ingestion-service")


# ─── Lifespan ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 {settings.service_name} v{settings.version} starting on :{settings.port}")
    yield
    # Cleanup Kafka producer
    producer = get_producer()
    producer.close()
    logger.info(f"🛑 {settings.service_name} shutting down")


# ─── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="NEXUS Ingestion Service",
    description="Repository cloning and file extraction service",
    version=settings.version,
    lifespan=lifespan,
)


# ─── Request Models ──────────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    repo_id: str
    repo_url: str = Field(..., description="Git repository URL")
    branch: str = Field(default="main")


# ─── Endpoints ───────────────────────────────────────────────────────────────

@app.post(
    "/ingest",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger repository ingestion",
)
async def trigger_ingest(request: IngestRequest, background_tasks: BackgroundTasks) -> dict:
    """Start async repository ingestion.
    
    Clones the repo, extracts file metadata, and publishes
    a repo.ingested event to Kafka.
    """
    # Check if already ingesting
    existing = repo_store.get(request.repo_id)
    if existing and existing.status in ("cloning", "extracting", "publishing"):
        return {
            "repo_id": request.repo_id,
            "status": "already_processing",
            "message": f"Repository is currently {existing.status}",
        }

    # Run ingestion in background
    background_tasks.add_task(
        ingest_repository,
        repo_id=request.repo_id,
        repo_url=request.repo_url,
        branch=request.branch,
    )

    return {
        "repo_id": request.repo_id,
        "status": "accepted",
        "message": "Ingestion started in background",
    }


@app.get(
    "/repos/{repo_id}",
    summary="Get repository status",
)
async def get_repo_status(repo_id: str) -> dict:
    """Get the current ingestion status for a repository."""
    record = repo_store.get(repo_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found",
        )
    return record.model_dump()


@app.get(
    "/repos",
    summary="List all repositories",
)
async def list_repos() -> dict:
    """List all ingested repositories and their statuses."""
    repos = repo_store.list_all()
    return {
        "total": len(repos),
        "repositories": [r.model_dump() for r in repos],
    }


@app.get("/health")
async def health() -> dict:
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": settings.version,
    }
