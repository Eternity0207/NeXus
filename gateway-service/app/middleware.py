"""Gateway middleware — request logging, timing, and correlation IDs."""

import time
import uuid
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("gateway-service")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs every request with timing and correlation ID."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        start_time = time.perf_counter()

        # Inject request_id into request state for downstream use
        request.state.request_id = request_id

        logger.info(
            f"→ {request.method} {request.url.path}",
            extra={"request_id": request_id},
        )

        response: Response = await call_next(request)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = str(duration_ms)

        logger.info(
            f"← {request.method} {request.url.path} [{response.status_code}] {duration_ms}ms",
            extra={"request_id": request_id},
        )

        return response
