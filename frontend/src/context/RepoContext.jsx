import { createContext, useState, useCallback } from 'react';

const KEY = 'nexus.activeRepoId';

// eslint-disable-next-line react-refresh/only-export-components
export const RepoContext = createContext(null);

export function RepoProvider({ children }) {
  const [activeRepoId, setActiveRepoIdState] = useState(() => {
    try { return localStorage.getItem(KEY) || ''; } catch { return ''; }
  });
  const [activeRepo, setActiveRepo] = useState(null);

  const setActiveRepoId = useCallback((id) => {
    setActiveRepoIdState(id || '');
    try {
      if (id) localStorage.setItem(KEY, id);
      else localStorage.removeItem(KEY);
    } catch { /* ignore quota / privacy errors */ }
  }, []);

  return (
    <RepoContext.Provider value={{ activeRepoId, setActiveRepoId, activeRepo, setActiveRepo }}>
      {children}
    </RepoContext.Provider>
  );
}
