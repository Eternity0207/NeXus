# NEXUS — Architecture & Setup Guide

This document is the technical companion to [README.md](README.md). If the
README explains *why* NEXUS exists, this one explains *how* it works and
how to run it.

---

## 1. System Overview

NEXUS is an event-driven, seven-service platform glued together by Kafka.
Each service has a single responsibility; none of them talk to each other
over shared memory or synchronous RPC except through the gateway or Kafka.

```
          ┌──────────────┐
          │   Frontend   │  React + Vite
          └──────┬───────┘
                 │
          ┌──────▼───────┐
          │   Gateway    │  FastAPI, REST fan-out + CORS + auth
          └──────┬───────┘
                 │ HTTP
    ┌────────────┼───────────────┬───────────┬───────────┐
    ▼            ▼               ▼           ▼           ▼
Ingestion    Search           AI        Graph (REST)  (admin)
    │                                       │
    └──────► Kafka topics ◄──────────────── │
                 │
       ┌─────────┼─────────┬────────────┐
       ▼         ▼         ▼            ▼
     Parser  Embedding   Graph         AI
                │         │
              Chroma    Neo4j
```

## 2. Services

| Service             | Port | Role                                                          |
|---------------------|------|---------------------------------------------------------------|
| `gateway-service`   | 8000 | REST entrypoint, CORS, request logging, global error handler  |
| `ingestion-service` | 8001 | Clone repos, walk file trees, publish `repo.ingested`         |
| `parser-service`    | 8002 | Consume `repo.ingested`, AST-parse files, emit `file.parsed`  |
| `embedding-service` | 8003 | Chunk + embed `file.parsed` → ChromaDB + `embeddings.generated` |
| `graph-service`     | 8004 | Consume `file.parsed`, build Neo4j graph, emit `graph.updated` |
| `ai-service`        | 8005 | LLM-powered summaries, PR review, RAG chat                    |
| `search-service`    | 8006 | Vector search over ChromaDB                                   |

The React dashboard runs on :5173 in dev.

## 3. Data Flow

### 3.1 Ingestion Pipeline

```
Git URL
   │
   ▼
Ingestion ── repo.ingested ──► Parser ── file.parsed ──► Embedding ── embeddings.generated ──► Search
                                         │
                                         └─────────────► Graph ── graph.updated ──► AI
```

1. **Ingestion** receives a POST, shallow-clones the repo, walks it,
   filters out `node_modules` / `.git` / etc, and publishes a
   `repo.ingested` event with the file manifest.
2. **Parser** consumes the event. For each supported file it reads the
   content, runs the language-specific parser, and publishes a
   `file.parsed` event per file.
3. **Embedding** consumes `file.parsed`. It chunks the file at semantic
   boundaries (one chunk per function, one per class summary, one file-level
   summary), runs them through a sentence-transformer, and upserts them
   into ChromaDB. It also emits `embeddings.generated` with truncated
   metadata for observability.
4. **Graph** also consumes `file.parsed` — in parallel — and MERGEs
   `File → Function/Class`, `Class-[:HAS_METHOD]->Function`,
   `Class-[:EXTENDS]->Class`, and `File-[:IMPORTS]->Module` nodes into
   Neo4j. When it's done it emits `graph.updated`.
5. **AI** consumes `graph.updated` for downstream event hooks (currently a
   placeholder) and serves REST endpoints that reach across Search and
   Graph over HTTP to build context for LLM prompts.
6. **Search** reads from ChromaDB synchronously; it doesn't consume Kafka
   events — the embedding service writes, search reads.

### 3.2 Query Pipeline

```
User ─► Gateway ─► { Search | AI | Graph | Ingestion }
```

Everything flowing from the UI goes through the gateway, which forwards to
whichever backend actually owns that route. The gateway also surfaces
every Kafka-backed long-running response as HTTP 202 + a polling endpoint
(`/api/v1/repos/{id}`).

## 4. Kafka Topics

| Topic                   | Producer           | Consumer(s)                    | Partitions |
|-------------------------|--------------------|--------------------------------|------------|
| `repo.ingested`         | ingestion-service  | parser-service                 | 3          |
| `file.parsed`           | parser-service     | embedding-service, graph-service | 6        |
| `embeddings.generated`  | embedding-service  | (observability only)           | 3          |
| `graph.updated`         | graph-service      | ai-service                     | 3          |
| `pr.analyzed`           | ai-service         | gateway-service                | 3          |

Schemas live in `shared/schemas.py` (Pydantic) and are documented below.

### `repo.ingested`
```json
{
  "event_id": "uuid",
  "timestamp": "ISO-8601",
  "repo_id": "string",
  "repo_url": "string",
  "branch": "string",
  "commit_sha": "string",
  "files": [{"path": "…", "language": "…", "size_bytes": 123}]
}
```

### `file.parsed`
```json
{
  "event_id": "uuid",
  "timestamp": "ISO-8601",
  "repo_id": "string",
  "file_path": "string",
  "language": "string",
  "functions": [{"name": "…", "start_line": 1, "end_line": 20, "params": ["…"], "docstring": "…"}],
  "classes":   [{"name": "…", "methods": ["…"], "bases": ["…"]}],
  "imports":   ["module.a", "module.b"],
  "raw_content": "…"
}
```

### `embeddings.generated`
```json
{
  "event_id": "uuid",
  "timestamp": "ISO-8601",
  "repo_id": "string",
  "file_path": "string",
  "chunks": [{"chunk_id": "…", "content": "…", "vector": [0.1, …], "metadata": {…}}]
}
```

### `graph.updated`
```json
{
  "event_id": "uuid",
  "repo_id": "string",
  "nodes_added": 10,
  "edges_added": 25,
  "node_types": {"File": 5, "Function": 3, "Class": 2}
}
```

### `pr.analyzed`
```json
{
  "event_id": "uuid",
  "repo_id": "string",
  "pr_id": "string",
  "summary": "…",
  "risk_score": 0.42,
  "suggestions": [{"file": "…", "line": 42, "severity": "warning", "message": "…"}]
}
```

## 5. Tech Stack

| Layer                 | Choice                                               | Why                                                     |
|-----------------------|------------------------------------------------------|---------------------------------------------------------|
| Services              | Python 3.11 + FastAPI + uvicorn                      | Fast, async, Pydantic models double as request schemas  |
| Message bus           | Apache Kafka (KRaft mode, no Zookeeper)              | Durable, replayable, supports consumer groups           |
| Graph DB              | Neo4j 5                                              | Mature Cypher, solid Python driver, APOC plugins        |
| Vector DB             | ChromaDB                                             | Zero-config, HTTP client, upserts with metadata filters |
| Embeddings            | `sentence-transformers/all-MiniLM-L6-v2` (384 dims)  | Good quality, runs on CPU, tiny footprint               |
| LLM                   | LiteLLM (OpenAI / Anthropic / OpenRouter / local)    | One SDK, swappable providers, mock fallback             |
| Cache                 | Redis                                                | Gateway rate limiting, session state (future)           |
| Frontend              | React 19 + Vite + React Router                       | Fast HMR, modern DX, no build config needed             |
| Reverse proxy         | Caddy                                                | Automatic HTTPS, one-line subdomain rules, tiny config  |
| Process management    | Plain Bash + `nohup` + PID files                     | No systemd coupling, easy to read, easy to kill         |
| Infra for local dev   | Docker Compose (infra only — no app containers)      | Host-independent Kafka/Neo4j/Chroma/Redis versions      |

## 6. Repository Layout

```
nexus/
├── gateway-service/        # FastAPI REST entrypoint
├── ingestion-service/      # Git clone + file manifest + Kafka producer
├── parser-service/         # AST parsing (Kafka consumer + producer)
├── embedding-service/      # Sentence-transformers + ChromaDB
├── graph-service/          # Neo4j writer + graph query API
├── ai-service/             # LLM orchestration (summaries, PRs, chat)
├── search-service/         # Chroma-backed vector search API
├── shared/                 # Cross-service config, schemas, Kafka helpers
├── frontend/               # React + Vite dashboard
├── scripts/                # create-topics.sh, health-check.sh
├── infra/
│   ├── Caddyfile           # Subdomain routing, local + prod
│   └── docker-compose.yml  # Kafka, Neo4j, ChromaDB, Redis
├── docs/architecture.md    # Deeper Kafka schema notes
├── nexus.sh                # One-shot bootstrap / start / stop / status
├── Makefile                # Shorthand for nexus.sh + dev tasks
├── requirements.txt        # One pinned set of deps for all services
├── CONTRIBUTING.md
├── LICENSE
├── README.md               # The "why"
└── Architecture.md         # This file — the "how"
```

## 7. Prerequisites

- Linux/macOS host (tested on Arch)
- Python **3.11+**
- Node.js **20+** and npm
- Docker + Docker Compose
- [Caddy](https://caddyserver.com) — `pacman -S caddy` on Arch,
  `brew install caddy` on macOS
- `curl`, `lsof`, `nc` in PATH for health checks

## 8. Setup (local dev)

```bash
git clone https://github.com/Eternity0207/NeXus.git
cd NeXus
cp .env.example .env              # adjust NEXUS_LLM_API_KEY if you want real LLM
./nexus.sh                         # purges, installs, starts everything
open http://nexus.localhost        # React dashboard
open http://gateway.localhost/docs # FastAPI swagger
```

That one script:

1. Stops anything already running.
2. Creates `.venv/` and installs `requirements.txt`.
3. Starts Kafka, Neo4j, ChromaDB, Redis via `infra/docker-compose.yml`.
4. Creates the five Kafka topics.
5. Launches every service on 127.0.0.1 with `nohup uvicorn …`.
6. Starts the React dev server.
7. Starts Caddy with `infra/Caddyfile` to expose `*.localhost`.

### Useful follow-ups

```bash
./nexus.sh status             # quick health summary
./nexus.sh logs gateway-service
./nexus.sh stop               # kill everything
make health                   # scripts/health-check.sh
make run-gateway              # run a single service in the foreground
```

### Environment variables

Every variable is `NEXUS_*` prefixed. See [.env.example](.env.example) for
the full list. Two worth calling out:

- `NEXUS_LLM_API_KEY` — blank = mock mode (no network), otherwise any
  LiteLLM-supported key (OpenAI, Anthropic, OpenRouter, …).
- `NEXUS_DOMAIN` — defaults to `localhost`. Set to your apex domain when
  deploying to a VPS; Caddy will serve `nexus.$NEXUS_DOMAIN`,
  `gateway.$NEXUS_DOMAIN`, etc.

## 9. Running on a VPS

You can host NEXUS on any small VPS (1 vCPU, 2 GB RAM is fine for small
repos). There's no Kubernetes, no service containers to push — just the
same four infra containers plus native Python processes.

```bash
# On the server
sudo apt install -y python3-venv python3-pip nodejs npm docker.io docker-compose-plugin caddy

git clone https://github.com/Eternity0207/NeXus.git /opt/nexus
cd /opt/nexus
cp .env.example .env
# Edit .env:
#   NEXUS_DOMAIN=example.com
#   NEXUS_LLM_API_KEY=sk-...
./nexus.sh start
```

Point DNS at the server:

```
A   example.com.      → <server ip>
A   *.example.com.    → <server ip>
```

Caddy automatically provisions Let's Encrypt certificates for every
subdomain on first request. The `infra/Caddyfile` already reads
`{$NEXUS_DOMAIN}` so no config edit is needed — `nexus.example.com`,
`gateway.example.com`, `graph.example.com`, etc will all work.

For free-tier hosts (Cloudflare Tunnel, ngrok, Railway) the same Caddyfile
works — just expose port 443 to the public and let your provider handle
the tunnel.

## 10. Observability & Debugging

- Every service logs JSON to stdout (see `shared/logging_config.py`).
- `./nexus.sh logs <service>` tails the log for that service.
- `http://kafka.localhost` — Kafka UI (topic browser, consumer lag).
- `http://neo4j.localhost` — Neo4j Browser for Cypher queries.
- `make health` — curls every `/health` endpoint.

## 11. Pipeline Guarantees

- **At-least-once** delivery: consumers auto-commit after successful
  handling. The `BaseKafkaConsumer` in `shared/kafka_consumer.py` retries
  with exponential backoff (2s, 4s, 8s) up to three times and logs dead
  letters when every attempt fails.
- **Idempotent writes**: `graph-service` uses `MERGE` everywhere so
  re-processing an event doesn't create duplicates. ChromaDB upserts are
  keyed on deterministic chunk IDs — re-embedding overwrites.
- **No message ordering across files**: `file.parsed` events are keyed by
  `{repo_id}:{file_path}` so all events for the same file land on the same
  partition, but cross-file ordering is deliberately unordered.

## 12. Design Decisions

- **Regex JS/TS parser, not tree-sitter.** Tree-sitter is more accurate
  but the native bindings are a maintenance headache. Regex handles 95 %
  of real-world code and has zero install cost.
- **No service-level Docker.** Every service is a small FastAPI app; the
  overhead of a Dockerfile per service wasn't earning anything. A Python
  virtualenv + Caddy gives me the same deployment story with half the
  moving parts.
- **Mock LLM fallback.** I wanted to develop end-to-end without spending
  API credits. `ai-service` returns structured canned answers when
  `NEXUS_LLM_API_KEY` is blank; swap the key in and real LLM responses
  flow through unchanged.
- **ChromaDB over Pinecone/Qdrant.** Chroma runs in a single container
  with zero config; Pinecone is hosted-only and Qdrant's Python API was
  less mature at the time I started.
- **Neo4j over ArangoDB/Dgraph.** Cypher is the most readable graph
  query language I've used, and APOC has the algorithms I needed for
  future work (centrality, weakly connected components).

## 13. Backlog

- Real PR diff ingestion (fetch from GitHub API by PR URL).
- Tree-sitter optional backend behind a feature flag.
- More languages: Go, Rust, Java, Ruby.
- Authentication at the gateway (currently open).
- Per-repo Chroma collections to enable multi-tenant deployments.
- Prometheus metrics endpoint on each service.

## 14. Related Documents

- [docs/architecture.md](docs/architecture.md) — deeper Kafka schema notes
- [CONTRIBUTING.md](CONTRIBUTING.md) — development loop, code style
- [README.md](README.md) — project story and motivation
