#!/bin/bash
# ─── NEXUS Health Check ─────────────────────────────────────────────────────
# Checks the health of all services.
# ─────────────────────────────────────────────────────────────────────────────

set -uo pipefail

services=(
  "gateway:8000"
  "ingestion:8001"
  "parser:8002"
  "embedding:8003"
  "graph:8004"
  "ai:8005"
  "search:8006"
)

echo "🔍 NEXUS Service Health Check"
echo "════════════════════════════════════════"

all_healthy=true

for entry in "${services[@]}"; do
  IFS=':' read -r name port <<< "$entry"

  printf "   %-20s" "$name (:$port)"

  if response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 "http://localhost:$port/health" 2>/dev/null); then
    if [ "$response" = "200" ]; then
      echo "✅ healthy"
    else
      echo "⚠️  HTTP $response"
      all_healthy=false
    fi
  else
    echo "❌ unreachable"
    all_healthy=false
  fi
done

echo "════════════════════════════════════════"

# Infrastructure checks
echo ""
echo "🛠️  Infrastructure"
echo "════════════════════════════════════════"

# Kafka
printf "   %-20s" "Kafka (:9092)"
if nc -z localhost 9092 2>/dev/null; then echo "✅ reachable"; else echo "❌ unreachable"; all_healthy=false; fi

# Neo4j
printf "   %-20s" "Neo4j (:7474)"
if curl -s -o /dev/null --connect-timeout 2 "http://localhost:7474" 2>/dev/null; then echo "✅ reachable"; else echo "❌ unreachable"; all_healthy=false; fi

# ChromaDB
printf "   %-20s" "ChromaDB (:8100)"
if curl -s -o /dev/null --connect-timeout 2 "http://localhost:8100/api/v1/heartbeat" 2>/dev/null; then echo "✅ reachable"; else echo "❌ unreachable"; all_healthy=false; fi

# Redis
printf "   %-20s" "Redis (:6380)"
if nc -z localhost 6380 2>/dev/null; then echo "✅ reachable"; else echo "❌ unreachable"; all_healthy=false; fi

echo "════════════════════════════════════════"

if $all_healthy; then
  echo "✅ All systems operational"
else
  echo "⚠️  Some services are unhealthy"
  exit 1
fi
