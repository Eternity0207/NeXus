"""Shared Kafka consumer base with retry logic and dead letter handling."""

from __future__ import annotations

import json
import logging
import threading
import time
from abc import ABC, abstractmethod
from typing import Optional

from confluent_kafka import Consumer, KafkaError

logger = logging.getLogger("nexus")

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # seconds


class BaseKafkaConsumer(ABC):
    """Production-grade Kafka consumer base class.

    Features:
    - Automatic retry with exponential backoff
    - Dead letter logging for unprocessable messages
    - Graceful shutdown
    - Background thread execution
    - Processing metrics (count, errors)

    Subclasses implement `handle_event(event: dict)` with their logic.
    """

    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str,
        topics: list[str],
        service_name: str = "nexus",
    ):
        self._consumer = Consumer({
            "bootstrap.servers": bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,
            "max.poll.interval.ms": 300000,
            "session.timeout.ms": 30000,
        })
        self._topics = topics
        self._service_name = service_name
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._processed = 0
        self._errors = 0

    @abstractmethod
    def handle_event(self, event: dict) -> None:
        """Process a single event. Implement in subclasses."""
        ...

    def start(self) -> None:
        """Start consuming in a background thread."""
        if self._running:
            return

        self._consumer.subscribe(self._topics)
        self._running = True
        self._thread = threading.Thread(target=self._consume_loop, daemon=True)
        self._thread.start()
        logger.info(f"[{self._service_name}] Consumer started for topics: {self._topics}")

    def _consume_loop(self) -> None:
        try:
            while self._running:
                msg = self._consumer.poll(timeout=1.0)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    logger.error(f"[{self._service_name}] Consumer error: {msg.error()}")
                    continue

                self._process_message(msg)

        except Exception as e:
            logger.error(f"[{self._service_name}] Consumer loop crashed: {e}", exc_info=True)
        finally:
            self._consumer.close()

    def _process_message(self, msg) -> None:
        """Process message with retry logic."""
        try:
            value = json.loads(msg.value().decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"[{self._service_name}] Malformed message: {e}")
            self._errors += 1
            return

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                self.handle_event(value)
                self._processed += 1
                return
            except Exception as e:
                wait = RETRY_BACKOFF_BASE ** attempt
                logger.warning(
                    f"[{self._service_name}] Attempt {attempt}/{MAX_RETRIES} failed: {e}. "
                    f"Retrying in {wait}s..."
                )
                if attempt < MAX_RETRIES:
                    time.sleep(wait)

        # All retries exhausted — dead letter
        self._errors += 1
        event_id = value.get("event_id", "unknown")
        logger.error(
            f"[{self._service_name}] Dead letter: event {event_id} failed after {MAX_RETRIES} retries"
        )

    def stop(self) -> None:
        """Stop the consumer loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
        logger.info(
            f"[{self._service_name}] Consumer stopped. "
            f"Processed: {self._processed}, Errors: {self._errors}"
        )

    @property
    def stats(self) -> dict:
        return {
            "processed": self._processed,
            "errors": self._errors,
            "running": self._running,
        }
