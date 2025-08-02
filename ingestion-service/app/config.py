"""Ingestion service configuration."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Ingestion service configuration with env overrides."""

    # Service
    service_name: str = "ingestion-service"
    version: str = "0.1.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8001

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"

    # Storage
    repos_base_path: str = "./repos"

    # Git
    clone_depth: int = 1  # Shallow clone by default
    max_file_size_kb: int = 500  # Skip files larger than this

    # Supported languages (extensions)
    supported_extensions: list[str] = [
        ".py", ".js", ".ts", ".jsx", ".tsx",
        ".java", ".go", ".rs", ".rb",
        ".c", ".cpp", ".h", ".hpp",
        ".css", ".html", ".json", ".yaml", ".yml",
        ".md", ".txt", ".toml", ".cfg",
    ]

    class Config:
        env_file = ".env"
        env_prefix = "NEXUS_"


@lru_cache
def get_settings() -> Settings:
    return Settings()
