"""Request/Response models for the Gateway API."""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from datetime import datetime


# ─── Repo Ingestion ──────────────────────────────────────────────────────────

class IngestRepoRequest(BaseModel):
    """Request to ingest a new repository."""
    repo_url: str = Field(..., description="Git repository URL to ingest")
    branch: str = Field(default="main", description="Branch to analyze")
    name: Optional[str] = Field(default=None, description="Optional display name")


class IngestRepoResponse(BaseModel):
    """Response after repo ingestion is initiated."""
    repo_id: str
    status: str = "ingesting"
    message: str = "Repository ingestion started"


# ─── Search ──────────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    """Semantic search query."""
    query: str = Field(..., min_length=1, max_length=500)
    repo_id: Optional[str] = None
    top_k: int = Field(default=10, ge=1, le=50)


class SearchResult(BaseModel):
    """A single search result."""
    file_path: str
    content: str
    score: float
    metadata: dict = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Search results response."""
    query: str
    results: list[SearchResult] = Field(default_factory=list)
    total: int = 0


# ─── Chat ────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """AI chat with codebase."""
    message: str = Field(..., min_length=1, max_length=2000)
    repo_id: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    """AI chat response."""
    reply: str
    conversation_id: str
    sources: list[dict] = Field(default_factory=list)


# ─── PR Analysis ─────────────────────────────────────────────────────────────

class AnalyzePRRequest(BaseModel):
    """Request to analyze a pull request."""
    repo_id: str
    pr_url: str
    pr_id: Optional[str] = None


class PRAnalysisResponse(BaseModel):
    """PR analysis result."""
    pr_id: str
    status: str = "analyzing"
    message: str = "PR analysis started"


# ─── Health ──────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    service: str = "gateway-service"
    version: str = "0.1.0"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
