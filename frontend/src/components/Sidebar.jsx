import { NavLink } from 'react-router-dom';
import { useRepo } from '../context/useRepo';
import CopyButton from './CopyButton';

const navItems = [
  { path: '/', icon: '📊', label: 'Overview' },
  { path: '/graph', icon: '🔗', label: 'Dependency Graph' },
  { path: '/search', icon: '🔍', label: 'Semantic Search' },
  { path: '/chat', icon: '🤖', label: 'AI Chat' },
  { path: '/pr', icon: '📋', label: 'PR Insights' },
];

export default function Sidebar() {
  const { activeRepoId, setActiveRepoId } = useRepo();

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">N</div>
          <span className="sidebar-logo-text">NEXUS</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map(({ path, icon, label }) => (
          <NavLink
            key={path}
            to={path}
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            end={path === '/'}
          >
            <span className="nav-link-icon">{icon}</span>
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      {activeRepoId && (
        <div className="sidebar-active-repo">
          <div className="sidebar-active-repo-label">Active repository</div>
          <div className="sidebar-active-repo-row">
            <code title={activeRepoId}>{activeRepoId.slice(0, 8)}…</code>
            <CopyButton value={activeRepoId} label="Repo ID" compact />
            <button
              type="button"
              className="sidebar-active-repo-clear"
              onClick={() => setActiveRepoId('')}
              title="Clear active repository"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      <div className="sidebar-footer">
        <div className="sidebar-footer-label">Codebase Intelligence</div>
        <div className="sidebar-footer-version">v0.1.0</div>
      </div>
    </aside>
  );
}
