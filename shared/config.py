"""Centralized configuration for NEXUS services.

All environment variables are prefixed with NEXUS_ to avoid collisions with
unrelated tooling on the host machine. See .env.example for the full list.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str, default: str) -> str:
    """Fetch NEXUS_* env, falling back to legacy unprefixed for safety."""
    return os.getenv(f"NEXUS_{name}", os.getenv(name, default))


@dataclass(frozen=True)
class KafkaConfig:
    """Kafka connection configuration."""
    bootstrap_servers: str = _env("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    group_id: str = _env("KAFKA_GROUP_ID", "nexus-default")
    auto_offset_reset: str = "earliest"
    enable_auto_commit: bool = True


@dataclass(frozen=True)
class Neo4jConfig:
    """Neo4j connection configuration."""
    uri: str = _env("NEO4J_URI", "bolt://localhost:7687")
    username: str = _env("NEO4J_USERNAME", "neo4j")
    password: str = _env("NEO4J_PASSWORD", "nexus_password")


@dataclass(frozen=True)
class ChromaConfig:
    """ChromaDB connection configuration."""
    host: str = _env("CHROMA_HOST", "localhost")
    port: int = int(_env("CHROMA_PORT", "8100"))


@dataclass(frozen=True)
class RedisConfig:
    """Redis connection configuration."""
    host: str = _env("REDIS_HOST", "localhost")
    port: int = int(_env("REDIS_PORT", "6380"))
    db: int = int(_env("REDIS_DB", "0"))


@dataclass(frozen=True)
class KafkaTopics:
    """Kafka topic names used across services."""
    REPO_INGESTED: str = "repo.ingested"
    FILE_PARSED: str = "file.parsed"
    EMBEDDINGS_GENERATED: str = "embeddings.generated"
    GRAPH_UPDATED: str = "graph.updated"
    PR_ANALYZED: str = "pr.analyzed"


kafka_config = KafkaConfig()
neo4j_config = Neo4jConfig()
chroma_config = ChromaConfig()
redis_config = RedisConfig()
topics = KafkaTopics()
