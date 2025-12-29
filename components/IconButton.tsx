import React from 'react';

interface IconButtonProps {
  title?: string;
  onClick?: () => void;
}

export const IconButton: React.FC<IconButtonProps> = ({ title, onClick }) => {
  return (
    <button
      title={title}
      onClick={onClick}
      className="w-6 h-6 flex items-center justify-center rounded bg-zinc-800 text-zinc-300 hover:opacity-80 hover:scale-105 active:scale-95 transition-transform duration-200"
      style={{ width: 24, height: 24 }}
    >
      <svg
        viewBox="0 0 24 24"
        width="24"
        height="24"
        className="text-zinc-300"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 12a7.4 7.4 0 0 0-.1-1l2.1-1.6-2-3.4-2.6.8a7.4 7.4 0 0 0-1.7-1l-.4-2.7H11l-.4 2.7a7.4 7.4 0 0 0-1.7 1l-2.6-.8-2 3.4 2.1 1.6a7.4 7.4 0 0 0-.1 1c0 .3 0 .7.1 1L4.3 14.6l2 3.4 2.6-.8c.5.4 1.1.7 1.7 1l.4 2.7h3.2l.4-2.7c.6-.3 1.2-.6 1.7-1l2.6.8 2-3.4-2.1-1.6c.1-.3.1-.7.1-1Z" />
      </svg>
    </button>
  );
};

