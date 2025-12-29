import React from 'react';

interface LogsPanelProps {
  logs: string[];
}

export const LogsPanel: React.FC<LogsPanelProps> = ({ logs }) => {
  return (
    <div className="h-32 border-t border-zinc-800 bg-black/40 p-4 font-mono text-[9px] overflow-y-auto custom-scrollbar text-zinc-500">
      {logs.map((log, i) => <div key={i} className="mb-1">{log}</div>)}
    </div>
  );
};

