# Ingestion Service

Repository ingestion and file extraction service.

## Responsibilities

- Clone Git repositories (public and private)
- Extract file trees with metadata
- Detect supported languages
- Produce `repo.ingested` events to Kafka
- Track repository state for incremental updates

## Tech Stack

- Python 3.11+
- FastAPI (trigger API)
- GitPython (repository operations)
- Kafka (event production)

## Kafka

- **Produces**: `repo.ingested`

## Running

```bash
cd ingestion-service
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001
```
