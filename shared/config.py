"""Centralized configuration for NEXUS services."""

from dataclasses import dataclass, field
import os


@dataclass(frozen=True)
class KafkaConfig:
    """Kafka connection configuration."""
    bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    group_id: str = os.getenv("KAFKA_GROUP_ID", "nexus-default")
    auto_offset_reset: str = "earliest"
    enable_auto_commit: bool = True


@dataclass(frozen=True)
class Neo4jConfig:
    """Neo4j connection configuration."""
    uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username: str = os.getenv("NEO4J_USERNAME", "neo4j")
    password: str = os.getenv("NEO4J_PASSWORD", "nexus_password")


@dataclass(frozen=True)
class ChromaConfig:
    """ChromaDB connection configuration."""
    host: str = os.getenv("CHROMA_HOST", "localhost")
    port: int = int(os.getenv("CHROMA_PORT", "8100"))


@dataclass(frozen=True)
class RedisConfig:
    """Redis connection configuration."""
    host: str = os.getenv("REDIS_HOST", "localhost")
    port: int = int(os.getenv("REDIS_PORT", "6379"))
    db: int = int(os.getenv("REDIS_DB", "0"))


@dataclass(frozen=True)
class KafkaTopics:
    """Kafka topic names used across services."""
    REPO_INGESTED: str = "repo.ingested"
    FILE_PARSED: str = "file.parsed"
    EMBEDDINGS_GENERATED: str = "embeddings.generated"
    GRAPH_UPDATED: str = "graph.updated"
    PR_ANALYZED: str = "pr.analyzed"


# Singleton instances
kafka_config = KafkaConfig()
neo4j_config = Neo4jConfig()
chroma_config = ChromaConfig()
redis_config = RedisConfig()
topics = KafkaTopics()
