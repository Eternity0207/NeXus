#!/bin/bash
# ─── NEXUS Kafka Topic Setup ────────────────────────────────────────────────
# Creates all required Kafka topics via the Kafka container.
# Run this after Kafka is up: ./scripts/create-topics.sh
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

KAFKA_CONTAINER="${KAFKA_CONTAINER:-nexus-kafka}"
KAFKA_BROKER="localhost:9092"

topics=(
  "repo.ingested:3:1"
  "file.parsed:6:1"
  "embeddings.generated:3:1"
  "graph.updated:3:1"
  "pr.analyzed:3:1"
)

echo "🔧 Creating NEXUS Kafka topics..."
echo "   Container: $KAFKA_CONTAINER"
echo ""

for entry in "${topics[@]}"; do
  IFS=':' read -r topic partitions replication <<< "$entry"

  echo -n "   Creating $topic (partitions=$partitions) ... "

  docker exec "$KAFKA_CONTAINER" \
    kafka-topics --bootstrap-server "$KAFKA_BROKER" \
    --create \
    --topic "$topic" \
    --partitions "$partitions" \
    --replication-factor "$replication" \
    --if-not-exists \
    2>/dev/null && echo "✅" || echo "⚠️  (may already exist)"
done

echo ""
echo "📋 Listing all topics:"
docker exec "$KAFKA_CONTAINER" kafka-topics --bootstrap-server "$KAFKA_BROKER" --list 2>/dev/null || echo "   (could not list)"

echo ""
echo "✅ Kafka topic setup complete"
