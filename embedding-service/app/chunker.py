"""Intelligent code chunking for embedding generation.

Chunks code at meaningful boundaries (functions, classes) rather
than arbitrary token counts, preserving semantic coherence.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Optional

from app.config import get_settings

logger = logging.getLogger("embedding-service")
settings = get_settings()


@dataclass
class CodeChunk:
    """A semantically meaningful code chunk ready for embedding."""
    chunk_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    metadata: dict = field(default_factory=dict)


def chunk_parsed_file(event: dict) -> list[CodeChunk]:
    """Chunk a parsed file into embedding-ready pieces.

    Strategy:
    1. Each function becomes its own chunk (with context)
    2. Each class becomes a chunk (signature + docstring)
    3. Remaining top-level code becomes file-level chunks
    4. Imports are grouped into a single chunk

    Args:
        event: A file.parsed Kafka event payload.

    Returns:
        List of CodeChunk objects.
    """
    chunks = []
    file_path = event.get("file_path", "")
    language = event.get("language", "unknown")
    repo_id = event.get("repo_id", "")
    raw_content = event.get("raw_content", "")
    functions = event.get("functions", [])
    classes = event.get("classes", [])
    imports = event.get("imports", [])

    if not raw_content.strip():
        return chunks

    lines = raw_content.split("\n")

    # ── Function chunks ──────────────────────────────────────────────────
    for func in functions:
        name = func.get("name", "")
        start = func.get("start_line", 1) - 1  # Convert to 0-indexed
        end = func.get("end_line", start + 1)
        params = func.get("params", [])
        docstring = func.get("docstring", "")

        # Add overlap context (lines before function)
        ctx_start = max(0, start - settings.chunk_overlap_lines)
        func_lines = lines[ctx_start:end]
        content = "\n".join(func_lines)

        if not content.strip():
            continue

        chunks.append(CodeChunk(
            content=content,
            metadata={
                "type": "function",
                "name": name,
                "file_path": file_path,
                "language": language,
                "repo_id": repo_id,
                "start_line": start + 1,
                "end_line": end,
                "params": params,
                "docstring": docstring or "",
            },
        ))

    # ── Class chunks (signature + docstring only, methods are separate) ──
    for cls in classes:
        name = cls.get("name", "")
        methods = cls.get("methods", [])
        bases = cls.get("bases", [])

        # Build a summary chunk for the class
        bases_str = f"({', '.join(bases)})" if bases else ""
        methods_str = ", ".join(methods) if methods else "none"
        summary = f"class {name}{bases_str}:\n  methods: {methods_str}"

        chunks.append(CodeChunk(
            content=summary,
            metadata={
                "type": "class",
                "name": name,
                "file_path": file_path,
                "language": language,
                "repo_id": repo_id,
                "methods": methods,
                "bases": bases,
            },
        ))

    # ── File-level summary chunk ─────────────────────────────────────────
    # Create a high-level summary chunk with imports and structure
    func_names = [f.get("name", "") for f in functions]
    class_names = [c.get("name", "") for c in classes]

    file_summary = f"File: {file_path}\n"
    file_summary += f"Language: {language}\n"
    if imports:
        file_summary += f"Imports: {', '.join(imports[:20])}\n"
    if func_names:
        file_summary += f"Functions: {', '.join(func_names[:20])}\n"
    if class_names:
        file_summary += f"Classes: {', '.join(class_names[:10])}\n"

    # Include first N lines as context
    preview_lines = min(30, len(lines))
    file_summary += f"\n{''.join(lines[:preview_lines])}"

    chunks.append(CodeChunk(
        content=file_summary,
        metadata={
            "type": "file_summary",
            "file_path": file_path,
            "language": language,
            "repo_id": repo_id,
            "function_count": len(func_names),
            "class_count": len(class_names),
            "import_count": len(imports),
        },
    ))

    logger.debug(f"Chunked {file_path}: {len(chunks)} chunks")
    return chunks
