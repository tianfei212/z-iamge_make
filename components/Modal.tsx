import React, { useEffect, useRef, useState } from 'react';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children?: React.ReactNode;
}

export const Modal: React.FC<ModalProps> = ({ open, onClose, title, children }) => {
  const [mounted, setMounted] = useState(open);
  const [closing, setClosing] = useState(false);
  const closeTimer = useRef<number | null>(null);

  useEffect(() => {
    if (open) {
      setMounted(true);
      setClosing(false);
    } else if (mounted) {
      setClosing(true);
      closeTimer.current = window.setTimeout(() => {
        setMounted(false);
        setClosing(false);
      }, 200);
    }
    return () => {
      if (closeTimer.current) {
        clearTimeout(closeTimer.current);
        closeTimer.current = null;
      }
    };
  }, [open, mounted]);

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        setClosing(true);
        window.setTimeout(() => onClose(), 200);
      }
    }
    if (mounted) {
      document.addEventListener('keydown', handleKey);
    }
    return () => document.removeEventListener('keydown', handleKey);
  }, [mounted, onClose]);

  if (!mounted) return null;
  return (
    <div className={`fixed inset-0 z-50 transition-opacity ${closing ? 'opacity-0' : 'opacity-100'}`}>
      <div className="absolute inset-0 bg-black/60" onClick={() => {
        setClosing(true);
        window.setTimeout(() => onClose(), 200);
      }} />
      <div
        className={`absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-[#141518] border border-[#2e3035] rounded-lg shadow-xl overflow-hidden transition-transform ${closing ? 'scale-95' : 'scale-100'}`}
      >
        {title ? (
          <div className="flex items-center justify-between px-4 py-3 border-b border-[#2e3035]">
            <h2 className="text-sm font-bold tracking-wider text-gray-200">{title}</h2>
            <button
              onClick={() => {
                setClosing(true);
                window.setTimeout(() => onClose(), 200);
              }}
              className="w-6 h-6 flex items-center justify-center rounded bg-zinc-800 text-zinc-300 hover:opacity-80 transition-opacity"
              title="Close"
            >
              <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" fill="none" strokeWidth="2">
                <path d="M6 6l12 12M6 18L18 6" />
              </svg>
            </button>
          </div>
        ) : null}
        <div className="w-full h-full p-4 overflow-auto">
          {children}
        </div>
      </div>
      <style>
        {`
          @media (max-width: 640px) {
            .fixed > div.absolute > div {
              width: 90vw;
              height: 80vh;
            }
          }
          @media (min-width: 641px) {
            .fixed > div.absolute > div {
              width: 800px;
              height: 600px;
            }
          }
        `}
      </style>
    </div>
  );
};
