"""Kafka event producer for the ingestion service."""

from __future__ import annotations

import json
import logging
from typing import Optional

from confluent_kafka import Producer

from app.config import get_settings

logger = logging.getLogger("ingestion-service")
settings = get_settings()

# Topic name
TOPIC_REPO_INGESTED = "repo.ingested"


class IngestionProducer:
    """Produces repo.ingested events to Kafka."""

    def __init__(self):
        self._producer = Producer({
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "client.id": "ingestion-service",
            "acks": "all",
            "retries": 3,
            "retry.backoff.ms": 500,
        })
        self._connected = False

    def _delivery_callback(self, err, msg) -> None:
        if err:
            logger.error(f"Kafka delivery failed: {err}")
        else:
            logger.info(
                f"Published to {msg.topic()}[{msg.partition()}] @ offset {msg.offset()}"
            )
            self._connected = True

    def publish_repo_ingested(
        self,
        event_id: str,
        repo_id: str,
        repo_url: str,
        branch: str,
        commit_sha: str,
        files: list[dict],
        repo_path: str = "",
    ) -> bool:
        """Publish a repo.ingested event.

        Args:
            event_id: Unique event identifier.
            repo_id: Repository identifier.
            repo_url: Source repository URL.
            branch: Branch that was cloned.
            commit_sha: HEAD commit SHA.
            files: List of file info dicts.

        Returns:
            True if message was queued successfully.
        """
        from datetime import datetime

        event = {
            "event_id": event_id,
            "timestamp": datetime.utcnow().isoformat(),
            "repo_id": repo_id,
            "repo_url": repo_url,
            "branch": branch,
            "commit_sha": commit_sha,
            "repo_path": repo_path,
            "files": files,
        }

        try:
            self._producer.produce(
                topic=TOPIC_REPO_INGESTED,
                key=repo_id.encode("utf-8"),
                value=json.dumps(event).encode("utf-8"),
                callback=self._delivery_callback,
            )
            self._producer.flush(timeout=10)
            logger.info(f"Published repo.ingested event for {repo_id} ({len(files)} files)")
            return True
        except Exception as e:
            logger.error(f"Failed to publish repo.ingested: {e}")
            return False

    def close(self) -> None:
        """Flush and close the producer."""
        self._producer.flush(timeout=5)


# Singleton
_producer: Optional[IngestionProducer] = None


def get_producer() -> IngestionProducer:
    """Get or create the singleton producer instance."""
    global _producer
    if _producer is None:
        _producer = IngestionProducer()
    return _producer
