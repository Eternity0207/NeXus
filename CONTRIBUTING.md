# Contributing to NEXUS

Thanks for taking the time to look. This doc covers the dev loop and
conventions; the big picture lives in [README.md](README.md) and the
full setup is in [Architecture.md](Architecture.md).

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker + Docker Compose
- [Caddy](https://caddyserver.com)

## Quick Start

```bash
git clone https://github.com/Eternity0207/NeXus.git
cd NeXus
cp .env.example .env
./nexus.sh               # bring everything up
```

That's it — one venv in `.venv/`, one pinned `requirements.txt`, one
Caddy config. Visit `http://nexus.localhost` for the dashboard and
`http://gateway.localhost/docs` for the API.

## Running One Service in the Foreground

Useful while debugging:

```bash
make run-gateway      # :8000
make run-ingestion    # :8001
make run-parser       # :8002
make run-embedding    # :8003
make run-graph        # :8004
make run-ai           # :8005
make run-search       # :8006
```

Tail logs from the other services with `./nexus.sh logs <service>`.

## Code Style

- **Python**: PEP 8, type hints on public surfaces, small functions.
- **JavaScript**: ESLint defaults from the Vite scaffold.
- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/)
  — `feat:`, `fix:`, `chore:`, `refactor:`, `docs:`, `test:`.

## Adding a New Service

1. Create `my-service/app/{__init__.py,config.py,main.py}`.
2. Expose a `/health` endpoint that returns 200.
3. If the service consumes Kafka, subclass
   `shared.kafka_consumer.BaseKafkaConsumer` — you get retries, dead
   letter handling, and metrics for free.
4. Add the port to `nexus.sh` (`SERVICES` array) and Makefile
   (`run-<name>`).
5. Add a subdomain rule in `infra/Caddyfile`.
6. Add a proxy route in `gateway-service/app/routes/` if the frontend
   should be able to call it.

## Adding a New Language Parser

1. Create `parser-service/app/<lang>_parser.py`.
2. Implement `BaseParser` from `parser-service/app/base.py`.
3. Register it in `parser-service/app/main.py::_register_all_parsers`.
4. Add the file extension mapping in
   `ingestion-service/app/git_ops.py::EXTENSION_LANGUAGE_MAP` so the
   ingestion step actually picks it up.

## Testing

There's no test suite yet (the backlog in Architecture.md tracks this).
`make health` is the closest thing to an integration test right now —
it curls every `/health` endpoint and pings the infra.
