# Embedding Service

Code embedding generation service using transformer models.

## Responsibilities

- Generate vector embeddings for code chunks
- Chunk code intelligently (function-level, block-level)
- Store embeddings in ChromaDB
- Produce `embeddings.generated` events to Kafka

## Tech Stack

- Python 3.11+
- sentence-transformers (embedding models)
- ChromaDB (vector storage)
- Kafka (event consumption/production)

## Kafka

- **Consumes**: `file.parsed`
- **Produces**: `embeddings.generated`

## Running

```bash
cd embedding-service
pip install -r requirements.txt
python -m app.main
```
