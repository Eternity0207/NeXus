"""NEXUS AI Service — Main Application."""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional

from app.config import get_settings
from app.analysis import summarize_code, review_pr, detect_bugs, chat_with_codebase

settings = get_settings()

# ─── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("ai-service")


# ─── Lifespan ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 {settings.service_name} v{settings.version} starting")
    logger.info(f"LLM model: {settings.llm_model}")
    api_status = "configured" if settings.llm_api_key else "mock mode (no API key)"
    logger.info(f"API key: {api_status}")
    yield
    logger.info(f"🛑 {settings.service_name} shutting down")


# ─── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="NEXUS AI Service",
    description="LLM-powered code analysis, summarization, and chat",
    version=settings.version,
    lifespan=lifespan,
)


# ─── Request Models ──────────────────────────────────────────────────────────

class SummarizeRequest(BaseModel):
    file_path: str
    language: str = "python"
    code: str


class PRAnalyzeRequest(BaseModel):
    repo_id: str
    pr_url: str
    pr_id: str
    diff: str = ""
    changed_files: list[str] = Field(default_factory=list)


class BugDetectRequest(BaseModel):
    file_path: str
    language: str = "python"
    code: str


class ChatRequest(BaseModel):
    message: str
    repo_id: str
    conversation_id: Optional[str] = None


# ─── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> dict:
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": settings.version,
        "llm_model": settings.llm_model,
    }


@app.post("/summarize", summary="Summarize a code file", tags=["analysis"])
async def summarize(request: SummarizeRequest) -> dict:
    """Generate an AI summary of a code file."""
    try:
        summary = await summarize_code(request.file_path, request.language, request.code)
        return {"file_path": request.file_path, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pr/analyze", summary="Analyze a pull request", tags=["pr"])
async def analyze_pr(request: PRAnalyzeRequest) -> dict:
    """AI-powered pull request analysis with risk scoring."""
    try:
        result = await review_pr(
            pr_id=request.pr_id,
            changed_files=request.changed_files,
            diff=request.diff,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/bugs/detect", summary="Detect potential bugs", tags=["analysis"])
async def detect(request: BugDetectRequest) -> dict:
    """Scan code for potential bugs and security issues."""
    try:
        findings = await detect_bugs(request.file_path, request.language, request.code)
        return {"file_path": request.file_path, "findings": findings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat", summary="Chat with your codebase", tags=["chat"])
async def chat(request: ChatRequest) -> dict:
    """RAG-powered conversational interface to the codebase."""
    try:
        result = await chat_with_codebase(
            message=request.message,
            repo_id=request.repo_id,
            conversation_id=request.conversation_id,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
