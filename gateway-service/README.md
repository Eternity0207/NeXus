# Gateway Service

API gateway and request router for the NEXUS platform.

## Responsibilities

- REST API entrypoint for all client requests
- Authentication and authorization (JWT)
- Rate limiting and request validation
- Request routing to internal services
- WebSocket support for real-time updates

## Tech Stack

- Python 3.11+
- FastAPI
- Redis (rate limiting cache)

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/repos` | Ingest a new repository |
| GET | `/api/v1/repos/{id}` | Get repository details |
| POST | `/api/v1/search` | Semantic code search |
| POST | `/api/v1/chat` | AI chat with codebase |
| GET | `/api/v1/graph/{repo_id}` | Query dependency graph |
| POST | `/api/v1/pr/analyze` | Analyze a pull request |
| GET | `/health` | Health check |

## Running

```bash
cd gateway-service
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka broker address |
| `REDIS_HOST` | `localhost` | Redis host |
| `JWT_SECRET` | — | JWT signing secret |
