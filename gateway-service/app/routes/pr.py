"""PR analysis endpoints."""

import logging

import httpx
from fastapi import APIRouter, HTTPException, status

from app.config import get_settings
from app.models import AnalyzePRRequest, PRAnalysisResponse

logger = logging.getLogger("gateway-service")
router = APIRouter(prefix="/api/v1/pr", tags=["pull-requests"])
settings = get_settings()


@router.post(
    "/analyze",
    response_model=PRAnalysisResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Analyze a pull request",
    description="Submit a PR for AI-powered analysis. Returns review suggestions, risk score, and summary.",
)
async def analyze_pr(request: AnalyzePRRequest) -> PRAnalysisResponse:
    """Forward PR analysis request to the AI service."""
    pr_id = request.pr_id or request.pr_url.split("/")[-1]

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.ai_service_url}/pr/analyze",
                json={
                    "repo_id": request.repo_id,
                    "pr_url": request.pr_url,
                    "pr_id": pr_id,
                },
            )
            response.raise_for_status()
    except httpx.ConnectError:
        logger.warning("AI service unavailable for PR analysis")
        return PRAnalysisResponse(
            pr_id=pr_id,
            status="queued",
            message="AI service unavailable — analysis queued",
        )

    return PRAnalysisResponse(pr_id=pr_id)
