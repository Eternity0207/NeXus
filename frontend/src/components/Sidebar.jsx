import { NavLink } from 'react-router-dom';

const navItems = [
  { path: '/', icon: '📊', label: 'Overview' },
  { path: '/graph', icon: '🔗', label: 'Dependency Graph' },
  { path: '/search', icon: '🔍', label: 'Semantic Search' },
  { path: '/chat', icon: '🤖', label: 'AI Chat' },
  { path: '/pr', icon: '📋', label: 'PR Insights' },
];

export default function Sidebar() {
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

      <div style={{ padding: '1rem 1.5rem', borderTop: '1px solid var(--border-subtle)' }}>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
          Codebase Intelligence
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
          v0.1.0
        </div>
      </div>
    </aside>
  );
}
