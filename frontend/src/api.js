// ─── API Client ─────────────────────────────────────────────────────────────
// In local dev and production we talk to the gateway through a reverse proxy
// (Caddy) that exposes gateway.<host>. Override with VITE_API_URL if needed.

const API_BASE = (() => {
  const env = import.meta.env.VITE_API_URL;
  if (env) return env.replace(/\/$/, '');
  if (typeof window !== 'undefined') {
    const { protocol, hostname, port } = window.location;
    if (hostname === 'nexus.localhost') {
      return `${protocol}//gateway.localhost`;
    }
    if (hostname.endsWith('.localhost')) {
      return `${protocol}//gateway.localhost`;
    }
    if (port === '5173' || port === '3000') {
      return 'http://localhost:8000';
    }
    return `${protocol}//gateway.${hostname.replace(/^(nexus\.|www\.)/, '')}`;
  }
  return 'http://localhost:8000';
})();

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const config = {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  };

  try {
    const res = await fetch(url, config);
    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(error.detail || `HTTP ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      console.warn(`API unavailable: ${url}`);
      return null;
    }
    throw err;
  }
}

export const api = {
  listRepos: () => request('/api/v1/repos'),
  getRepo: (id) => request(`/api/v1/repos/${id}`),
  ingestRepo: (repoUrl, branch = 'main') =>
    request('/api/v1/repos', {
      method: 'POST',
      body: JSON.stringify({ repo_url: repoUrl, branch }),
    }),
  deleteRepo: (id) =>
    request(`/api/v1/repos/${id}`, { method: 'DELETE' }),

  search: (query, repoId = null, topK = 10) =>
    request('/api/v1/search', {
      method: 'POST',
      body: JSON.stringify({ query, repo_id: repoId, top_k: topK }),
    }),

  chat: (message, repoId, conversationId = null) =>
    request('/api/v1/chat', {
      method: 'POST',
      body: JSON.stringify({ message, repo_id: repoId, conversation_id: conversationId }),
    }),

  getGraph: (repoId, depth = 2, nodeType = 'all') =>
    request(`/api/v1/graph/${repoId}?depth=${depth}&node_type=${nodeType}`),

  analyzePR: (repoId, prUrl) =>
    request('/api/v1/pr/analyze', {
      method: 'POST',
      body: JSON.stringify({ repo_id: repoId, pr_url: prUrl }),
    }),

  health: () => request('/health'),
};
