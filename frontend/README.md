# NEXUS Frontend

React-based dashboard for the NEXUS platform.

## Pages

- **Repo Overview** — Repository listing, stats, and status
- **Dependency Graph** — Interactive graph visualization (D3/Cytoscape)
- **Semantic Search** — Search code by meaning, not just text
- **AI Chat** — Conversational interface to query your codebase
- **PR Insights** — AI-powered pull request analysis

## Tech Stack

- React 18
- Vite
- React Router v6
- Cytoscape.js (graph visualization)
- Tailwind CSS (utility styling)

## Running

```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8000` | Gateway API URL |
