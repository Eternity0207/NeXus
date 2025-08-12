# Contributing to NEXUS

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose

### Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/Eternity0207/NeXus.git
cd NeXus

# 2. Copy environment configuration
cp .env.example .env

# 3. Start infrastructure
make infra

# 4. Create Kafka topics
make topics

# 5. Install service dependencies (each service has its own venv)
cd gateway-service && pip install -r requirements.txt && cd ..
cd ingestion-service && pip install -r requirements.txt && cd ..
# ... repeat for each service

# 6. Start services
make run-gateway    # terminal 1
make run-ingestion  # terminal 2
make run-parser     # terminal 3
# ... etc

# 7. Start frontend
cd frontend && npm install && npm run dev
```

## Architecture

See [docs/architecture.md](docs/architecture.md) for the full system design.

## Code Style

- **Python**: PEP 8, type hints, docstrings on public functions
- **JavaScript**: ESLint defaults from Vite scaffold
- **Commits**: Conventional Commits format (`feat:`, `fix:`, `chore:`, `refactor:`)

## Adding a New Service

1. Create a new directory: `my-service/`
2. Add `app/__init__.py`, `app/config.py`, `app/main.py`
3. Add health check endpoint at `/health`
4. Add `requirements.txt`, `Dockerfile`, `README.md`
5. If consuming Kafka, extend `shared.kafka_consumer.BaseKafkaConsumer`
6. Add service to `docker/docker-compose.services.yml`
7. Add proxy route in `gateway-service/app/routes/`

## Adding a New Language Parser

1. Create `parser-service/app/<lang>_parser.py`
2. Implement `BaseParser` interface from `app/base.py`
3. Register in `parser-service/app/main.py`
4. Add extension mapping in `ingestion-service/app/git_ops.py`

## Testing

```bash
# Run service-specific tests (when added)
cd gateway-service && pytest

# Health check all services
make health
```
