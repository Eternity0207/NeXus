"""API error handling and exception middleware."""

from __future__ import annotations

import logging
import traceback
from datetime import datetime

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("gateway-service")


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Global error handler that catches unhandled exceptions
    and returns structured JSON error responses."""

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.error(
                f"Unhandled exception [{request_id}]: {exc}\n"
                f"{traceback.format_exc()}"
            )

            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_server_error",
                    "message": "An unexpected error occurred",
                    "request_id": request_id,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
