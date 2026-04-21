import { useState } from 'react';
import { api } from '../api';
import { useRepo } from '../context/useRepo';
import RepoPicker from '../components/RepoPicker';

export default function Search() {
  const { activeRepoId } = useRepo();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [topK, setTopK] = useState(10);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setSearched(true);

    try {
      const data = await api.search(query, activeRepoId || null, topK);
      setResults(data?.results || []);
    } catch {
      setResults([]);
    }

    setLoading(false);
  };

  const scoreColor = (score) => {
    if (score >= 0.9) return 'var(--accent-success)';
    if (score >= 0.7) return 'var(--accent-secondary)';
    if (score >= 0.5) return 'var(--accent-warning)';
    return 'var(--text-muted)';
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">Semantic Search</h1>
        <p className="page-subtitle">Search your codebase using natural language — powered by vector similarity</p>
      </div>

      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div className="search-controls">
          <RepoPicker />
          <label className="depth-control">
            <span>Top K</span>
            <input
              type="range"
              min="3"
              max="25"
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
            />
            <span className="depth-value">{topK}</span>
          </label>
        </div>

        <form onSubmit={handleSearch} style={{ marginTop: '0.75rem' }}>
          <div className="input-group">
            <input
              className="input"
              type="text"
              placeholder="e.g. 'authentication flow with JWT tokens' or 'database connection pooling'"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              style={{ fontSize: '1rem', padding: '0.875rem 1.25rem' }}
            />
            <button className="btn btn-primary" type="submit" disabled={loading} style={{ padding: '0.875rem 1.75rem' }}>
              {loading ? <><span className="spinner" style={{ width: 16, height: 16, marginRight: '0.5rem' }} /> Searching</> : '🔍 Search'}
            </button>
          </div>
          {!activeRepoId && (
            <p className="hint-line">
              Tip — pick a repository above to scope the search. Without a repo, results come from the global index.
            </p>
          )}
        </form>
      </div>

      {loading && (
        <div className="loading">
          <span className="spinner" />
          Searching across embeddings…
        </div>
      )}

      {!loading && !searched && (
        <div className="empty-state">
          <div className="empty-state-icon">🔍</div>
          <p>Search your codebase using natural language.</p>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.5rem' }}>
            Ingest a repository first, then search across functions, classes, and files.
          </p>
        </div>
      )}

      {!loading && searched && results.length === 0 && (
        <div className="empty-state">
          <div className="empty-state-icon">🔍</div>
          <p>No results found. Try a different query or ingest a repository first.</p>
        </div>
      )}

      {!loading && results.length > 0 && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '1rem 1.25rem', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              {results.length} results for "<strong style={{ color: 'var(--text-primary)' }}>{query}</strong>"
            </span>
          </div>

          {results.map((result, idx) => (
            <div className="search-result" key={idx}>
              <div className="search-result-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                  <span className="search-result-path">{result.file_path}</span>
                  <span className="badge badge-primary" style={{ fontSize: '0.65rem' }}>
                    {result.metadata?.type || 'code'}
                  </span>
                  {result.metadata?.name && (
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--accent-primary-hover)' }}>
                      {result.metadata.name}
                    </span>
                  )}
                </div>
                <span className="search-result-score" style={{ color: scoreColor(result.score) }}>
                  {Math.round(result.score * 100)}% match
                </span>
              </div>
              <pre className="search-result-content">{result.content}</pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
