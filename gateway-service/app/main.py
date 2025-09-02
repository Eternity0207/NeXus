"""NEXUS Gateway Service — Main FastAPI Application."""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.middleware import RequestLoggingMiddleware
from app.error_handler import ErrorHandlerMiddleware
from app.models import HealthResponse
from app.routes import repos, search, chat, graph, pr

settings = get_settings()

# ─── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("gateway-service")


# ─── Lifespan ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown hooks."""
    logger.info(f"🚀 {settings.service_name} v{settings.version} starting on :{settings.port}")
    logger.info(f"Kafka: {settings.kafka_bootstrap_servers}")
    yield
    logger.info(f"🛑 {settings.service_name} shutting down")


# ─── Application ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="NEXUS Gateway API",
    description="API gateway for the NEXUS Codebase Intelligence Platform",
    version=settings.version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── Middleware ───────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_origin_regex=settings.allowed_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(ErrorHandlerMiddleware)

# ─── Routes ──────────────────────────────────────────────────────────────────

app.include_router(repos.router)
app.include_router(search.router)
app.include_router(chat.router)
app.include_router(graph.router)
app.include_router(pr.router)


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["health"],
    summary="Health check",
)
async def health_check() -> HealthResponse:
    """Service health check endpoint."""
    return HealthResponse(version=settings.version)


@app.get("/", tags=["root"])
async def root() -> dict:
    """Root endpoint with API information."""
    return {
        "service": settings.service_name,
        "version": settings.version,
        "docs": "/docs",
        "health": "/health",
    }
