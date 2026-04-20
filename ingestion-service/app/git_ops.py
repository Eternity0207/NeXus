"""Git repository operations — clone, extract, detect languages."""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Optional

from git import Repo, GitCommandError

from app.config import get_settings

logger = logging.getLogger("ingestion-service")
settings = get_settings()

# Map file extensions to language names
EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".css": "css",
    ".html": "html",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".md": "markdown",
    ".txt": "text",
    ".toml": "toml",
    ".cfg": "config",
}


def clone_repository(
    repo_url: str,
    repo_id: str,
    branch: str = "main",
) -> Path:
    """Clone a Git repository to the local filesystem.

    Args:
        repo_url: Git remote URL (HTTPS or SSH).
        repo_id: Unique identifier for this ingestion.
        branch: Branch to clone.

    Returns:
        Path to the cloned repository.

    Raises:
        GitCommandError: If cloning fails.
    """
    clone_path = (Path(settings.repos_base_path) / repo_id).resolve()
    
    # Clean up if previous clone exists
    if clone_path.exists():
        logger.info(f"Removing existing clone at {clone_path}")
        shutil.rmtree(clone_path)

    logger.info(f"Cloning {repo_url} (branch: {branch}) → {clone_path}")

    try:
        Repo.clone_from(
            url=repo_url,
            to_path=str(clone_path),
            branch=branch,
            depth=settings.clone_depth,
            single_branch=True,
        )
        logger.info(f"Clone complete: {clone_path}")
        return clone_path
    except GitCommandError as e:
        logger.error(f"Clone failed for {repo_url}: {e}")
        raise


def get_commit_sha(repo_path: Path) -> str:
    """Get the HEAD commit SHA of a cloned repo."""
    try:
        repo = Repo(str(repo_path))
        return str(repo.head.commit.hexsha)
    except Exception:
        return ""


def extract_file_tree(repo_path: Path) -> list[dict]:
    """Walk the repository and extract metadata for supported files.

    Args:
        repo_path: Path to the cloned repository root.

    Returns:
        List of file info dicts: {path, language, size_bytes}
    """
    files = []
    max_size_bytes = settings.max_file_size_kb * 1024

    for root, dirs, filenames in os.walk(repo_path):
        # Skip hidden directories (.git, .github, etc.)
        dirs[:] = [d for d in dirs if not d.startswith(".")]

        # Skip common non-source directories
        dirs[:] = [
            d for d in dirs
            if d not in {"node_modules", "__pycache__", "venv", ".venv", "dist", "build", ".tox"}
        ]

        for filename in filenames:
            filepath = Path(root) / filename
            ext = filepath.suffix.lower()

            # Only include supported extensions
            if ext not in settings.supported_extensions:
                continue

            # Skip files that are too large
            try:
                size = filepath.stat().st_size
            except OSError:
                continue

            if size > max_size_bytes:
                logger.debug(f"Skipping large file: {filepath} ({size} bytes)")
                continue

            # Relative path from repo root
            rel_path = str(filepath.relative_to(repo_path))
            language = EXTENSION_LANGUAGE_MAP.get(ext, "unknown")

            files.append({
                "path": rel_path,
                "language": language,
                "size_bytes": size,
            })

    logger.info(f"Extracted {len(files)} files from {repo_path}")
    return files


def detect_repo_languages(files: list[dict]) -> dict[str, int]:
    """Count files per language for repo statistics.

    Args:
        files: File info list from extract_file_tree.

    Returns:
        Dict of {language: file_count}, sorted by count descending.
    """
    counts: dict[str, int] = {}
    for f in files:
        lang = f["language"]
        counts[lang] = counts.get(lang, 0) + 1

    return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))
