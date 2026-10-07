import * as React from 'react';
import { AlertCircle, CheckCircle2, Info, X, XCircle } from 'lucide-react';
import { cn } from '../../lib/utils';

export type ToastType = 'success' | 'error' | 'info' | 'warning';

export interface ToastItem {
  id: string;
  type?: ToastType;
  title: string;
  description?: string;
}

interface ToastContextValue {
  toast: (options: Omit<ToastItem, 'id'>) => void;
  removeToast: (id: string) => void;
}

const ToastContext = React.createContext<ToastContextValue | undefined>(undefined);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = React.useState<ToastItem[]>([]);

  const removeToast = React.useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = React.useCallback(
    ({ type = 'info', title, description }: Omit<ToastItem, 'id'>) => {
      const id = Math.random().toString(36).substring(2, 9);
      setToasts((prev) => [...prev, { id, type, title, description }]);

      setTimeout(() => {
        removeToast(id);
      }, 5000);
    },
    [removeToast]
  );

  return (
    <ToastContext.Provider value={{ toast, removeToast }}>
      {children}
      <div
        aria-live="assertive"
        className="pointer-events-none fixed bottom-0 right-0 z-50 flex max-h-screen w-full flex-col-reverse p-4 sm:bottom-0 sm:right-0 sm:top-auto sm:flex-col md:max-w-[420px] gap-2"
      >
        {toasts.map((item) => (
          <div
            key={item.id}
            role="status"
            className={cn(
              'pointer-events-auto flex w-full items-start justify-between space-x-3 overflow-hidden rounded-md border p-4 shadow-lg transition-all animate-in slide-in-from-bottom-5',
              item.type === 'success' &&
                'border-emerald-500/30 bg-emerald-50 dark:bg-emerald-950/80 text-emerald-900 dark:text-emerald-100',
              item.type === 'error' &&
                'border-destructive/30 bg-destructive/10 text-destructive dark:bg-destructive/20',
              item.type === 'warning' &&
                'border-amber-500/30 bg-amber-50 dark:bg-amber-950/80 text-amber-900 dark:text-amber-100',
              item.type === 'info' && 'border-border bg-card text-card-foreground'
            )}
          >
            <div className="flex items-start space-x-2">
              {item.type === 'success' && (
                <CheckCircle2 className="h-5 w-5 text-emerald-600 dark:text-emerald-400 mt-0.5" />
              )}
              {item.type === 'error' && <XCircle className="h-5 w-5 text-destructive mt-0.5" />}
              {item.type === 'warning' && (
                <AlertCircle className="h-5 w-5 text-amber-600 dark:text-amber-400 mt-0.5" />
              )}
              {item.type === 'info' && <Info className="h-5 w-5 text-primary mt-0.5" />}
              <div>
                <h5 className="text-sm font-semibold">{item.title}</h5>
                {item.description && <p className="text-xs opacity-90 mt-1">{item.description}</p>}
              </div>
            </div>
            <button
              onClick={() => removeToast(item.id)}
              className="rounded p-1 opacity-70 hover:opacity-100 focus:outline-none"
              aria-label="Dismiss notification"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};

// eslint-disable-next-line react-refresh/only-export-components
export function useToast(): ToastContextValue {
  const context = React.useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}
