'use client';

import { useState } from 'react';
import { RefreshCw, Radio } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ApiConnectionErrorProps {
  onRetry?: () => void | Promise<void>;
  message?: string;
}

export function ApiConnectionError({ onRetry, message }: ApiConnectionErrorProps) {
  const [isRetrying, setIsRetrying] = useState(false);

  const isLocal =
    typeof window !== 'undefined' &&
    (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');

  async function handleRetry() {
    if (!onRetry) {
      if (typeof window !== 'undefined') window.location.reload();
      return;
    }
    setIsRetrying(true);
    try {
      await onRetry();
    } finally {
      setIsRetrying(false);
    }
  }

  return (
    <div className="rounded-xl border border-amber-500/40 bg-gradient-to-r from-amber-500/10 via-slate-900 to-amber-950/20 p-4 sm:p-5 font-mono shadow-lg backdrop-blur-md">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-amber-500/20 border border-amber-500/40 text-amber-400 mt-0.5">
            <Radio className="h-4 w-4 animate-pulse" />
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-amber-300 uppercase tracking-wider">
                Backend Service Initializing
              </span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30">
                Cold Start
              </span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed max-w-xl">
              {message ||
                (isLocal
                  ? 'Cannot reach local backend API. Ensure Uvicorn is running on 127.0.0.1:8000.'
                  : 'The backend service is waking up. Render Free Tier instances spin down when idle and take ~30–45s to boot on first request.')}
            </p>
          </div>
        </div>

        <Button
          onClick={handleRetry}
          disabled={isRetrying}
          size="sm"
          className="bg-amber-600/90 hover:bg-amber-500 text-white font-mono text-xs font-semibold px-4 border border-amber-400/40 shadow-md shrink-0 flex items-center gap-1.5 self-start sm:self-center"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isRetrying ? 'animate-spin' : ''}`} />
          <span>{isRetrying ? 'CONNECTING…' : 'RETRY CONNECTION'}</span>
        </Button>
      </div>
    </div>
  );
}
