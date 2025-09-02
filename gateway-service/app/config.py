"""Gateway service configuration."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Gateway configuration with environment variable overrides."""

    # Service metadata
    service_name: str = "gateway-service"
    version: str = "0.1.0"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"

    # Internal service URLs
    ingestion_service_url: str = "http://localhost:8001"
    parser_service_url: str = "http://localhost:8002"
    embedding_service_url: str = "http://localhost:8003"
    graph_service_url: str = "http://localhost:8004"
    ai_service_url: str = "http://localhost:8005"
    search_service_url: str = "http://localhost:8006"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379

    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # CORS — include the Caddy subdomain setup used in dev and production
    allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://nexus.localhost",
        "https://nexus.localhost",
    ]
    # Regex for additional origins (e.g. all *.localhost subdomains + prod host)
    allowed_origin_regex: str = r"https?://([a-z0-9-]+\.)?(localhost|nexus\.local)(:\d+)?"

    class Config:
        env_file = ".env"
        env_prefix = "NEXUS_"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
