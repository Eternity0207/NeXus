"""Kafka producer and consumer utilities for NEXUS services."""

from __future__ import annotations

import json
import logging
from typing import Callable, Optional

from confluent_kafka import Consumer, Producer, KafkaError

from shared.config import kafka_config

logger = logging.getLogger(__name__)


class KafkaProducer:
    """Wrapper around confluent_kafka Producer with JSON serialization."""

    def __init__(self, client_id: str = "nexus-producer"):
        self._producer = Producer({
            "bootstrap.servers": kafka_config.bootstrap_servers,
            "client.id": client_id,
            "acks": "all",
            "retries": 3,
            "retry.backoff.ms": 500,
        })

    def produce(self, topic: str, value: dict, key: Optional[str] = None) -> None:
        """Produce a JSON message to the specified topic."""
        try:
            self._producer.produce(
                topic=topic,
                key=key.encode("utf-8") if key else None,
                value=json.dumps(value).encode("utf-8"),
                callback=self._delivery_callback,
            )
            self._producer.flush(timeout=5)
        except Exception as e:
            logger.error(f"Failed to produce message to {topic}: {e}")
            raise

    @staticmethod
    def _delivery_callback(err, msg) -> None:
        if err:
            logger.error(f"Delivery failed: {err}")
        else:
            logger.debug(f"Delivered to {msg.topic()}[{msg.partition()}]")


class KafkaConsumer:
    """Wrapper around confluent_kafka Consumer with JSON deserialization."""

    def __init__(self, group_id: str, topics: list[str]):
        self._consumer = Consumer({
            "bootstrap.servers": kafka_config.bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": kafka_config.auto_offset_reset,
            "enable.auto.commit": kafka_config.enable_auto_commit,
        })
        self._consumer.subscribe(topics)
        self._running = False

    def consume(
        self,
        handler: Callable[[dict], None],
        poll_timeout: float = 1.0,
    ) -> None:
        """Start consuming messages, calling handler for each."""
        self._running = True
        logger.info(f"Consumer started for group '{self._consumer}'")

        try:
            while self._running:
                msg = self._consumer.poll(timeout=poll_timeout)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    logger.error(f"Consumer error: {msg.error()}")
                    continue

                try:
                    value = json.loads(msg.value().decode("utf-8"))
                    handler(value)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode message: {e}")
                except Exception as e:
                    logger.error(f"Handler error: {e}")

        except KeyboardInterrupt:
            logger.info("Consumer interrupted")
        finally:
            self._consumer.close()

    def stop(self) -> None:
        """Signal the consumer loop to stop."""
        self._running = False
