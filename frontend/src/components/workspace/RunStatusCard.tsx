'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2, Clock, AlertCircle, CheckCircle2, Hourglass, Cpu, Zap } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { getRun } from '@/lib/api/runs';
import type { ResearchRun } from '@/lib/types/run';

const FALLBACK_POLL_INTERVAL = 60_000;

const STAGES = [
  'Initializing',
  'Processing documents',
  'Searching the web',
  'Collecting evidence',
  'Synthesizing findings',
  'Generating report',
  'Complete',
];

function stageIndex(stage: string | null): number {
  if (!stage) return 0;
  const idx = STAGES.findIndex((s) => s.toLowerCase() === stage.toLowerCase());
  return idx >= 0 ? idx : 0;
}

function formatElapsed(startedAt: string | null): string {
  if (!startedAt) return '00:00';
  const elapsed = Math.floor((Date.now() - new Date(startedAt).getTime()) / 1000);
  const mins = Math.floor(elapsed / 60);
  const secs = elapsed % 60;
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

interface RunStatusCardProps {
  projectId: string;
  initialRun: ResearchRun;
  liveRun?: ResearchRun | null;
  sseConnected?: boolean;
  onRunCompleted?: () => void;
}

export function RunStatusCard({
  projectId,
  initialRun,
  liveRun,
  sseConnected = false,
  onRunCompleted,
}: RunStatusCardProps) {
  const router = useRouter();
  const [run, setRun] = useState<ResearchRun>(initialRun);
  const [elapsed, setElapsed] = useState('');
  const onRunCompletedRef = useRef(onRunCompleted);
  useEffect(() => {
    onRunCompletedRef.current = onRunCompleted;
  });

  useEffect(() => {
    if (liveRun) {
      setRun(liveRun);
    }
  }, [liveRun]);

  useEffect(() => {
    setElapsed(formatElapsed(run.started_at));
    const ticker = setInterval(() => {
      setElapsed(formatElapsed(run.started_at));
    }, 1000);
    return () => clearInterval(ticker);
  }, [run.started_at]);

  useEffect(() => {
    const isActive =
      run.status === 'pending' || run.status === 'running' || run.status === 'awaiting_approval';
    if (sseConnected || !isActive) return;

    const interval = setInterval(async () => {
      try {
        const updated = await getRun(projectId, run.id);
        setRun(updated);
        if (updated.status === 'completed' || updated.status === 'failed') {
          clearInterval(interval);
          if (onRunCompletedRef.current) {
            onRunCompletedRef.current();
          } else {
            router.refresh();
          }
        }
      } catch {
        // backend unreachable — keep polling
      }
    }, FALLBACK_POLL_INTERVAL);

    return () => clearInterval(interval);
  }, [run.id, run.status, projectId, sseConnected, router]);

  const prevStatusRef = useRef(run.status);
  useEffect(() => {
    const prev = prevStatusRef.current;
    prevStatusRef.current = run.status;
    if (
      (prev === 'running' || prev === 'awaiting_approval' || prev === 'pending') &&
      (run.status === 'completed' || run.status === 'failed')
    ) {
      if (onRunCompletedRef.current) onRunCompletedRef.current();
    }
  }, [run.status]);

  const stageIdx = stageIndex(run.current_stage);
  const isActive =
    run.status === 'pending' || run.status === 'running' || run.status === 'awaiting_approval';
  const isAwaitingApproval = run.status === 'awaiting_approval';
  const isCompleted = run.status === 'completed';
  const isFailed = run.status === 'failed';

  function statusIcon() {
    if (isAwaitingApproval) return <Hourglass className="h-4 w-4 text-amber-400 animate-pulse" />;
    if (isActive) return <Loader2 className="h-4 w-4 text-blue-400 animate-spin" />;
    if (isCompleted) return <CheckCircle2 className="h-4 w-4 text-emerald-400" />;
    return <AlertCircle className="h-4 w-4 text-red-400" />;
  }

  function statusTitle() {
    if (isAwaitingApproval) return 'PIPELINE PAUSED // AWAITING APPROVAL';
    if (isActive) return 'LINEAR EXECUTION // IN PROGRESS';
    if (isCompleted) return 'LINEAR EXECUTION // COMPLETE';
    return 'LINEAR EXECUTION // HALTED';
  }

  function progressBarColor(i: number): string {
    if (i > stageIdx) return 'bg-slate-800';
    if (isFailed) return 'bg-red-400';
    if (isAwaitingApproval) return 'bg-amber-400';
    return 'bg-blue-500';
  }

  return (
    <Card className="tech-panel border-slate-700 bg-slate-900 shadow-2xl relative overflow-hidden">
      <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-blue-500/20 via-blue-500/60 to-transparent" />

      <CardHeader className="pb-3 border-b border-slate-800">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <CardTitle className="font-mono text-xs font-bold text-white flex items-center gap-2">
            {statusIcon()}
            <span>{statusTitle()}</span>
          </CardTitle>

          <div className="flex items-center gap-2 font-mono text-xs font-semibold">
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-md border border-slate-700 bg-slate-950 text-blue-300">
              <Cpu className="h-3.5 w-3.5 text-blue-400" />
              <span>PRIMARY: GEMINI 3.1</span>
            </div>
            <Badge
              variant="outline"
              className={`font-mono text-xs uppercase tracking-wider px-2.5 py-0.5 font-bold ${
                isCompleted
                  ? 'border-emerald-500/50 bg-emerald-500/20 text-emerald-300'
                  : isFailed
                  ? 'border-red-500/50 bg-red-500/20 text-red-300'
                  : isAwaitingApproval
                  ? 'border-amber-500/50 bg-amber-500/20 text-amber-300'
                  : 'border-blue-500/50 bg-blue-500/20 text-blue-300'
              }`}
            >
              {isAwaitingApproval ? 'PAUSED' : run.status}
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-4">
        {/* Current stage */}
        <div>
          <div className="flex items-center justify-between font-mono text-xs text-slate-200 mb-2">
            <span className="uppercase tracking-wider font-bold">CURRENT STAGE</span>
            <span className="text-white font-bold">{run.current_stage ?? 'Waiting to dispatch…'}</span>
          </div>

          {/* Stage indicator */}
          <div className="flex gap-1.5">
            {STAGES.map((s, i) => (
              <div
                key={s}
                className={`h-2 flex-1 rounded-full transition-all duration-300 ${progressBarColor(i)}`}
                title={s}
              />
            ))}
          </div>
        </div>

        {/* Awaiting approval notice */}
        {isAwaitingApproval && (
          <div className="rounded-lg border border-amber-500/40 bg-amber-500/15 p-3.5 font-mono text-xs text-amber-200 font-semibold">
            This run is paused and requires your review before proceeding.
          </div>
        )}

        {/* Error message */}
        {isFailed && run.error_message && (
          <div className="rounded-lg border border-red-500/40 bg-red-500/15 p-3.5 font-mono text-xs text-red-200 font-semibold">
            {run.error_message}
          </div>
        )}

        {/* Timing and metadata */}
        <div className="flex items-center justify-between border-t border-slate-800 pt-3 font-mono text-xs text-slate-200">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-cyan-400" />
            <span className="font-bold text-white tabular-nums text-sm">{elapsed || '00:00'}</span>
            <span className="text-xs text-slate-300 font-medium">
              ({sseConnected ? 'SSE LIVE' : 'REST POLL'})
            </span>
          </div>
          <div className="flex items-center gap-2.5">
            {run.total_tokens_used > 0 && (
              <a
                href="/tokens"
                title="View in Token Tracker"
                className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-sky-500/10 border border-sky-500/30 text-sky-300 font-mono text-[11px] hover:bg-sky-500/20 transition-colors"
              >
                <Zap className="h-3 w-3 text-sky-400" />
                <span>{run.total_tokens_used.toLocaleString()} tok</span>
              </a>
            )}
            <span className="text-xs text-slate-300 uppercase font-semibold">Single-Pass Workflow</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
