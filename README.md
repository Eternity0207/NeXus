# NEXUS — Neural Execution & Understanding System

> An AI-powered codebase intelligence platform that reads, indexes, graphs,
> and reasons about source code at scale.

[![Architecture](https://img.shields.io/badge/architecture-microservices-blue)]()
[![Pipeline](https://img.shields.io/badge/pipeline-kafka-orange)]()
[![AI](https://img.shields.io/badge/ai-RAG%20%2B%20LLM-purple)]()
[![Graph](https://img.shields.io/badge/graph-neo4j-green)]()
[![License](https://img.shields.io/badge/license-MIT-informational)]()

---

## Why I Built This

Every time I joined a new codebase — internship, side project, even my own
repos six months later — the same painful ritual repeated itself:

1. `grep` for keywords until something vaguely relevant showed up.
2. Follow imports manually to piece together how the code actually fit
   together.
3. Ask a teammate (or past-me) what a specific function was for, because the
   comments had long since drifted from reality.
4. Eventually give up and read files top-to-bottom, taking notes.

Tools like GitHub search and IDE go-to-definition help a bit, but they only
understand *syntax*. They don't understand *meaning*. They can't tell you
"show me the code that handles retry logic for failed payments" — they can
only tell you where the string "retry" appears.

I wanted something that read a repository the way a senior engineer reads a
repository — by building a mental model of the pieces, the relationships
between them, and what each piece is trying to achieve. NEXUS is my attempt
at that: a system that ingests a repo, parses it into structure, embeds it
into semantic vectors, maps it onto a dependency graph, and lets you *talk
to it*.

## What It Does

Give NEXUS a Git URL and it will:

- **Clone and catalogue** every source file in the repo.
- **Parse** each file into an AST and pull out functions, classes, imports,
  and inheritance chains. Python uses the real `ast` module; JS/TS uses a
  regex-based parser that works without native bindings.
- **Embed** every chunk of code (functions, classes, file summaries) into a
  384-dimensional vector using a sentence-transformer model and write them
  into a vector database (ChromaDB).
- **Graph** the dependencies between files, functions, and classes inside
  Neo4j — so "what calls this function?" or "what does this file depend on?"
  becomes a Cypher query away.
- **Search** the repo with natural language: *"authentication middleware
  that validates JWTs"* returns the right functions in rank order, even if
  none of those words literally appear in the code.
- **Chat** with the codebase — a RAG pipeline combines semantic search +
  graph context and passes it to an LLM so you can ask open questions and
  get answers anchored in real source.
- **Review PRs** — paste a diff, get a summary, a risk score, and
  line-level suggestions.

The whole thing runs as seven small FastAPI services connected by Apache
Kafka, with a React dashboard on top.

## Who It's For

- **You, on day one of a new codebase.** Ingest it, ask what the main
  entrypoint is, look at the dependency graph, read the AI-generated file
  summaries instead of guessing.
- **Code reviewers.** Let the PR analyser flag risky diffs before you even
  open them.
- **Anyone maintaining a large repo.** Watch the graph grow, track what
  depends on what, and find dead code by looking for nodes with no edges.
- **Me, practising distributed systems.** Honestly, half the reason this
  project exists is that I wanted to build a real event-driven pipeline,
  with Kafka topics and consumer groups and dead letter handling, and learn
  where the rough edges are.

## What It Looks Like

```
          ┌──────────────┐
          │   Frontend   │  nexus.localhost  (React + Vite)
          └──────┬───────┘
                 │ REST
          ┌──────▼───────┐
          │   Gateway    │  gateway.localhost  (FastAPI)
          └──────┬───────┘
                 │
          ┌──────▼───────────── Kafka event bus ─────────────┐
          │  repo.ingested │ file.parsed │ embeddings.* │ … │
          └──┬──────┬───────┬───────┬────────┬───────┬─────┘
             │      │       │       │        │       │
         Ingestion Parser Embedding Graph    AI    Search
             │              │       │        │       │
                          ChromaDB Neo4j             ChromaDB
```

Every service owns one job and talks to the others through Kafka topics or
plain REST. That means any of them can crash, restart, or be replaced
without dragging the rest down with them.

## How Far It Goes

- Ingests any public Git repo on the open internet.
- Supports Python, JavaScript, TypeScript, and the usual set of text
  formats (Markdown, JSON, YAML, TOML).
- Works without an LLM key — the AI service falls back to deterministic
  mock responses so you can develop the whole pipeline offline.
- Runs either fully local (`./nexus.sh`) or on a single small VPS — Caddy
  handles automatic HTTPS and routes `*.example.com` subdomains to each
  service.

## Status

This is a personal project. It works end-to-end for repos up to a few
thousand files, but I'm still polishing the AI service and the dependency
graph queries. See the `backlog` section of [Architecture.md](Architecture.md)
for what's next.

## Getting Started

See [Architecture.md](Architecture.md) for the full tech stack, the full
setup guide, the Kafka schemas, and the decisions I made along the way.
The short version is:

```bash
git clone https://github.com/Eternity0207/NeXus.git
cd NeXus
cp .env.example .env
./nexus.sh          # starts infra + services + frontend + Caddy
open http://nexus.localhost
```

## Contributing

Contributions and honest feedback are welcome. See
[CONTRIBUTING.md](CONTRIBUTING.md) for the dev loop.

## License

MIT — see [LICENSE](LICENSE).
