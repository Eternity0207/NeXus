# ═══════════════════════════════════════════════════════════════════════════
# NEXUS Makefile — Development workflow commands
# ═══════════════════════════════════════════════════════════════════════════

.PHONY: help infra infra-down services services-down frontend dev health topics clean

# Default
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Infrastructure ──────────────────────────────────────────────────────

infra: ## Start infrastructure (Kafka, Neo4j, ChromaDB, Redis)
	docker compose -f docker/docker-compose.infra.yml up -d
	@echo "⏳ Waiting for services to be ready..."
	@sleep 10
	@echo "✅ Infrastructure started"

infra-down: ## Stop infrastructure
	docker compose -f docker/docker-compose.infra.yml down

# ─── Services ────────────────────────────────────────────────────────────

services: ## Start all backend services
	docker compose -f docker/docker-compose.services.yml up -d --build

services-down: ## Stop all backend services
	docker compose -f docker/docker-compose.services.yml down

# ─── Frontend ────────────────────────────────────────────────────────────

frontend: ## Start frontend dev server
	cd frontend && npm run dev

frontend-build: ## Build frontend for production
	cd frontend && npm run build

# ─── Development ─────────────────────────────────────────────────────────

dev: infra ## Start infra + create topics (dev mode)
	@sleep 5
	@bash scripts/create-topics.sh 2>/dev/null || true
	@echo ""
	@echo "🚀 Infrastructure ready. Start services individually:"
	@echo "   cd gateway-service && uvicorn app.main:app --port 8000 --reload"
	@echo "   cd ingestion-service && uvicorn app.main:app --port 8001 --reload"
	@echo "   cd parser-service && uvicorn app.main:app --port 8002 --reload"
	@echo "   cd frontend && npm run dev"

topics: ## Create Kafka topics
	bash scripts/create-topics.sh

health: ## Check all service health
	bash scripts/health-check.sh

# ─── Cleanup ─────────────────────────────────────────────────────────────

clean: infra-down services-down ## Stop everything and clean up
	docker volume prune -f
	rm -rf repos/
	@echo "🧹 Cleaned up"

# ─── Individual Services ─────────────────────────────────────────────────

run-gateway: ## Run gateway service locally
	cd gateway-service && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

run-ingestion: ## Run ingestion service locally
	cd ingestion-service && uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

run-parser: ## Run parser service locally
	cd parser-service && uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload

run-embedding: ## Run embedding service locally
	cd embedding-service && uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload

run-graph: ## Run graph service locally
	cd graph-service && uvicorn app.main:app --host 0.0.0.0 --port 8004 --reload

run-ai: ## Run AI service locally
	cd ai-service && uvicorn app.main:app --host 0.0.0.0 --port 8005 --reload

run-search: ## Run search service locally
	cd search-service && uvicorn app.main:app --host 0.0.0.0 --port 8006 --reload
