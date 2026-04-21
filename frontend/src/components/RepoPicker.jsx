import { useEffect, useState } from 'react';
import { api } from '../api';
import { useRepo } from '../context/useRepo';

/**
 * Compact dropdown to pick which ingested repo the current page operates on.
 * Persists selection via RepoContext (→ localStorage).
 */
export default function RepoPicker({ compact = false, showLabel = true }) {
  const { activeRepoId, setActiveRepoId } = useRepo();
  const [repos, setRepos] = useState([]);

  useEffect(() => {
    let alive = true;
    (async () => {
      const data = await api.listRepos().catch(() => null);
      if (alive && data?.repos) setRepos(data.repos);
    })();
    return () => { alive = false; };
  }, []);

  const active = repos.find((r) => r.repo_id === activeRepoId);
  const shortName = (r) => (r.repo_url || '').replace('https://github.com/', '') || r.repo_id.slice(0, 8);

  return (
    <div className={`repo-picker ${compact ? 'repo-picker-compact' : ''}`}>
      {showLabel && <label className="repo-picker-label">Repository</label>}
      <div className="repo-picker-wrap">
        <select
          className="input repo-picker-select"
          value={activeRepoId}
          onChange={(e) => setActiveRepoId(e.target.value)}
        >
          <option value="">— none selected —</option>
          {repos.map((r) => (
            <option key={r.repo_id} value={r.repo_id}>
              {shortName(r)} · {r.status}
            </option>
          ))}
        </select>
        {active && (
          <span
            className="repo-picker-id"
            title={active.repo_id}
          >
            {active.repo_id.slice(0, 8)}…
          </span>
        )}
      </div>
    </div>
  );
}
