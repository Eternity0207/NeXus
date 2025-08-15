import { useState, useEffect } from 'react';
import { api } from '../api';

export default function Overview() {
  const [repoUrl, setRepoUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [repos, setRepos] = useState([]);
  const [stats, setStats] = useState({
    repos: 0,
    files: 0,
    functions: 0,
    embeddings: 0,
  });

  useEffect(() => {
    fetchRepos();
  }, []);

  const fetchRepos = async () => {
    try {
      const data = await api.listRepos();
      if (data?.repos) {
        setRepos(data.repos);
        setStats({
          repos: data.repos.length,
          files: data.repos.reduce((sum, r) => sum + (r.file_count || 0), 0),
          functions: data.total_functions || 0,
          embeddings: data.total_embeddings || 0,
        });
      }
    } catch {
      // API not available — show empty state
    }
  };

  const handleIngest = async (e) => {
    e.preventDefault();
    if (!repoUrl.trim()) return;
    setLoading(true);
    try {
      await api.ingestRepo(repoUrl);
      setRepoUrl('');
      await fetchRepos();
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
      pending: 'badge-primary',
    };
    return <span className={`badge ${map[status] || 'badge-primary'}`}>{status}</span>;
  };

  const statCards = [
    { label: 'Repositories', value: stats.repos, icon: '📦' },
    { label: 'Files Indexed', value: stats.files, icon: '📄' },
    { label: 'Functions Mapped', value: stats.functions, icon: '⚡' },
    { label: 'Embeddings', value: stats.embeddings, icon: '🧬' },
  ];

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">Dashboard</h1>
        <p className="page-subtitle">Monitor your codebase intelligence pipeline</p>
      </div>

      {/* Stats Grid */}
      <div className="card-grid" style={{ marginBottom: '2rem' }}>
        {statCards.map((s) => (
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

        {repos.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">📦</div>
            <p>No repositories ingested yet.</p>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.5rem' }}>
              Paste a GitHub URL above to get started.
            </p>
          </div>
        ) : (
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
                        {(repo.repo_url || '').replace('https://github.com/', '')}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.125rem' }}>
                        {(repo.repo_id || '').slice(0, 8)}
                      </div>
                    </td>
                    <td><code>{repo.branch || 'main'}</code></td>
                    <td>{statusBadge(repo.status || 'pending')}</td>
                    <td>{repo.file_count || 0}</td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.375rem', flexWrap: 'wrap' }}>
                        {Object.entries(repo.languages || {}).slice(0, 3).map(([lang, count]) => (
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
        )}
      </div>
    </div>
  );
}
