"""NEXUS Parser Service — Main Application.

Runs as a Kafka consumer that listens for repo.ingested events,
parses source files, and publishes file.parsed events.
Also exposes a lightweight FastAPI server for health checks.
"""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.base import register_parser, get_supported_languages
from app.python_parser import PythonParser
from app.js_parser import JavaScriptParser
from app.kafka_handler import get_consumer

settings = get_settings()

# ─── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("parser-service")


# ─── Register Parsers ────────────────────────────────────────────────────────

def _register_all_parsers() -> None:
    """Register all available language parsers."""
    register_parser(PythonParser())
    register_parser(JavaScriptParser(lang="javascript"))
    register_parser(JavaScriptParser(lang="typescript"))


# ─── Lifespan ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start Kafka consumer on startup, stop on shutdown."""
    _register_all_parsers()
    logger.info(f"Supported languages: {get_supported_languages()}")

    consumer = get_consumer()
    consumer.start()
    logger.info(f"🚀 {settings.service_name} v{settings.version} running")

    yield

    consumer.stop()
    logger.info(f"🛑 {settings.service_name} shutting down")


# ─── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="NEXUS Parser Service",
    description="AST parsing and code structure extraction",
    version=settings.version,
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict:
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": settings.version,
        "supported_languages": get_supported_languages(),
    }


@app.get("/languages")
async def languages() -> dict:
    """List supported parsing languages."""
    return {"languages": get_supported_languages()}
