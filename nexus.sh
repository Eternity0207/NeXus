#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# NEXUS — System Bootstrap
#
# Starts the whole platform natively on the host machine. Only the four
# stateful infra services (Kafka, Neo4j, ChromaDB, Redis) run in Docker;
# every NEXUS service is a plain Python process and Caddy exposes them on
# *.localhost subdomains.
#
#   ./nexus.sh            # purge + start everything
#   ./nexus.sh start      # start without purging (reuses infra volumes)
#   ./nexus.sh stop       # stop everything
#   ./nexus.sh status     # health summary
#   ./nexus.sh logs <svc> # tail a service's log
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

LOG_DIR="${SCRIPT_DIR}/.logs"
PID_DIR="${SCRIPT_DIR}/.pids"
VENV_DIR="${SCRIPT_DIR}/.venv"
mkdir -p "$LOG_DIR" "$PID_DIR"

log()   { echo -e "${CYAN}[NEXUS]${NC} $1"; }
ok()    { echo -e "${GREEN}  ✅ $1${NC}"; }
warn()  { echo -e "${YELLOW}  ⚠️  $1${NC}"; }
fail()  { echo -e "${RED}  ❌ $1${NC}"; }

SERVICES=(
  "gateway-service:8000"
  "ingestion-service:8001"
  "parser-service:8002"
  "embedding-service:8003"
  "graph-service:8004"
  "ai-service:8005"
  "search-service:8006"
)

# ─── Helpers ─────────────────────────────────────────────────────────────

load_env() {
  if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
  fi
}

ensure_venv() {
  if [ ! -d "$VENV_DIR" ]; then
    log "Creating Python virtualenv at .venv"
    python3 -m venv "$VENV_DIR"
  fi
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
}

install_deps() {
  ensure_venv
  log "Installing Python dependencies (this is cached in .venv)..."
  pip install --quiet --upgrade pip
  pip install --quiet -r requirements.txt

  if [ ! -d "frontend/node_modules" ]; then
    log "Installing frontend dependencies..."
    (cd frontend && npm install --silent)
  fi
  ok "Dependencies ready"
}

# ─── Lifecycle ───────────────────────────────────────────────────────────

stop_all() {
  log "Stopping NEXUS..."

  for entry in "${SERVICES[@]}"; do
    svc="${entry%%:*}"
    pidfile="$PID_DIR/$svc.pid"
    if [ -f "$pidfile" ]; then
      pid=$(cat "$pidfile")
      kill "$pid" 2>/dev/null || true
      rm -f "$pidfile"
    fi
  done

  # Frontend + Caddy
  [ -f "$PID_DIR/frontend.pid" ] && kill "$(cat "$PID_DIR/frontend.pid")" 2>/dev/null || true
  [ -f "$PID_DIR/caddy.pid" ] && kill "$(cat "$PID_DIR/caddy.pid")" 2>/dev/null || true
  rm -f "$PID_DIR"/*.pid

  # Nuke any stragglers on known ports
  pkill -f "uvicorn app.main" 2>/dev/null || true
  pkill -f "vite.*5173" 2>/dev/null || true

  docker compose -f infra/docker-compose.yml down 2>/dev/null || true
  ok "Stopped"
}

purge_all() {
  log "Purging containers, volumes, and cached data..."
  stop_all
  docker volume rm infra_kafka_data infra_neo4j_data infra_neo4j_logs infra_chroma_data infra_redis_data 2>/dev/null || true
  docker network rm nexus-network 2>/dev/null || true
  rm -rf repos/ data/ "$LOG_DIR" "$PID_DIR"
  mkdir -p "$LOG_DIR" "$PID_DIR"
  ok "Purged"
}

start_infra() {
  log "Starting infrastructure (Kafka, Neo4j, ChromaDB, Redis)..."
  docker compose -f infra/docker-compose.yml up -d

  log "Waiting for Kafka to be ready..."
  local MAX_WAIT=90
  local WAITED=0
  while [ $WAITED -lt $MAX_WAIT ]; do
    if docker exec nexus-kafka kafka-broker-api-versions --bootstrap-server localhost:9092 >/dev/null 2>&1; then
      ok "Kafka is healthy"
      break
    fi
    sleep 3
    WAITED=$((WAITED + 3))
    printf "\r  ⏳ Waiting... %ds / %ds" "$WAITED" "$MAX_WAIT"
  done
  echo ""

  if [ $WAITED -ge $MAX_WAIT ]; then
    fail "Kafka failed to start"
    docker logs nexus-kafka 2>&1 | tail -20
    exit 1
  fi

  bash scripts/create-topics.sh >/dev/null
  ok "Topics created"
}

start_services() {
  log "Starting NEXUS services..."
  load_env
  ensure_venv

  for entry in "${SERVICES[@]}"; do
    svc="${entry%%:*}"
    port="${entry##*:}"
    logfile="$LOG_DIR/$svc.log"
    pidfile="$PID_DIR/$svc.pid"

    (
      cd "$svc"
      PYTHONPATH="$SCRIPT_DIR" \
      nohup "$VENV_DIR/bin/uvicorn" app.main:app \
        --host 127.0.0.1 --port "$port" \
        > "$logfile" 2>&1 &
      echo $! > "$pidfile"
    )
    ok "$svc → http://${svc%-service}.localhost (pid $(cat "$pidfile"))"
  done

  sleep 3
  log "Verifying health..."
  for entry in "${SERVICES[@]}"; do
    svc="${entry%%:*}"
    port="${entry##*:}"
    if curl -fsS --max-time 2 "http://127.0.0.1:$port/health" >/dev/null 2>&1; then
      ok "$svc healthy"
    else
      warn "$svc still starting — tail .logs/$svc.log"
    fi
  done
}

start_frontend() {
  log "Starting frontend..."
  (
    cd frontend
    nohup npx vite --port 5173 --host 127.0.0.1 \
      > "$LOG_DIR/frontend.log" 2>&1 &
    echo $! > "$PID_DIR/frontend.pid"
  )
  sleep 2
  ok "Frontend running on :5173"
}

start_caddy() {
  if ! command -v caddy >/dev/null 2>&1; then
    warn "caddy not found on PATH. Install it (pacman -S caddy) and rerun — services are still reachable on localhost:<port>."
    return
  fi
  log "Starting Caddy reverse proxy..."
  nohup caddy run --config infra/Caddyfile --adapter caddyfile \
    > "$LOG_DIR/caddy.log" 2>&1 &
  echo $! > "$PID_DIR/caddy.pid"
  sleep 1
  ok "Caddy serving *.localhost subdomains"
}

status_check() {
  echo ""
  echo -e "${BOLD}═══════════════════════════════════════════${NC}"
  echo -e "${BOLD}   NEXUS System Status${NC}"
  echo -e "${BOLD}═══════════════════════════════════════════${NC}"

  echo ""
  echo -e "${CYAN}Infrastructure:${NC}"
  for svc in nexus-kafka nexus-neo4j nexus-chromadb nexus-redis; do
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^$svc$"; then
      ok "$svc"
    else
      fail "$svc"
    fi
  done

  echo ""
  echo -e "${CYAN}Services:${NC}"
  for entry in "${SERVICES[@]}"; do
    svc="${entry%%:*}"
    port="${entry##*:}"
    if curl -fsS --max-time 1 "http://127.0.0.1:$port/health" >/dev/null 2>&1; then
      ok "$svc (:$port)"
    else
      fail "$svc (:$port)"
    fi
  done

  echo ""
  echo -e "${CYAN}Subdomains (requires Caddy):${NC}"
  echo "  Dashboard:   http://nexus.localhost"
  echo "  API:         http://gateway.localhost"
  echo "  Graph API:   http://graph.localhost"
  echo "  Search API:  http://search.localhost"
  echo "  Kafka UI:    http://kafka.localhost"
  echo "  Neo4j UI:    http://neo4j.localhost"
  echo ""
}

tail_logs() {
  local svc="${1:-}"
  if [ -z "$svc" ]; then
    log "Available logs:"
    ls "$LOG_DIR" 2>/dev/null | sed 's/^/  /'
    return
  fi
  tail -f "$LOG_DIR/$svc.log"
}

# ─── Main ────────────────────────────────────────────────────────────────

case "${1:-full}" in
  full)
    echo -e "${BOLD}╔═══════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║   NEXUS — Full Bootstrap                  ║${NC}"
    echo -e "${BOLD}╚═══════════════════════════════════════════╝${NC}"
    purge_all
    install_deps
    start_infra
    start_services
    start_frontend
    start_caddy
    status_check
    ;;
  start)
    install_deps
    start_infra
    start_services
    start_frontend
    start_caddy
    status_check
    ;;
  stop) stop_all ;;
  status) status_check ;;
  logs) tail_logs "${2:-}" ;;
  *)
    echo "Usage: $0 {full|start|stop|status|logs [service]}"
    exit 1
    ;;
esac
