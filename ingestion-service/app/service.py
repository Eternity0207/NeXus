"""Ingestion orchestrator — coordinates clone, extract, and publish."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from app.config import get_settings
from app.git_ops import clone_repository, extract_file_tree, get_commit_sha, detect_repo_languages
from app.producer import get_producer
from app.store import repo_store, RepoStatus

logger = logging.getLogger("ingestion-service")
settings = get_settings()


def ingest_repository(repo_id: str, repo_url: str, branch: str = "main") -> dict:
    """Full ingestion pipeline: clone → extract → publish.

    Declared as a plain sync function on purpose: every step below
    (GitPython clone, filesystem walk, kafka publish) is blocking.
    FastAPI's BackgroundTasks runs sync callables in a worker thread,
    so keeping this sync prevents the service's event loop from being
    blocked while a repo is being cloned (which would make /repos,
    /health, etc. time out for the duration of the clone).

    Args:
        repo_id: Unique identifier for this ingestion.
        repo_url: Git repository URL.
        branch: Branch to clone.

    Returns:
        Dict with ingestion result summary.
    """
    # Track state
    record = repo_store.create(repo_id, repo_url, branch)

    try:
        # Phase 1: Clone
        repo_store.update_status(repo_id, RepoStatus.CLONING)
        repo_path = clone_repository(repo_url, repo_id, branch)

        # Phase 2: Extract
        repo_store.update_status(repo_id, RepoStatus.EXTRACTING)
        commit_sha = get_commit_sha(repo_path)
        files = extract_file_tree(repo_path)
        languages = detect_repo_languages(files)

        repo_store.update_status(
            repo_id,
            RepoStatus.PUBLISHING,
            commit_sha=commit_sha,
            file_count=len(files),
            languages=languages,
        )

        # Phase 3: Publish to Kafka
        event_id = str(uuid.uuid4())
        producer = get_producer()
        success = producer.publish_repo_ingested(
            event_id=event_id,
            repo_id=repo_id,
            repo_url=repo_url,
            branch=branch,
            commit_sha=commit_sha,
            files=files,
        )

        if success:
            repo_store.update_status(repo_id, RepoStatus.COMPLETED)
            logger.info(f"Ingestion complete: {repo_id} ({len(files)} files, {len(languages)} languages)")
        else:
            repo_store.update_status(
                repo_id, RepoStatus.COMPLETED,
                error="Kafka publish failed — data extracted but event not sent",
            )

        return {
            "repo_id": repo_id,
            "status": "completed",
            "file_count": len(files),
            "languages": languages,
            "commit_sha": commit_sha,
        }

    except Exception as e:
        logger.error(f"Ingestion failed for {repo_id}: {e}")
        repo_store.update_status(repo_id, RepoStatus.FAILED, error=str(e))
        return {
            "repo_id": repo_id,
            "status": "failed",
            "error": str(e),
        }
