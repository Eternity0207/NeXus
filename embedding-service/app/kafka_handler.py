"""Kafka consumer and producer for the embedding pipeline."""

from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime
from typing import Optional

from confluent_kafka import Consumer, Producer, KafkaError

from app.config import get_settings
from app.chunker import chunk_parsed_file
from app.embedder import generate_embeddings
from app.vector_store import store_embeddings

logger = logging.getLogger("embedding-service")
settings = get_settings()

TOPIC_FILE_PARSED = "file.parsed"
TOPIC_EMBEDDINGS_GENERATED = "embeddings.generated"


class EmbeddingProducer:
    """Produces embeddings.generated events."""

    def __init__(self):
        self._producer = Producer({
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "client.id": "embedding-service-producer",
            "acks": "all",
        })

    def publish(self, repo_id: str, file_path: str, chunks: list[dict]) -> None:
        """Publish an embeddings.generated event."""
        event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "repo_id": repo_id,
            "file_path": file_path,
            "chunks": chunks,
        }

        self._producer.produce(
            topic=TOPIC_EMBEDDINGS_GENERATED,
            key=f"{repo_id}:{file_path}".encode("utf-8"),
            value=json.dumps(event).encode("utf-8"),
            callback=self._on_delivery,
        )
        self._producer.poll(0)

    def flush(self):
        self._producer.flush(timeout=10)

    @staticmethod
    def _on_delivery(err, msg):
        if err:
            logger.error(f"embeddings.generated delivery failed: {err}")


class EmbeddingConsumer:
    """Consumes file.parsed events and runs the embedding pipeline."""

    def __init__(self):
        self._consumer = Consumer({
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "group.id": settings.kafka_group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,
        })
        self._producer = EmbeddingProducer()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def _handle_event(self, event: dict) -> None:
        """Process a file.parsed event through the embedding pipeline."""
        repo_id = event.get("repo_id", "")
        file_path = event.get("file_path", "")

        logger.info(f"Processing file.parsed: {file_path}")

        # Step 1: Chunk the parsed file
        chunks = chunk_parsed_file(event)
        if not chunks:
            logger.debug(f"No chunks generated for {file_path}")
            return

        # Step 2: Generate embeddings for all chunks
        texts = [chunk.content for chunk in chunks]
        vectors = generate_embeddings(texts)

        if len(vectors) != len(chunks):
            logger.error(f"Vector count mismatch: {len(vectors)} vs {len(chunks)} chunks")
            return

        # Step 3: Store in ChromaDB
        chunk_ids = [chunk.chunk_id for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]

        stored = store_embeddings(
            chunk_ids=chunk_ids,
            embeddings=vectors,
            documents=texts,
            metadatas=metadatas,
        )

        # Step 4: Publish embeddings.generated event
        event_chunks = [
            {
                "chunk_id": chunk.chunk_id,
                "content": chunk.content[:200],  # Truncate for event payload
                "vector": vectors[i][:10],  # Only first 10 dims for the event
                "metadata": chunk.metadata,
            }
            for i, chunk in enumerate(chunks)
        ]

        self._producer.publish(repo_id, file_path, event_chunks)
        self._producer.flush()

        logger.info(
            f"Embedded {file_path}: {len(chunks)} chunks, {stored} stored in ChromaDB"
        )

    def start(self) -> None:
        """Start consuming in a background thread."""
        if self._running:
            return

        self._consumer.subscribe([TOPIC_FILE_PARSED])
        self._running = True
        self._thread = threading.Thread(target=self._consume_loop, daemon=True)
        self._thread.start()
        logger.info(f"Embedding consumer started (group: {settings.kafka_group_id})")

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
        logger.info("Embedding consumer stopped")


_consumer: Optional[EmbeddingConsumer] = None


def get_consumer() -> EmbeddingConsumer:
    global _consumer
    if _consumer is None:
        _consumer = EmbeddingConsumer()
    return _consumer
