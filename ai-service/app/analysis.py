"""AI analysis service — orchestrates LLM calls for codebase intelligence."""

from __future__ import annotations

import logging
import uuid
from typing import Optional

import httpx

from app.config import get_settings
from app.llm_client import call_llm
from app.prompts import (
    SUMMARIZE_FILE_PROMPT,
    PR_REVIEW_PROMPT,
    BUG_DETECTION_PROMPT,
    CHAT_SYSTEM_PROMPT,
    CHAT_WITH_CONTEXT_PROMPT,
)

logger = logging.getLogger("ai-service")
settings = get_settings()


async def summarize_code(file_path: str, language: str, code: str) -> str:
    """Generate a summary for a code file."""
    prompt = SUMMARIZE_FILE_PROMPT.format(
        file_path=file_path,
        language=language,
        code=code[:4000],  # Truncate for token limits
    )
    return await call_llm(prompt)


async def review_pr(
    pr_id: str,
    changed_files: list[str],
    diff: str,
    context: str = "",
) -> dict:
    """Analyze a pull request and generate review suggestions."""
    prompt = PR_REVIEW_PROMPT.format(
        pr_id=pr_id,
        changed_files=", ".join(changed_files),
        diff=diff[:6000],
        context=context[:2000],
    )

    response = await call_llm(prompt)

    # Parse risk score from response (basic extraction)
    risk_score = 0.5
    for line in response.split("\n"):
        if "risk score" in line.lower():
            try:
                import re
                match = re.search(r"(\d+\.?\d*)", line)
                if match:
                    risk_score = min(1.0, float(match.group(1)))
            except (ValueError, AttributeError):
                pass

    return {
        "pr_id": pr_id,
        "summary": response,
        "risk_score": risk_score,
        "suggestions": _extract_suggestions(response),
    }


async def detect_bugs(file_path: str, language: str, code: str) -> list[dict]:
    """Run bug detection heuristics on a code file."""
    prompt = BUG_DETECTION_PROMPT.format(
        file_path=file_path,
        language=language,
        code=code[:4000],
    )

    response = await call_llm(prompt)
    return _parse_bug_findings(response)


async def chat_with_codebase(
    message: str,
    repo_id: str,
    conversation_id: Optional[str] = None,
) -> dict:
    """RAG-powered chat with the codebase.

    1. Search for relevant code snippets
    2. Fetch dependency context
    3. Generate response with LLM
    """
    conv_id = conversation_id or str(uuid.uuid4())

    # Step 1: Retrieve relevant code via search service
    context = await _retrieve_context(message, repo_id)

    # Step 2: Fetch graph context
    dependencies = await _fetch_graph_context(repo_id)

    # Step 3: Generate response
    prompt = CHAT_WITH_CONTEXT_PROMPT.format(
        context=context,
        dependencies=dependencies,
        question=message,
    )

    response = await call_llm(prompt, system_prompt=CHAT_SYSTEM_PROMPT)

    return {
        "reply": response,
        "conversation_id": conv_id,
        "sources": [],  # Would contain source references in production
    }


async def _retrieve_context(query: str, repo_id: str) -> str:
    """Retrieve relevant code snippets from the search service."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{settings.search_service_url}/search",
                json={"query": query, "repo_id": repo_id, "top_k": 5},
            )
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                snippets = []
                for r in results[:5]:
                    snippets.append(
                        f"**{r.get('file_path', 'unknown')}** (score: {r.get('score', 0):.2f})\n"
                        f"```\n{r.get('content', '')[:500]}\n```"
                    )
                return "\n\n".join(snippets) if snippets else "No relevant code found."
    except Exception as e:
        logger.warning(f"Search service unavailable: {e}")

    return "Search service unavailable — answering based on general knowledge."


async def _fetch_graph_context(repo_id: str) -> str:
    """Fetch graph statistics for additional context."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{settings.graph_service_url}/graph/{repo_id}/stats"
            )
            if response.status_code == 200:
                stats = response.json()
                nodes = stats.get("node_counts", {})
                return (
                    f"Graph: {nodes.get('File', 0)} files, "
                    f"{nodes.get('Function', 0)} functions, "
                    f"{nodes.get('Class', 0)} classes"
                )
    except Exception:
        pass

    return "Graph context unavailable."


def _extract_suggestions(response: str) -> list[dict]:
    """Extract structured suggestions from LLM response."""
    import re

    suggestions = []
    pattern = r"\[([^:]+):?(\d+)?\]\s*(critical|warning|info|error)?:?\s*(.+)"

    for line in response.split("\n"):
        match = re.search(pattern, line, re.IGNORECASE)
        if match:
            suggestions.append({
                "file": match.group(1).strip(),
                "line": int(match.group(2)) if match.group(2) else 0,
                "severity": (match.group(3) or "info").lower(),
                "message": match.group(4).strip(),
            })

    return suggestions


def _parse_bug_findings(response: str) -> list[dict]:
    """Parse bug detection findings from LLM response."""
    import re

    findings = []
    pattern = r"\[line\s*(\d+)\]\s*(critical|warning|info):?\s*(.+)"

    for line in response.split("\n"):
        match = re.search(pattern, line, re.IGNORECASE)
        if match:
            findings.append({
                "line": int(match.group(1)),
                "severity": match.group(2).lower(),
                "message": match.group(3).strip(),
            })

    return findings
