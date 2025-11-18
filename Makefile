# ═══════════════════════════════════════════════════════════════════════════
# NEXUS Makefile — thin wrapper around nexus.sh plus dev shortcuts
# ═══════════════════════════════════════════════════════════════════════════

.PHONY: help up down status logs clean infra infra-down topics health \
        caddy frontend install \
        run-gateway run-ingestion run-parser run-embedding run-graph run-ai run-search

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ─── Full system ─────────────────────────────────────────────────────────

up: ## Start the entire platform (infra + services + frontend + caddy)
	./nexus.sh start

down: ## Stop everything
	./nexus.sh stop

status: ## Check system health
	./nexus.sh status

logs: ## Tail logs — make logs svc=gateway-service
	./nexus.sh logs $(svc)

clean: ## Purge containers, volumes, logs, cloned repos
	./nexus.sh stop
	rm -rf repos/ data/ .logs/ .pids/
	docker volume prune -f

# ─── Infrastructure only ─────────────────────────────────────────────────

infra: ## Start Kafka, Neo4j, ChromaDB, Redis
	docker compose -f infra/docker-compose.yml up -d
	@sleep 10
	@bash scripts/create-topics.sh

infra-down: ## Stop infra containers
	docker compose -f infra/docker-compose.yml down

topics: ## (Re)create Kafka topics
	bash scripts/create-topics.sh

health: ## Curl each service's /health endpoint
	bash scripts/health-check.sh

# ─── Dependencies ────────────────────────────────────────────────────────

install: ## Install Python and frontend dependencies
	python3 -m venv .venv
	.venv/bin/pip install -U pip
	.venv/bin/pip install -r requirements.txt
	cd frontend && npm install

# ─── Caddy ───────────────────────────────────────────────────────────────

caddy: ## Run Caddy in the foreground (subdomain routing)
	caddy run --config infra/Caddyfile --adapter caddyfile

# ─── Frontend ────────────────────────────────────────────────────────────

frontend: ## Start the frontend dev server
	cd frontend && npm run dev

# ─── Individual services (foreground, great for debugging) ───────────────

run-gateway:    ## Run gateway-service on :8000
	cd gateway-service && ../.venv/bin/uvicorn app.main:app --port 8000 --reload
run-ingestion:  ## Run ingestion-service on :8001
	cd ingestion-service && ../.venv/bin/uvicorn app.main:app --port 8001 --reload
run-parser:     ## Run parser-service on :8002
	cd parser-service && ../.venv/bin/uvicorn app.main:app --port 8002 --reload
run-embedding:  ## Run embedding-service on :8003
	cd embedding-service && ../.venv/bin/uvicorn app.main:app --port 8003 --reload
run-graph:      ## Run graph-service on :8004
	cd graph-service && ../.venv/bin/uvicorn app.main:app --port 8004 --reload
run-ai:         ## Run ai-service on :8005
	cd ai-service && ../.venv/bin/uvicorn app.main:app --port 8005 --reload
run-search:     ## Run search-service on :8006
	cd search-service && ../.venv/bin/uvicorn app.main:app --port 8006 --reload
