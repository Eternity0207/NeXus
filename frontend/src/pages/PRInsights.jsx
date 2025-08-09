import { useState } from 'react';
import { api } from '../api';

const mockPRs = [
  {
    pr_id: '142',
    title: 'feat: add user role-based access control',
    author: 'alice',
    status: 'reviewed',
    risk_score: 0.35,
    summary: 'Adds RBAC middleware with role checking on protected endpoints. Introduces admin, editor, and viewer roles with hierarchical permissions.',
    suggestions: [
      { file: 'app/middleware/rbac.py', line: 27, severity: 'warning', message: 'Role check bypassed when user.is_superadmin — consider explicit audit logging' },
      { file: 'app/models/role.py', line: 12, severity: 'info', message: 'Consider using enum for role names instead of string constants' },
    ],
    files_changed: 6,
    additions: 234,
    deletions: 18,
  },
  {
    pr_id: '139',
    title: 'fix: resolve connection pool exhaustion under load',
    author: 'bob',
    status: 'reviewed',
    risk_score: 0.72,
    summary: 'Fixes database connection pool exhaustion by adding proper connection release in exception handlers and increasing pool timeout.',
    suggestions: [
      { file: 'app/db/session.py', line: 45, severity: 'critical', message: 'Connection not released in the except branch — potential resource leak' },
      { file: 'app/config.py', line: 89, severity: 'warning', message: 'pool_timeout increased to 60s may mask underlying issues' },
      { file: 'app/db/session.py', line: 52, severity: 'info', message: 'Consider using async context manager for guaranteed cleanup' },
    ],
    files_changed: 3,
    additions: 42,
    deletions: 15,
  },
];

export default function PRInsights() {
  const [prUrl, setPrUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [prs] = useState(mockPRs);

  const handleAnalyze = (e) => {
    e.preventDefault();
    setLoading(true);
    setTimeout(() => setLoading(false), 1500);
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
        <form onSubmit={handleAnalyze}>
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

      {/* PR Cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        {prs.map((pr) => (
          <div className="card" key={pr.pr_id}>
            {/* PR Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.375rem' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', fontSize: '0.85rem' }}>#{pr.pr_id}</span>
                  <h3 style={{ fontSize: '1.05rem', fontWeight: 600 }}>{pr.title}</h3>
                </div>
                <div style={{ display: 'flex', gap: '1rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  <span>by @{pr.author}</span>
                  <span>{pr.files_changed} files changed</span>
                  <span style={{ color: 'var(--accent-success)' }}>+{pr.additions}</span>
                  <span style={{ color: 'var(--accent-danger)' }}>-{pr.deletions}</span>
                </div>
              </div>

              {/* Risk Score */}
              <div style={{ textAlign: 'center' }}>
                <div style={{
                  width: 56, height: 56, borderRadius: '50%',
                  border: `3px solid ${riskColor(pr.risk_score)}`,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                }}>
                  <div style={{ fontSize: '1rem', fontWeight: 800, color: riskColor(pr.risk_score) }}>
                    {Math.round(pr.risk_score * 100)}
                  </div>
                </div>
                <div style={{ fontSize: '0.65rem', color: riskColor(pr.risk_score), fontWeight: 600, marginTop: '0.25rem', textTransform: 'uppercase' }}>
                  {riskLabel(pr.risk_score)} Risk
                </div>
              </div>
            </div>

            {/* Summary */}
            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '1rem', lineHeight: 1.6 }}>
              {pr.summary}
            </p>

            {/* Suggestions */}
            <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '1rem' }}>
              <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '0.75rem' }}>
                Review Suggestions
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {pr.suggestions.map((s, idx) => (
                  <div key={idx} style={{
                    display: 'flex', alignItems: 'flex-start', gap: '0.75rem',
                    padding: '0.625rem 0.875rem',
                    background: 'var(--bg-glass)',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '0.85rem',
                  }}>
                    <span className={`badge ${severityClass[s.severity]}`} style={{ flexShrink: 0, marginTop: '0.1rem' }}>
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
          </div>
        ))}
      </div>
    </div>
  );
}
