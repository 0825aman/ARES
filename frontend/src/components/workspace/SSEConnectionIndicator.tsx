'use client';

interface SSEConnectionIndicatorProps {
  connected: boolean;
}

/**
 * Small badge shown in the workspace header.
 * Green dot + "Live" when SSE is connected.
 * Grey dot + "Polling" when SSE is disconnected (fallback mode).
 */
export function SSEConnectionIndicator({ connected }: SSEConnectionIndicatorProps) {
  return (
    <div className="flex items-center gap-1.5">
      <span
        className={`h-2 w-2 rounded-full flex-shrink-0 ${
          connected ? 'bg-green-500' : 'bg-slate-400'
        }`}
        aria-hidden="true"
      />
      <span className="text-xs text-slate-500">
        {connected ? 'Live' : 'Polling'}
      </span>
    </div>
  );
}
