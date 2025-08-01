# Search Service

Semantic code search service powered by vector similarity.

## Responsibilities

- Index code embeddings for fast retrieval
- Semantic search via cosine similarity
- RAG pipeline: retrieve → augment → generate
- Expose search APIs

## Tech Stack

- Python 3.11+
- FastAPI
- ChromaDB (vector queries)
- Kafka (event consumption)

## Kafka

- **Consumes**: `embeddings.generated`

## Running

```bash
cd search-service
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8006
```
