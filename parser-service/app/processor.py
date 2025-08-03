"""File processing orchestrator — reads files, dispatches to parsers, collects results."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from app.base import ParseResult, get_parser
from app.config import get_settings

logger = logging.getLogger("parser-service")
settings = get_settings()


def parse_file(file_path: str, repo_path: str, language: str) -> Optional[ParseResult]:
    """Parse a single file using the appropriate language parser.

    Args:
        file_path: Relative path to the file within the repo.
        repo_path: Absolute path to the repository root.
        language: Detected language of the file.

    Returns:
        ParseResult or None if no parser available / file unreadable.
    """
    parser = get_parser(language)
    if not parser:
        logger.debug(f"No parser for language '{language}', skipping {file_path}")
        return None

    full_path = Path(repo_path) / file_path

    try:
        content = full_path.read_text(encoding="utf-8", errors="replace")
    except (OSError, IOError) as e:
        logger.error(f"Cannot read {full_path}: {e}")
        return None

    # Skip empty files
    if not content.strip():
        return None

    # Skip very large files
    max_size = settings.max_file_size_kb * 1024
    if len(content.encode("utf-8")) > max_size:
        logger.debug(f"File too large, skipping: {file_path}")
        return None

    result = parser.parse(content, file_path)

    logger.info(
        f"Parsed {file_path}: "
        f"{len(result.functions)} functions, "
        f"{len(result.classes)} classes, "
        f"{len(result.imports)} imports"
    )

    return result


def parse_repo_files(
    files: list[dict],
    repo_id: str,
    repo_path: str,
) -> list[ParseResult]:
    """Parse all supported files in a repository.

    Args:
        files: List of file info dicts from repo.ingested event.
        repo_id: Repository identifier.
        repo_path: Local path to the cloned repo.

    Returns:
        List of ParseResult objects for successfully parsed files.
    """
    results = []
    skipped = 0

    for file_info in files:
        path = file_info["path"]
        lang = file_info.get("language", "unknown")

        result = parse_file(path, repo_path, lang)
        if result:
            results.append(result)
        else:
            skipped += 1

    logger.info(
        f"Repo {repo_id}: parsed {len(results)} files, skipped {skipped}"
    )
    return results
