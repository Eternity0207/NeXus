"""Kafka consumer and producer for the graph service pipeline."""

from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime
from typing import Optional

from confluent_kafka import Consumer, Producer, KafkaError

from app.config import get_settings
from app.graph_builder import build_file_graph

logger = logging.getLogger("graph-service")
settings = get_settings()

TOPIC_FILE_PARSED = "file.parsed"
TOPIC_GRAPH_UPDATED = "graph.updated"


class GraphProducer:
    """Produces graph.updated events."""

    def __init__(self):
        self._producer = Producer({
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "client.id": "graph-service-producer",
            "acks": "all",
        })

    def publish(self, repo_id: str, summary: dict) -> None:
        event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "repo_id": repo_id,
            "nodes_added": summary.get("nodes_added", 0),
            "edges_added": summary.get("edges_added", 0),
            "node_types": summary.get("node_types", {}),
        }

        self._producer.produce(
            topic=TOPIC_GRAPH_UPDATED,
            key=repo_id.encode("utf-8"),
            value=json.dumps(event).encode("utf-8"),
            callback=self._on_delivery,
        )
        self._producer.poll(0)

    def flush(self):
        self._producer.flush(timeout=10)

    @staticmethod
    def _on_delivery(err, msg):
        if err:
            logger.error(f"graph.updated delivery failed: {err}")


class GraphConsumer:
    """Consumes file.parsed events and builds the dependency graph."""

    def __init__(self):
        self._consumer = Consumer({
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "group.id": settings.kafka_group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,
        })
        self._producer = GraphProducer()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def _handle_event(self, event: dict) -> None:
        """Process a file.parsed event into graph nodes/edges."""
        repo_id = event.get("repo_id", "")
        file_path = event.get("file_path", "")

        logger.info(f"Building graph for: {file_path}")

        try:
            summary = build_file_graph(event)
            self._producer.publish(repo_id, summary)
            self._producer.flush()
        except Exception as e:
            logger.error(f"Graph build failed for {file_path}: {e}", exc_info=True)

    def start(self) -> None:
        if self._running:
            return

        self._consumer.subscribe([TOPIC_FILE_PARSED])
        self._running = True
        self._thread = threading.Thread(target=self._consume_loop, daemon=True)
        self._thread.start()
        logger.info(f"Graph consumer started (group: {settings.kafka_group_id})")

    def _consume_loop(self) -> None:
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
                    logger.error(f"Invalid JSON: {e}")
                except Exception as e:
                    logger.error(f"Error processing event: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Consumer loop crashed: {e}", exc_info=True)
        finally:
            self._consumer.close()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Graph consumer stopped")


_consumer: Optional[GraphConsumer] = None


def get_consumer() -> GraphConsumer:
    global _consumer
    if _consumer is None:
        _consumer = GraphConsumer()
    return _consumer
