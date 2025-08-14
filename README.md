# NEXUS — Neural Execution & Understanding System

[![Architecture](https://img.shields.io/badge/architecture-microservices-blue)]()
[![Pipeline](https://img.shields.io/badge/pipeline-kafka-orange)]()
[![AI](https://img.shields.io/badge/ai-RAG%20%2B%20LLM-purple)]()
[![Graph](https://img.shields.io/badge/graph-neo4j-green)]()

> An AI-powered codebase intelligence platform that understands, indexes, and reasons about your code at scale.

## Overview

NEXUS is a production-grade platform that ingests source code repositories, builds semantic understanding through embeddings and graph analysis, and provides intelligent insights via LLM-powered interfaces.

### What It Does

- **Ingests** repositories and watches for changes
- **Parses** code into ASTs, extracts functions, classes, and dependencies
- **Embeds** code semantically using transformer models
- **Graphs** dependency relationships at file and function level (Neo4j)
- **Searches** code semantically using vector similarity (RAG)
- **Analyzes** PRs, detects bugs, and summarizes codebases with AI
- **Visualizes** everything through a modern React dashboard

## Architecture

```
┌─────────────┐     ┌──────────────────────────────────────────────────┐
│   Frontend   │────▶│              Gateway Service (API)               │
│  (React App) │◀────│         REST API · Auth · Rate Limiting          │
└─────────────┘     └──────────┬───────────────────────────────────────┘
                               │
                    ┌──────────▼───────────────────────────────────────┐
                    │              Apache Kafka (Event Bus)             │
                    │  Topics: repo.ingested │ file.parsed │ ...       │
                    └──┬──────┬──────┬──────┬──────┬──────┬───────────┘
                       │      │      │      │      │      │
                  ┌────▼─┐┌──▼───┐┌─▼────┐┌▼─────┐┌▼────┐┌▼──────┐
                  │Ingest││Parser││Embed ││Graph ││  AI ││Search │
                  │ Svc  ││ Svc  ││ Svc  ││ Svc  ││ Svc ││  Svc  │
                  └──────┘└──────┘└──────┘└──────┘└─────┘└───────┘
                                     │       │
                              ┌──────▼─┐ ┌───▼────┐
                              │ChromaDB│ │  Neo4j │
                              │(Vector)│ │(Graph) │
                              └────────┘ └────────┘
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| `gateway-service` | 8000 | API gateway, routing, auth, rate limiting |
| `ingestion-service` | 8001 | Repository cloning, file extraction, change detection |
| `parser-service` | 8002 | AST parsing, function/class extraction, dependency mapping |
| `embedding-service` | 8003 | Code embedding generation via transformer models |
| `graph-service` | 8004 | Neo4j graph construction and query APIs |
| `ai-service` | 8005 | LLM integration, summarization, PR review, chat |
| `search-service` | 8006 | Semantic search, RAG pipeline |
| `frontend` | 3000 | React dashboard |

## Kafka Topics

| Topic | Producer | Consumer(s) | Payload |
|-------|----------|-------------|---------|
| `repo.ingested` | ingestion-service | parser-service | `{repo_id, repo_url, files[]}` |
| `file.parsed` | parser-service | embedding-service, graph-service | `{repo_id, file_path, ast, functions[], imports[]}` |
| `embeddings.generated` | embedding-service | search-service | `{repo_id, file_path, vectors[]}` |
| `graph.updated` | graph-service | ai-service | `{repo_id, nodes_added, edges_added}` |
| `pr.analyzed` | ai-service | gateway-service | `{repo_id, pr_id, review, suggestions[]}` |

## Tech Stack

- **Language**: Python 3.11+ (services), TypeScript (frontend)
- **Framework**: FastAPI (REST APIs)
- **Message Broker**: Apache Kafka
- **Graph DB**: Neo4j
- **Vector DB**: ChromaDB
- **LLM**: OpenAI GPT-4 / local models via LiteLLM
- **Frontend**: React + Vite
- **Containerization**: Docker + Docker Compose

## Quick Start

```bash
# 1. Clone and configure
git clone https://github.com/Eternity0207/NeXus.git
cd NeXus
cp .env.example .env

# 2. Start infrastructure (Kafka, Neo4j, ChromaDB, Redis)
make infra

# 3. Create Kafka topics
make topics

# 4. Start all services (Docker)
make services

# 5. Start frontend
cd frontend && npm install && npm run dev
```

### Development Mode

```bash
# Run services individually with hot-reload
make run-gateway      # :8000
make run-ingestion    # :8001
make run-parser       # :8002
make run-embedding    # :8003
make run-graph        # :8004
make run-ai           # :8005
make run-search       # :8006

# Check health of all services
make health
```

## Project Structure

```
nexus/
├── gateway-service/         # API gateway, routing, rate limiting
├── ingestion-service/       # Repository cloning, file extraction
├── parser-service/          # AST parsing (Python, JS/TS)
├── embedding-service/       # Vector generation, ChromaDB storage
├── graph-service/           # Neo4j graph builder and query APIs
├── ai-service/              # LLM integration, PR review, chat
├── search-service/          # Semantic code search (RAG)
├── frontend/                # React + Vite dashboard
├── shared/                  # Kafka utilities, schemas, base consumer
├── scripts/                 # Kafka topics, health checks
├── docker/                  # Infrastructure & services compose
├── docs/                    # Architecture documentation
├── Makefile                 # Development workflow commands
├── .env.example             # Environment configuration template
├── CONTRIBUTING.md          # Development guide
└── LICENSE                  # MIT License
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and extension guides.

## License

MIT — see [LICENSE](LICENSE) for details.
