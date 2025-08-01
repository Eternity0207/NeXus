# Graph Service

Dependency graph construction and query service.

## Responsibilities

- Build file-level and function-level dependency graphs
- Store graph data in Neo4j
- Provide REST APIs for graph queries
- Produce `graph.updated` events to Kafka

## Tech Stack

- Python 3.11+
- FastAPI (query API)
- neo4j (Python driver)
- Kafka (event consumption/production)

## Kafka

- **Consumes**: `file.parsed`
- **Produces**: `graph.updated`

## Running

```bash
cd graph-service
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8004
```
