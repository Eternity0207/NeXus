# NEXUS Architecture Document

## 1. System Overview

NEXUS is an event-driven microservices platform for AI-powered codebase intelligence. The system ingests source code, builds multi-dimensional understanding (semantic, structural, relational), and serves intelligent insights through a unified API gateway.

## 2. Data Flow

### 2.1 Ingestion Pipeline

```
Repository URL
      │
      ▼
┌─────────────────┐     repo.ingested      ┌──────────────┐
│ Ingestion Svc   │ ──────────────────────▶ │  Parser Svc  │
│ Clone + Extract │                         │  AST + Deps  │
└─────────────────┘                         └──────┬───────┘
                                                   │
                                            file.parsed
                                                   │
                              ┌────────────────────┼────────────────────┐
                              ▼                                         ▼
                    ┌──────────────────┐                      ┌──────────────────┐
                    │  Embedding Svc   │                      │   Graph Svc      │
                    │  Vector Gen      │                      │   Neo4j Build    │
                    └────────┬─────────┘                      └────────┬─────────┘
                             │                                         │
                    embeddings.generated                        graph.updated
                             │                                         │
                             ▼                                         ▼
                    ┌──────────────────┐                      ┌──────────────────┐
                    │  Search Svc      │                      │   AI Svc         │
                    │  Index + Query   │                      │   Analysis       │
                    └──────────────────┘                      └──────────────────┘
```

### 2.2 Query Pipeline

```
User Request
      │
      ▼
┌─────────────────┐
│  Gateway Svc    │
│  Route + Auth   │
└────────┬────────┘
         │
    ┌────┼────┬────────┬──────────┐
    ▼    ▼    ▼        ▼          ▼
 Search  AI  Graph  Ingestion  Parser
  Svc   Svc  Svc     Svc        Svc
```

## 3. Service Contracts

### 3.1 Gateway Service
- **Role**: API entrypoint, authentication, rate limiting, request routing
- **Protocol**: REST (HTTP/JSON)
- **Upstream**: All internal services
- **Produces**: None (synchronous routing)
- **Consumes**: `pr.analyzed` (webhook delivery)

### 3.2 Ingestion Service
- **Role**: Clone repositories, extract file trees, detect changes
- **Protocol**: REST (triggered by gateway), Kafka (produces events)
- **Produces**: `repo.ingested`
- **Consumes**: None
- **Storage**: Local filesystem (cloned repos)

### 3.3 Parser Service
- **Role**: Parse source files into ASTs, extract functions, classes, imports
- **Protocol**: Kafka consumer/producer
- **Produces**: `file.parsed`
- **Consumes**: `repo.ingested`
- **Supported Languages**: Python, JavaScript, TypeScript (extensible)

### 3.4 Embedding Service
- **Role**: Generate vector embeddings for code chunks
- **Protocol**: Kafka consumer/producer
- **Produces**: `embeddings.generated`
- **Consumes**: `file.parsed`
- **Model**: sentence-transformers/code-search (configurable)
- **Storage**: ChromaDB

### 3.5 Graph Service
- **Role**: Build and query dependency graphs
- **Protocol**: Kafka consumer, REST API for queries
- **Produces**: `graph.updated`
- **Consumes**: `file.parsed`
- **Storage**: Neo4j

### 3.6 AI Service
- **Role**: LLM-powered analysis — summarization, PR review, chat, bug detection
- **Protocol**: REST API, Kafka consumer
- **Produces**: `pr.analyzed`
- **Consumes**: `graph.updated`
- **LLM**: OpenAI GPT-4 / LiteLLM (configurable)

### 3.7 Search Service
- **Role**: Semantic code search using vector similarity (RAG)
- **Protocol**: REST API, Kafka consumer
- **Produces**: None
- **Consumes**: `embeddings.generated`
- **Storage**: ChromaDB

## 4. Kafka Topic Schema

### `repo.ingested`
```json
{
  "event_id": "uuid",
  "timestamp": "ISO-8601",
  "repo_id": "string",
  "repo_url": "string",
  "branch": "string",
  "commit_sha": "string",
  "files": [
    {
      "path": "string",
      "language": "string",
      "size_bytes": 1234
    }
  ]
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
  "functions": [
    {
      "name": "string",
      "start_line": 1,
      "end_line": 20,
      "params": ["string"],
      "docstring": "string"
    }
  ],
  "classes": [
    {
      "name": "string",
      "methods": ["string"],
      "bases": ["string"]
    }
  ],
  "imports": ["string"],
  "raw_content": "string"
}
```

### `embeddings.generated`
```json
{
  "event_id": "uuid",
  "timestamp": "ISO-8601",
  "repo_id": "string",
  "file_path": "string",
  "chunks": [
    {
      "chunk_id": "string",
      "content": "string",
      "vector": [0.1, 0.2, ...],
      "metadata": {
        "function_name": "string",
        "start_line": 1,
        "end_line": 20
      }
    }
  ]
}
```

### `graph.updated`
```json
{
  "event_id": "uuid",
  "timestamp": "ISO-8601",
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
  "timestamp": "ISO-8601",
  "repo_id": "string",
  "pr_id": "string",
  "summary": "string",
  "risk_score": 0.75,
  "suggestions": [
    {
      "file": "string",
      "line": 42,
      "severity": "warning",
      "message": "string"
    }
  ]
}
```

## 5. Infrastructure

| Component | Image | Port |
|-----------|-------|------|
| Kafka (KRaft) | confluentinc/cp-kafka:7.5.0 | 9092 |
| Neo4j | neo4j:5.12 | 7474, 7687 |
| ChromaDB | chromadb/chroma:latest | 8100 |
| Redis (cache) | redis:7-alpine | 6379 |

## 6. Non-Functional Requirements

- **Scalability**: Each service scales independently via container replicas
- **Observability**: Structured JSON logging, Prometheus metrics, health endpoints
- **Resilience**: Kafka consumer retries, dead letter queues, circuit breakers
- **Security**: JWT auth at gateway, service-to-service mTLS (production)
- **Performance**: Sub-200ms API response times, async processing via Kafka
