#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# NEXUS — Full System Bootstrap Script
# Purges everything, clears ports, rebuilds, and starts the entire platform.
#
# Usage:
#   ./nexus.sh          # Full clean start
#   ./nexus.sh start    # Start without purging
#   ./nexus.sh stop     # Stop everything
#   ./nexus.sh status   # Check status
# ═══════════════════════════════════════════════════════════════════════════

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

log()   { echo -e "${CYAN}[NEXUS]${NC} $1"; }
ok()    { echo -e "${GREEN}  ✅ $1${NC}"; }
warn()  { echo -e "${YELLOW}  ⚠️  $1${NC}"; }
fail()  { echo -e "${RED}  ❌ $1${NC}"; }

# ─── Stop Everything ─────────────────────────────────────────────────────

stop_all() {
  log "Stopping all NEXUS services..."

  # Stop frontend dev server if running
  pkill -f "vite.*5173" 2>/dev/null || true

  # Stop any locally running uvicorn services
  pkill -f "uvicorn app.main" 2>/dev/null || true

  # Stop Docker services
  docker compose -f docker/docker-compose.services.yml down 2>/dev/null || true
  docker compose -f docker/docker-compose.infra.yml down 2>/dev/null || true

  ok "All services stopped"
}

# ─── Purge Everything ────────────────────────────────────────────────────

purge_all() {
  log "Purging containers, volumes, and cached data..."

  stop_all

  # Remove NEXUS containers
  docker rm -f nexus-kafka nexus-kafka-ui nexus-neo4j nexus-chromadb nexus-redis 2>/dev/null || true
  docker rm -f nexus-gateway nexus-ingestion nexus-parser nexus-embedding nexus-graph nexus-ai nexus-search 2>/dev/null || true

  # Remove NEXUS volumes
  docker volume rm docker_kafka_data docker_neo4j_data docker_neo4j_logs docker_chroma_data docker_redis_data 2>/dev/null || true

  # Remove network
  docker network rm nexus-network 2>/dev/null || true

  # Clear cloned repos
  rm -rf repos/ 2>/dev/null || true

  ok "Purged all containers, volumes, and data"
}

# ─── Free Ports ──────────────────────────────────────────────────────────

free_ports() {
  log "Checking required ports..."

  local PORTS=(9092 8080 7474 7687 8100 6380 8000 8001 8002 8003 8004 8005 8006 5173)

  for port in "${PORTS[@]}"; do
    local PID
    PID=$(lsof -ti ":$port" 2>/dev/null || true)
    if [ -n "$PID" ]; then
      warn "Port $port in use by PID $PID — killing"
      kill -9 "$PID" 2>/dev/null || true
      sleep 0.5
    fi
  done

  ok "All required ports are free"
}

# ─── Start Infrastructure ────────────────────────────────────────────────

start_infra() {
  log "Starting infrastructure (Kafka, Neo4j, ChromaDB, Redis)..."

  docker compose -f docker/docker-compose.infra.yml up -d

  log "Waiting for Kafka to be healthy (this takes ~30s)..."

  local MAX_WAIT=90
  local WAITED=0

  while [ $WAITED -lt $MAX_WAIT ]; do
    if docker exec nexus-kafka kafka-broker-api-versions --bootstrap-server localhost:9092 >/dev/null 2>&1; then
      ok "Kafka is healthy"
      break
    fi
    sleep 3
    WAITED=$((WAITED + 3))
    echo -ne "\r  ⏳ Waiting... ${WAITED}s / ${MAX_WAIT}s"
  done
  echo ""

  if [ $WAITED -ge $MAX_WAIT ]; then
    fail "Kafka failed to start within ${MAX_WAIT}s"
    docker logs nexus-kafka 2>&1 | tail -10
    exit 1
  fi

  # Verify other services
  for svc in nexus-neo4j nexus-chromadb nexus-redis; do
    if docker ps --format '{{.Names}}' | grep -q "$svc"; then
      ok "$svc is running"
    else
      warn "$svc may not be running"
    fi
  done
}

# ─── Create Kafka Topics ─────────────────────────────────────────────────

create_topics() {
  log "Creating Kafka topics..."

  local TOPICS=("repo.ingested:3" "file.parsed:6" "embeddings.generated:3" "graph.updated:3" "pr.analyzed:3")

  for entry in "${TOPICS[@]}"; do
    IFS=':' read -r topic partitions <<< "$entry"
    docker exec nexus-kafka kafka-topics \
      --bootstrap-server localhost:9092 \
      --create --topic "$topic" \
      --partitions "$partitions" \
      --replication-factor 1 \
      --if-not-exists 2>/dev/null && ok "$topic" || warn "$topic (may exist)"
  done
}

# ─── Install Dependencies ────────────────────────────────────────────────

install_deps() {
  log "Installing Python dependencies for all services..."

  local SERVICES=(gateway-service ingestion-service parser-service embedding-service graph-service ai-service search-service)

  for svc in "${SERVICES[@]}"; do
    if [ -f "$svc/requirements.txt" ]; then
      echo -n "  📦 $svc... "
      pip install -q -r "$svc/requirements.txt" 2>/dev/null && echo "done" || echo "failed (non-critical)"
    fi
  done

  if [ -d "frontend/node_modules" ]; then
    ok "Frontend dependencies already installed"
  else
    log "Installing frontend dependencies..."
    (cd frontend && npm install --silent 2>/dev/null)
    ok "Frontend dependencies installed"
  fi
}

# ─── Start Backend Services ──────────────────────────────────────────────

start_services() {
  log "Starting backend services locally..."

  local SERVICES=(
    "gateway-service:8000"
    "ingestion-service:8001"
    "parser-service:8002"
    "embedding-service:8003"
    "graph-service:8004"
    "ai-service:8005"
    "search-service:8006"
  )

  for entry in "${SERVICES[@]}"; do
    IFS=':' read -r svc port <<< "$entry"

    echo -n "  🚀 $svc (:$port)... "

    (cd "$svc" && \
     NEXUS_KAFKA_BOOTSTRAP_SERVERS=localhost:9092 \
     NEXUS_NEO4J_URI=bolt://localhost:7687 \
     NEXUS_NEO4J_USERNAME=neo4j \
     NEXUS_NEO4J_PASSWORD=nexus_password \
     NEXUS_CHROMA_HOST=localhost \
     NEXUS_CHROMA_PORT=8100 \
     NEXUS_REDIS_HOST=localhost \
     NEXUS_REDIS_PORT=6380 \
     NEXUS_LLM_MODEL=openrouter/qwen/qwen3-235b-a22b \
     NEXUS_LLM_API_KEY=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 \
     NEXUS_SEARCH_SERVICE_URL=http://localhost:8006 \
     NEXUS_GRAPH_SERVICE_URL=http://localhost:8004 \
     NEXUS_INGESTION_SERVICE_URL=http://localhost:8001 \
     nohup uvicorn app.main:app --host 0.0.0.0 --port "$port" \
       > "/tmp/nexus-${svc}.log" 2>&1 &)

    sleep 1
    echo "started (PID: $!)"
  done

  # Wait for services to be ready
  sleep 3
  log "Verifying services..."

  for entry in "${SERVICES[@]}"; do
    IFS=':' read -r svc port <<< "$entry"
    if curl -s -o /dev/null -w "" --connect-timeout 2 "http://localhost:$port/health" 2>/dev/null; then
      ok "$svc (:$port) healthy"
    else
      warn "$svc (:$port) still starting — check /tmp/nexus-${svc}.log"
    fi
  done
}

# ─── Start Frontend ──────────────────────────────────────────────────────

start_frontend() {
  log "Starting frontend dev server..."

  (cd frontend && VITE_API_URL=http://localhost:8000 \
    nohup npx vite --port 5173 --host 0.0.0.0 \
    > /tmp/nexus-frontend.log 2>&1 &)

  sleep 2
  ok "Frontend running at http://localhost:5173"
}

# ─── Status Check ────────────────────────────────────────────────────────

status_check() {
  echo ""
  echo -e "${BOLD}═══════════════════════════════════════════${NC}"
  echo -e "${BOLD}   NEXUS System Status${NC}"
  echo -e "${BOLD}═══════════════════════════════════════════${NC}"
  echo ""

  echo -e "${CYAN}Infrastructure:${NC}"
  for svc in nexus-kafka nexus-neo4j nexus-chromadb nexus-redis nexus-kafka-ui; do
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "$svc"; then
      ok "$svc"
    else
      fail "$svc"
    fi
  done

  echo ""
  echo -e "${CYAN}Services:${NC}"
  local PORTS=("gateway:8000" "ingestion:8001" "parser:8002" "embedding:8003" "graph:8004" "ai:8005" "search:8006")
  for entry in "${PORTS[@]}"; do
    IFS=':' read -r name port <<< "$entry"
    if curl -s -o /dev/null --connect-timeout 1 "http://localhost:$port/health" 2>/dev/null; then
      ok "$name (:$port)"
    else
      fail "$name (:$port)"
    fi
  done

  echo ""
  echo -e "${CYAN}Frontend:${NC}"
  if curl -s -o /dev/null --connect-timeout 1 "http://localhost:5173" 2>/dev/null; then
    ok "React app (:5173)"
  else
    fail "React app (:5173)"
  fi

  echo ""
  echo -e "${CYAN}Links:${NC}"
  echo "  Dashboard:  http://localhost:5173"
  echo "  Gateway:    http://localhost:8000/docs"
  echo "  Kafka UI:   http://localhost:8080"
  echo "  Neo4j:      http://localhost:7474"
  echo ""
}

# ─── Main ────────────────────────────────────────────────────────────────

case "${1:-full}" in
  full)
    echo ""
    echo -e "${BOLD}╔═══════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║   NEXUS — Full System Bootstrap           ║${NC}"
    echo -e "${BOLD}╚═══════════════════════════════════════════╝${NC}"
    echo ""
    purge_all
    free_ports
    start_infra
    create_topics
    install_deps
    start_services
    start_frontend
    status_check
    ;;
  start)
    start_infra
    create_topics
    start_services
    start_frontend
    status_check
    ;;
  stop)
    stop_all
    ;;
  status)
    status_check
    ;;
  *)
    echo "Usage: $0 {full|start|stop|status}"
    echo "  full   - Purge everything and start fresh"
    echo "  start  - Start without purging"
    echo "  stop   - Stop everything"
    echo "  status - Check system status"
    exit 1
    ;;
esac
