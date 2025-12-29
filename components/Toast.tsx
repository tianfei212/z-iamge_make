import React, { useEffect, useState } from 'react';

type ToastType = 'success' | 'error' | 'info';

interface ToastItem {
  id: string;
  message: string;
  type: ToastType;
}

export function showToast(message: string, type: ToastType = 'info') {
  window.dispatchEvent(new CustomEvent('app-toast', { detail: { message, type } }));
}

export const ToastContainer: React.FC = () => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  useEffect(() => {
    function handler(ev: Event) {
      const ce = ev as CustomEvent<{ message: string; type: ToastType }>;
      const id = crypto.randomUUID();
      const item: ToastItem = { id, message: ce.detail.message, type: ce.detail.type };
      setToasts(prev => [...prev, item]);
      setTimeout(() => {
        setToasts(prev => prev.filter(t => t.id !== id));
      }, 3000);
    }
    window.addEventListener('app-toast', handler as EventListener);
    return () => window.removeEventListener('app-toast', handler as EventListener);
  }, []);

  const typeStyles: Record<ToastType, string> = {
    success: 'bg-green-600',
    error: 'bg-red-600',
    info: 'bg-zinc-800',
  };

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2">
      {toasts.map(t => (
        <div
          key={t.id}
          className={`px-3 py-2 rounded text-sm text-white shadow-lg ${typeStyles[t.type]} transition-all animate-fade-in`}
        >
          {t.message}
        </div>
      ))}
      <style>
        {`
          @keyframes fade-in { from { opacity: 0; transform: translateY(-6px); } to { opacity: 1; transform: translateY(0); } }
          .animate-fade-in { animation: fade-in 160ms ease-out; }
        `}
      </style>
    </div>
  );
};

