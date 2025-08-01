"""Shared Pydantic schemas for Kafka event payloads."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ─── Base Event ──────────────────────────────────────────────────────────────

class BaseEvent(BaseModel):
    """Base schema for all Kafka events."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ─── Ingestion Events ───────────────────────────────────────────────────────

class FileInfo(BaseModel):
    """Metadata for a single file in a repository."""
    path: str
    language: str
    size_bytes: int


class RepoIngestedEvent(BaseEvent):
    """Emitted when a repository is successfully cloned and indexed."""
    repo_id: str
    repo_url: str
    branch: str = "main"
    commit_sha: str = ""
    files: list[FileInfo] = Field(default_factory=list)


# ─── Parser Events ──────────────────────────────────────────────────────────

class FunctionInfo(BaseModel):
    """Extracted function metadata."""
    name: str
    start_line: int
    end_line: int
    params: list[str] = Field(default_factory=list)
    docstring: Optional[str] = None


class ClassInfo(BaseModel):
    """Extracted class metadata."""
    name: str
    methods: list[str] = Field(default_factory=list)
    bases: list[str] = Field(default_factory=list)


class FileParsedEvent(BaseEvent):
    """Emitted when a file is successfully parsed into AST components."""
    repo_id: str
    file_path: str
    language: str
    functions: list[FunctionInfo] = Field(default_factory=list)
    classes: list[ClassInfo] = Field(default_factory=list)
    imports: list[str] = Field(default_factory=list)
    raw_content: str = ""


# ─── Embedding Events ───────────────────────────────────────────────────────

class ChunkEmbedding(BaseModel):
    """A single code chunk with its vector embedding."""
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    vector: list[float] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class EmbeddingsGeneratedEvent(BaseEvent):
    """Emitted when embeddings are generated for a file's code chunks."""
    repo_id: str
    file_path: str
    chunks: list[ChunkEmbedding] = Field(default_factory=list)


# ─── Graph Events ────────────────────────────────────────────────────────────

class GraphUpdatedEvent(BaseEvent):
    """Emitted when the dependency graph is updated for a repository."""
    repo_id: str
    nodes_added: int = 0
    edges_added: int = 0
    node_types: dict[str, int] = Field(default_factory=dict)


# ─── PR Analysis Events ─────────────────────────────────────────────────────

class PRSuggestion(BaseModel):
    """A single review suggestion for a PR."""
    file: str
    line: int
    severity: str = "info"  # info, warning, error
    message: str


class PRAnalyzedEvent(BaseEvent):
    """Emitted when a PR has been analyzed by the AI service."""
    repo_id: str
    pr_id: str
    summary: str = ""
    risk_score: float = 0.0
    suggestions: list[PRSuggestion] = Field(default_factory=list)
