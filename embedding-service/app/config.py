"""Embedding service configuration."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Embedding service configuration with env overrides."""

    # Service
    service_name: str = "embedding-service"
    version: str = "0.1.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8003

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_group_id: str = "embedding-service-group"

    # ChromaDB
    chroma_host: str = "localhost"
    chroma_port: int = 8100
    chroma_collection: str = "nexus_code_embeddings"

    # Embedding model
    model_name: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384

    # Chunking
    max_chunk_tokens: int = 256
    chunk_overlap_lines: int = 2

    class Config:
        env_file = ".env"
        env_prefix = "NEXUS_"


@lru_cache
def get_settings() -> Settings:
    return Settings()
