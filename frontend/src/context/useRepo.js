import { useContext } from 'react';
import { RepoContext } from './RepoContext';

export function useRepo() {
  const ctx = useContext(RepoContext);
  if (!ctx) throw new Error('useRepo must be used inside <RepoProvider>');
  return ctx;
}
