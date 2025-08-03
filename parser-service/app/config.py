"""Parser service configuration."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Parser service configuration with env overrides."""

    # Service
    service_name: str = "parser-service"
    version: str = "0.1.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8002

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_group_id: str = "parser-service-group"

    # Repos
    repos_base_path: str = "./repos"

    # Parser limits
    max_file_size_kb: int = 500
    max_functions_per_file: int = 200

    class Config:
        env_file = ".env"
        env_prefix = "NEXUS_"


@lru_cache
def get_settings() -> Settings:
    return Settings()
