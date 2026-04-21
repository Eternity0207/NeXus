import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { useRepo } from '../context/useRepo';
import { useToast } from '../components/useToast';
import CopyButton from '../components/CopyButton';

const IN_PROGRESS = new Set(['pending', 'cloning', 'extracting', 'publishing']);

function StageIndicator({ status }) {
  const stages = ['cloning', 'extracting', 'publishing', 'completed'];
  const reached = (s) => {
    if (status === 'failed') return false;
    const idx = stages.indexOf(status);
    return idx >= 0 && idx >= stages.indexOf(s);
  };
  const active = (s) => status === s;
  const failed = status === 'failed';

  return (
    <div className="pipeline-stages" aria-label="pipeline progress">
      {stages.map((s, i) => (
        <span
          key={s}
          className={[
            'pipeline-stage',
            reached(s) ? 'reached' : '',
            active(s) ? 'active' : '',
            failed && i === 0 ? 'failed' : '',
          ].join(' ')}
          title={s}
        >
          <span className="pipeline-stage-dot" />
          <span className="pipeline-stage-label">{s}</span>
        </span>
      ))}
    </div>
  );
}

export default function Overview() {
  const navigate = useNavigate();
  const toast = useToast();
  const { activeRepoId, setActiveRepoId } = useRepo();

  const [repoUrl, setRepoUrl] = useState('');
  const [branch, setBranch] = useState('main');
  const [loading, setLoading] = useState(false);
  const [repos, setRepos] = useState([]);
  const [confirm, setConfirm] = useState(null);
  const pollRef = useRef(null);

  const fetchRepos = useCallback(async () => {
    const data = await api.listRepos().catch(() => null);
    if (data?.repos) setRepos(data.repos);
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchRepos();
  }, [fetchRepos]);

  // Auto-refresh every 3s while any repo is mid-pipeline.
  useEffect(() => {
    const anyInProgress = repos.some((r) => IN_PROGRESS.has(r.status));
    if (anyInProgress && !pollRef.current) {
      pollRef.current = setInterval(fetchRepos, 3000);
    }
    if (!anyInProgress && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    };
  }, [repos, fetchRepos]);

  const handleIngest = async (e) => {
    e.preventDefault();
    if (!repoUrl.trim()) return;
    setLoading(true);
    try {
      const res = await api.ingestRepo(repoUrl.trim(), branch.trim() || 'main');
      setRepoUrl('');
      toast.success('Ingestion started');
      if (res?.repo_id) setActiveRepoId(res.repo_id);
      await fetchRepos();
    } catch (err) {
      toast.error(err.message || 'Ingest failed');
    }
    setLoading(false);
  };

  const handleDelete = async (id) => {
    try {
      await api.deleteRepo(id);
      if (activeRepoId === id) setActiveRepoId('');
      toast.success('Repository removed');
      await fetchRepos();
    } catch (err) {
      toast.error(err.message || 'Delete failed');
    }
    setConfirm(null);
  };

  const goTo = (path, id) => {
    setActiveRepoId(id);
    navigate(path);
  };

  const statusBadge = (s) => {
    const map = {
      completed: 'badge-success',
      cloning: 'badge-warning',
      extracting: 'badge-warning',
      publishing: 'badge-warning',
      pending: 'badge-primary',
      failed: 'badge-danger',
    };
    return <span className={`badge ${map[s] || 'badge-primary'}`}>{s}</span>;
  };

  const totalFiles = repos.reduce((s, r) => s + (r.file_count || 0), 0);
  const completed = repos.filter((r) => r.status === 'completed').length;
  const inProgress = repos.filter((r) => IN_PROGRESS.has(r.status)).length;

  const statCards = [
    { label: 'Repositories', value: repos.length, icon: '📦' },
    { label: 'Completed', value: completed, icon: '✅' },
    { label: 'In progress', value: inProgress, icon: '⏳' },
    { label: 'Files indexed', value: totalFiles, icon: '📄' },
  ];

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">Dashboard</h1>
        <p className="page-subtitle">Ingest codebases and jump into exploring them</p>
      </div>

      {/* Stats */}
      <div className="card-grid" style={{ marginBottom: '2rem' }}>
        {statCards.map((s) => (
          <div className="card stat-card" key={s.label}>
            <div className="stat-icon">{s.icon}</div>
            <div className="stat-value">{s.value}</div>
            <div className="stat-label">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Ingest */}
      <div className="card" style={{ marginBottom: '2rem' }}>
        <div className="card-header">
          <h3 className="card-title">Ingest a Repository</h3>
          <span className="kbd-hint">
            <kbd>Paste</kbd> a GitHub URL to kick off the pipeline
          </span>
        </div>
        <form onSubmit={handleIngest}>
          <div className="input-group ingest-form">
            <input
              className="input"
              type="text"
              placeholder="https://github.com/user/repo"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
            />
            <input
              className="input branch-input"
              type="text"
              placeholder="main"
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
              title="Branch name"
            />
            <button className="btn btn-primary" type="submit" disabled={loading}>
              {loading ? 'Starting…' : '🚀 Ingest'}
            </button>
          </div>
        </form>
      </div>

      {/* Repositories */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Repositories</h3>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <span className="badge badge-primary">{repos.length} total</span>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={fetchRepos}
              title="Refresh"
            >
              ⟳ Refresh
            </button>
          </div>
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
          <div className="repo-list">
            {repos.map((repo) => {
              const isActive = repo.repo_id === activeRepoId;
              const canExplore = repo.status === 'completed';
              const shortName = (repo.repo_url || '').replace('https://github.com/', '') || repo.repo_id;
              return (
                <div className={`repo-card ${isActive ? 'active' : ''}`} key={repo.repo_id}>
                  <div className="repo-card-top">
                    <div className="repo-card-title-col">
                      <a
                        href={repo.repo_url}
                        target="_blank"
                        rel="noreferrer"
                        className="repo-card-name"
                      >
                        {shortName}
                      </a>
                      <div className="repo-card-meta">
                        <code className="repo-card-id" title={repo.repo_id}>
                          {repo.repo_id}
                        </code>
                        <CopyButton value={repo.repo_id} label="Repo ID" compact />
                      </div>
                    </div>

                    <div className="repo-card-status-col">
                      {statusBadge(repo.status || 'pending')}
                      <div className="repo-card-branch">
                        <span className="text-muted">branch:</span> <code>{repo.branch || 'main'}</code>
                      </div>
                    </div>
                  </div>

                  <StageIndicator status={repo.status} />

                  <div className="repo-card-bottom">
                    <div className="repo-card-stats">
                      <span>
                        <strong>{repo.file_count || 0}</strong>
                        <span className="text-muted"> files</span>
                      </span>
                      <span className="lang-chips">
                        {Object.entries(repo.languages || {}).slice(0, 4).map(([lang, count]) => (
                          <span key={lang} className="lang-chip">
                            {lang} · {count}
                          </span>
                        ))}
                      </span>
                    </div>

                    <div className="repo-card-actions">
                      <button
                        type="button"
                        className={`btn btn-sm ${isActive ? 'btn-primary' : 'btn-secondary'}`}
                        onClick={() => setActiveRepoId(repo.repo_id)}
                        title={isActive ? 'Selected' : 'Make this the active repo'}
                      >
                        {isActive ? '★ Active' : '☆ Select'}
                      </button>
                      <button
                        type="button"
                        className="btn btn-sm btn-secondary"
                        disabled={!canExplore}
                        onClick={() => goTo('/graph', repo.repo_id)}
                        title={canExplore ? 'Open dependency graph' : 'Available after pipeline completes'}
                      >
                        🔗 Graph
                      </button>
                      <button
                        type="button"
                        className="btn btn-sm btn-secondary"
                        disabled={!canExplore}
                        onClick={() => goTo('/search', repo.repo_id)}
                        title={canExplore ? 'Semantic search' : 'Available after pipeline completes'}
                      >
                        🔍 Search
                      </button>
                      <button
                        type="button"
                        className="btn btn-sm btn-secondary"
                        disabled={!canExplore}
                        onClick={() => goTo('/chat', repo.repo_id)}
                        title={canExplore ? 'Ask the AI' : 'Available after pipeline completes'}
                      >
                        🤖 Chat
                      </button>
                      <button
                        type="button"
                        className="btn btn-sm btn-danger"
                        onClick={() => setConfirm(repo)}
                        title="Delete repository"
                      >
                        ✕
                      </button>
                    </div>
                  </div>

                  {repo.error && (
                    <div className="repo-card-error">⚠ {repo.error}</div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Confirm delete */}
      {confirm && (
        <div className="modal-overlay" onClick={() => setConfirm(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3 className="modal-title">Remove repository?</h3>
            <p className="modal-body">
              This will delete the ingestion record and wipe the local clone.
              Vectors in Chroma and nodes in Neo4j are not removed automatically.
            </p>
            <pre className="modal-code">{confirm.repo_id}</pre>
            <div className="modal-actions">
              <button type="button" className="btn btn-secondary" onClick={() => setConfirm(null)}>Cancel</button>
              <button type="button" className="btn btn-danger" onClick={() => handleDelete(confirm.repo_id)}>Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
