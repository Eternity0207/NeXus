"""AI chat with codebase endpoints."""

import logging

import httpx
from fastapi import APIRouter, HTTPException, status

from app.config import get_settings
from app.models import ChatRequest, ChatResponse

logger = logging.getLogger("gateway-service")
router = APIRouter(prefix="/api/v1/chat", tags=["chat"])
settings = get_settings()


@router.post(
    "",
    response_model=ChatResponse,
    summary="Chat with your codebase",
    description="Ask questions about your codebase using natural language. Powered by RAG + LLM.",
)
async def chat_with_codebase(request: ChatRequest) -> ChatResponse:
    """Forward chat request to the AI service."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.ai_service_url}/chat",
                json=request.model_dump(),
            )
            response.raise_for_status()
            data = response.json()
            return ChatResponse(**data)
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service unavailable",
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail="AI service error",
        )
