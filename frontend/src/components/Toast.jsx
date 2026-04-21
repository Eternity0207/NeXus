import { createContext, useState, useCallback } from 'react';

// eslint-disable-next-line react-refresh/only-export-components
export const ToastContext = createContext(null);

let uid = 0;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const remove = useCallback((id) => {
    setToasts((t) => t.filter((x) => x.id !== id));
  }, []);

  const toast = useCallback((message, opts = {}) => {
    const id = ++uid;
    const kind = opts.kind || 'info';
    const duration = opts.duration ?? 2600;
    setToasts((t) => [...t, { id, message, kind }]);
    setTimeout(() => remove(id), duration);
    return id;
  }, [remove]);

  const value = {
    toast,
    success: (m, o) => toast(m, { ...o, kind: 'success' }),
    error:   (m, o) => toast(m, { ...o, kind: 'error' }),
    info:    (m, o) => toast(m, { ...o, kind: 'info' }),
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-stack" role="status" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast-${t.kind}`}>
            <span className="toast-dot" />
            <span className="toast-msg">{t.message}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
