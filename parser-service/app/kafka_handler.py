"""Kafka consumer and producer for the parser service pipeline."""

from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime
from typing import Optional

from confluent_kafka import Consumer, Producer, KafkaError

from app.config import get_settings
from app.processor import parse_repo_files
from app.base import ParseResult

logger = logging.getLogger("parser-service")
settings = get_settings()

TOPIC_REPO_INGESTED = "repo.ingested"
TOPIC_FILE_PARSED = "file.parsed"


class ParserProducer:
    """Produces file.parsed events to Kafka."""

    def __init__(self):
        self._producer = Producer({
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "client.id": "parser-service-producer",
            "acks": "all",
        })

    def publish_file_parsed(self, repo_id: str, result: ParseResult) -> None:
        """Publish a file.parsed event for a single parsed file."""
        event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "repo_id": repo_id,
            "file_path": result.file_path,
            "language": result.language,
            "functions": [
                {
                    "name": f.name,
                    "start_line": f.start_line,
                    "end_line": f.end_line,
                    "params": f.params,
                    "docstring": f.docstring,
                }
                for f in result.functions
            ],
            "classes": [
                {
                    "name": c.name,
                    "methods": c.methods,
                    "bases": c.bases,
                }
                for c in result.classes
            ],
            "imports": result.imports,
            "raw_content": result.raw_content,
        }

        self._producer.produce(
            topic=TOPIC_FILE_PARSED,
            key=f"{repo_id}:{result.file_path}".encode("utf-8"),
            value=json.dumps(event).encode("utf-8"),
            callback=self._on_delivery,
        )
        self._producer.poll(0)

    def flush(self) -> None:
        self._producer.flush(timeout=10)

    @staticmethod
    def _on_delivery(err, msg) -> None:
        if err:
            logger.error(f"file.parsed delivery failed: {err}")
        else:
            logger.debug(f"Published file.parsed → {msg.topic()}[{msg.partition()}]")


class ParserConsumer:
    """Consumes repo.ingested events and triggers parsing pipeline."""

    def __init__(self):
        self._consumer = Consumer({
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "group.id": settings.kafka_group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,
        })
        self._producer = ParserProducer()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def _handle_event(self, event: dict) -> None:
        """Process a repo.ingested event."""
        repo_id = event.get("repo_id", "")
        repo_url = event.get("repo_url", "")
        files = event.get("files", [])

        logger.info(f"Processing repo.ingested: {repo_id} ({len(files)} files)")

        # Prefer the absolute path the ingestion service published;
        # fall back to the local convention for events from older producers.
        repo_path = event.get("repo_path") or f"{settings.repos_base_path}/{repo_id}"

        # Parse all files
        results = parse_repo_files(files, repo_id, repo_path)

        # Publish file.parsed events
        for result in results:
            self._producer.publish_file_parsed(repo_id, result)

        self._producer.flush()
        logger.info(f"Published {len(results)} file.parsed events for repo {repo_id}")

    def start(self) -> None:
        """Start consuming in a background thread."""
        if self._running:
            return

        self._consumer.subscribe([TOPIC_REPO_INGESTED])
        self._running = True
        self._thread = threading.Thread(target=self._consume_loop, daemon=True)
        self._thread.start()
        logger.info(f"Parser consumer started (group: {settings.kafka_group_id})")

    def _consume_loop(self) -> None:
        """Main consume loop."""
        try:
            while self._running:
                msg = self._consumer.poll(timeout=1.0)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    logger.error(f"Consumer error: {msg.error()}")
                    continue

                try:
                    event = json.loads(msg.value().decode("utf-8"))
                    self._handle_event(event)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in message: {e}")
                except Exception as e:
                    logger.error(f"Error processing event: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Consumer loop crashed: {e}", exc_info=True)
        finally:
            self._consumer.close()

    def stop(self) -> None:
        """Stop the consumer loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Parser consumer stopped")


# Singleton
_consumer: Optional[ParserConsumer] = None


def get_consumer() -> ParserConsumer:
    global _consumer
    if _consumer is None:
        _consumer = ParserConsumer()
    return _consumer
