import { useState } from 'react';
import { api } from '../api';

const mockRepos = [
  { repo_id: 'demo-1', repo_url: 'https://github.com/example/fastapi-app', branch: 'main', status: 'completed', file_count: 47, languages: { python: 32, yaml: 8, markdown: 7 }, created_at: '2025-08-01T10:00:00' },
  { repo_id: 'demo-2', repo_url: 'https://github.com/example/react-dashboard', branch: 'main', status: 'completed', file_count: 83, languages: { javascript: 45, typescript: 22, css: 16 }, created_at: '2025-08-02T14:30:00' },
  { repo_id: 'demo-3', repo_url: 'https://github.com/example/ml-pipeline', branch: 'develop', status: 'ingesting', file_count: 0, languages: {}, created_at: '2025-08-05T09:15:00' },
];

const stats = [
  { label: 'Repositories', value: '3', icon: '📦' },
  { label: 'Files Indexed', value: '130', icon: '📄' },
  { label: 'Functions Mapped', value: '842', icon: '⚡' },
  { label: 'Embeddings', value: '2.4K', icon: '🧬' },
];

export default function Overview() {
  const [repoUrl, setRepoUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [repos] = useState(mockRepos);

  const handleIngest = async (e) => {
    e.preventDefault();
    if (!repoUrl.trim()) return;
    setLoading(true);
    try {
      await api.ingestRepo(repoUrl);
      setRepoUrl('');
    } catch (err) {
      console.error('Ingest failed:', err);
    }
    setLoading(false);
  };

  const statusBadge = (status) => {
    const map = {
      completed: 'badge-success',
      ingesting: 'badge-warning',
      failed: 'badge-danger',
      queued: 'badge-primary',
    };
    return <span className={`badge ${map[status] || 'badge-primary'}`}>{status}</span>;
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">Dashboard</h1>
        <p className="page-subtitle">Monitor your codebase intelligence pipeline</p>
      </div>

      {/* Stats Grid */}
      <div className="card-grid" style={{ marginBottom: '2rem' }}>
        {stats.map((s) => (
          <div className="card stat-card" key={s.label}>
            <div style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>{s.icon}</div>
            <div className="stat-value">{s.value}</div>
            <div className="stat-label">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Ingest Form */}
      <div className="card" style={{ marginBottom: '2rem' }}>
        <div className="card-header">
          <h3 className="card-title">Ingest Repository</h3>
        </div>
        <form onSubmit={handleIngest}>
          <div className="input-group">
            <input
              className="input"
              type="text"
              placeholder="https://github.com/user/repo.git"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
            />
            <button className="btn btn-primary" type="submit" disabled={loading}>
              {loading ? 'Ingesting...' : '🚀 Ingest'}
            </button>
          </div>
        </form>
      </div>

      {/* Repositories Table */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Repositories</h3>
          <span className="badge badge-primary">{repos.length} total</span>
        </div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Repository</th>
                <th>Branch</th>
                <th>Status</th>
                <th>Files</th>
                <th>Languages</th>
              </tr>
            </thead>
            <tbody>
              {repos.map((repo) => (
                <tr key={repo.repo_id}>
                  <td>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: 'var(--accent-secondary)' }}>
                      {repo.repo_url.replace('https://github.com/', '')}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.125rem' }}>
                      {repo.repo_id.slice(0, 8)}
                    </div>
                  </td>
                  <td><code>{repo.branch}</code></td>
                  <td>{statusBadge(repo.status)}</td>
                  <td>{repo.file_count}</td>
                  <td>
                    <div style={{ display: 'flex', gap: '0.375rem', flexWrap: 'wrap' }}>
                      {Object.entries(repo.languages).slice(0, 3).map(([lang, count]) => (
                        <span key={lang} className="badge badge-primary" style={{ fontSize: '0.7rem' }}>
                          {lang} ({count})
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
