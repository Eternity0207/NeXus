import { useState } from 'react';
import { api } from '../api';
import { useRepo } from '../context/useRepo';
import RepoPicker from '../components/RepoPicker';

export default function PRInsights() {
  const { activeRepoId } = useRepo();
  const [prUrl, setPrUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [prs, setPrs] = useState([]);

  const handleAnalyze = async (e) => {
    e.preventDefault();
    if (!prUrl.trim()) return;

    setLoading(true);
    try {
      const data = await api.analyzePR(activeRepoId || 'default', prUrl);
      if (data) {
        setPrs(prev => [data, ...prev]);
      }
      setPrUrl('');
    } catch (err) {
      console.error('PR analysis failed:', err);
    }
    setLoading(false);
  };

  const riskColor = (score) => {
    if (score >= 0.7) return 'var(--accent-danger)';
    if (score >= 0.4) return 'var(--accent-warning)';
    return 'var(--accent-success)';
  };

  const riskLabel = (score) => {
    if (score >= 0.7) return 'High';
    if (score >= 0.4) return 'Medium';
    return 'Low';
  };

  const severityClass = {
    critical: 'badge-danger',
    warning: 'badge-warning',
    info: 'badge-primary',
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">PR Insights</h1>
        <p className="page-subtitle">AI-powered pull request analysis with risk scoring</p>
      </div>

      {/* Analyze Form */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <RepoPicker />
        <form onSubmit={handleAnalyze} style={{ marginTop: '0.75rem' }}>
          <div className="input-group">
            <input
              className="input"
              placeholder="https://github.com/user/repo/pull/123"
              value={prUrl}
              onChange={(e) => setPrUrl(e.target.value)}
            />
            <button className="btn btn-primary" type="submit" disabled={loading}>
              {loading ? 'Analyzing...' : '🔬 Analyze PR'}
            </button>
          </div>
        </form>
      </div>

      {/* Empty State */}
      {prs.length === 0 && (
        <div className="empty-state">
          <div className="empty-state-icon">📋</div>
          <p>No PRs analyzed yet.</p>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.5rem' }}>
            Paste a GitHub PR URL above to get AI-powered review insights.
          </p>
        </div>
      )}

      {/* PR Cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        {prs.map((pr, idx) => (
          <div className="card" key={idx}>
            {/* PR Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.375rem' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', fontSize: '0.85rem' }}>#{pr.pr_id || idx + 1}</span>
                  <h3 style={{ fontSize: '1.05rem', fontWeight: 600 }}>{pr.title || 'PR Analysis'}</h3>
                </div>
              </div>

              {/* Risk Score */}
              <div style={{ textAlign: 'center' }}>
                <div style={{
                  width: 56, height: 56, borderRadius: '50%',
                  border: `3px solid ${riskColor(pr.risk_score || 0)}`,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                }}>
                  <div style={{ fontSize: '1rem', fontWeight: 800, color: riskColor(pr.risk_score || 0) }}>
                    {Math.round((pr.risk_score || 0) * 100)}
                  </div>
                </div>
                <div style={{ fontSize: '0.65rem', color: riskColor(pr.risk_score || 0), fontWeight: 600, marginTop: '0.25rem', textTransform: 'uppercase' }}>
                  {riskLabel(pr.risk_score || 0)} Risk
                </div>
              </div>
            </div>

            {/* Summary */}
            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '1rem', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
              {pr.summary || 'No summary available.'}
            </p>

            {/* Suggestions */}
            {pr.suggestions && pr.suggestions.length > 0 && (
              <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '1rem' }}>
                <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '0.75rem' }}>
                  Review Suggestions
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {pr.suggestions.map((s, i) => (
                    <div key={i} style={{
                      display: 'flex', alignItems: 'flex-start', gap: '0.75rem',
                      padding: '0.625rem 0.875rem',
                      background: 'var(--bg-glass)',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '0.85rem',
                    }}>
                      <span className={`badge ${severityClass[s.severity] || 'badge-primary'}`} style={{ flexShrink: 0, marginTop: '0.1rem' }}>
                        {s.severity}
                      </span>
                      <div>
                        <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-secondary)', fontSize: '0.8rem' }}>
                          {s.file}:{s.line}
                        </span>
                        <span style={{ margin: '0 0.5rem', color: 'var(--text-muted)' }}>—</span>
                        <span style={{ color: 'var(--text-secondary)' }}>{s.message}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
