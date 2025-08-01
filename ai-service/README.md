# AI Service

LLM-powered analysis and intelligence service.

## Responsibilities

- Code summarization (file and repo level)
- PR review and suggestions
- Bug detection heuristics
- Codebase chat (RAG-powered Q&A)
- Produce `pr.analyzed` events to Kafka

## Tech Stack

- Python 3.11+
- FastAPI
- LiteLLM (unified LLM interface)
- Kafka (event consumption/production)

## Kafka

- **Consumes**: `graph.updated`
- **Produces**: `pr.analyzed`

## Running

```bash
cd ai-service
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8005
```
