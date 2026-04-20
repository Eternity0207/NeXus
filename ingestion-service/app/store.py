"""In-memory repository store for tracking ingestion state."""

from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("ingestion-service")


class RepoStatus(str, Enum):
    """Repository ingestion status."""
    PENDING = "pending"
    CLONING = "cloning"
    EXTRACTING = "extracting"
    PUBLISHING = "publishing"
    COMPLETED = "completed"
    FAILED = "failed"


class RepoRecord(BaseModel):
    """Repository metadata record."""
    repo_id: str
    repo_url: str
    branch: str = "main"
    status: RepoStatus = RepoStatus.PENDING
    commit_sha: str = ""
    file_count: int = 0
    languages: dict[str, int] = Field(default_factory=dict)
    error: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class RepoStore:
    """In-memory store for repository records.
    
    In production, this would be backed by PostgreSQL or similar.
    """

    def __init__(self):
        self._repos: dict[str, RepoRecord] = {}

    def create(self, repo_id: str, repo_url: str, branch: str = "main") -> RepoRecord:
        record = RepoRecord(repo_id=repo_id, repo_url=repo_url, branch=branch)
        self._repos[repo_id] = record
        logger.info(f"Created repo record: {repo_id}")
        return record

    def update_status(
        self,
        repo_id: str,
        status: RepoStatus,
        **kwargs,
    ) -> Optional[RepoRecord]:
        record = self._repos.get(repo_id)
        if not record:
            return None

        record.status = status
        record.updated_at = datetime.utcnow().isoformat()

        for key, value in kwargs.items():
            if hasattr(record, key):
                setattr(record, key, value)

        return record

    def get(self, repo_id: str) -> Optional[RepoRecord]:
        return self._repos.get(repo_id)

    def list_all(self) -> list[RepoRecord]:
        return list(self._repos.values())

    def delete(self, repo_id: str) -> bool:
        """Remove the record for a repo. Returns True if it existed."""
        return self._repos.pop(repo_id, None) is not None


# Singleton store
repo_store = RepoStore()
