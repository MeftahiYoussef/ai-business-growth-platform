'use client';

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';

type Toast = { id: number; message: string; tone?: 'error' | 'success' };
type ToastContextValue = { showToast: (message: string, tone?: Toast['tone']) => void };

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const showToast = useCallback((message: string, tone: Toast['tone'] = 'success') => {
    const id = Date.now();
    setToasts((current) => [...current, { id, message, tone }]);
    window.setTimeout(() => setToasts((current) => current.filter((toast) => toast.id !== id)), 3600);
  }, []);
  const value = useMemo(() => ({ showToast }), [showToast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div aria-live="polite" style={{ bottom: 20, display: 'grid', gap: 10, position: 'fixed', right: 20, zIndex: 80 }}>
        {toasts.map((toast) => (
          <div
            className="app-card"
            key={toast.id}
            style={{
              borderColor: toast.tone === 'error' ? 'rgba(248,113,113,.45)' : 'rgba(52,211,153,.45)',
              maxWidth: 360,
              padding: 14
            }}
          >
            {toast.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) throw new Error('useToast must be used within ToastProvider');
  return context;
}
