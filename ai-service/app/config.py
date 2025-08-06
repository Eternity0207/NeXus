"""AI service configuration."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """AI service configuration with env overrides."""

    # Service
    service_name: str = "ai-service"
    version: str = "0.1.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8005

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_group_id: str = "ai-service-group"

    # LLM
    llm_model: str = "gpt-3.5-turbo"
    llm_api_key: str = ""
    llm_temperature: float = 0.2
    llm_max_tokens: int = 2048

    # Internal services
    search_service_url: str = "http://localhost:8006"
    graph_service_url: str = "http://localhost:8004"

    class Config:
        env_file = ".env"
        env_prefix = "NEXUS_"


@lru_cache
def get_settings() -> Settings:
    return Settings()
