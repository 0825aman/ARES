'use client';

import { useEffect, useRef, useState } from 'react';
import {
  Loader2,
  Clock,
  AlertCircle,
  CheckCircle2,
  Hourglass,
  Cpu,
  Settings2,
  Search,
  ShieldAlert,
  FileCheck2,
  Network,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { getRun } from '@/lib/api/runs';
import { ResearchPlanView } from './ResearchPlanView';
import { AgentActivityFeed } from './AgentActivityFeed';
import type { ResearchRun, AgentEvent } from '@/lib/types/run';

const POLL_INTERVAL = 3000;

interface StageDefinition {
  id: string;
  label: string;
  description: string;
  icon: React.ElementType;
}

const SWARM_STAGES: StageDefinition[] = [
  { id: 'initializing', label: 'INIT', description: 'Core Setup', icon: Cpu },
  { id: 'planning', label: 'PLAN', description: 'DAG Planning', icon: Settings2 },
  { id: 'researching', label: 'RESEARCH', description: 'Evidence Retrieval', icon: Search },
  { id: 'finalizing', label: 'CRITIQUE', description: 'Adversarial Review', icon: ShieldAlert },
  { id: 'complete', label: 'SYNTHESIS', description: 'Report Synthesis', icon: FileCheck2 },
];

function stageIndex(stage: string | null): number {
  if (!stage) return 0;
  const s = stage.toLowerCase();
  const idx = SWARM_STAGES.findIndex((st) => st.id === s || st.label.toLowerCase() === s);
  if (idx >= 0) return idx;
  if (s.includes('plan')) return 1;
  if (s.includes('res') || s.includes('gather')) return 2;
  if (s.includes('crit') || s.includes('rev') || s.includes('final')) return 3;
  if (s.includes('comp') || s.includes('done')) return 4;
  return 0;
}

function formatElapsed(startedAt: string | null, createdAt?: string | null): string {
  const ref = startedAt || createdAt;
  if (!ref) return '00:00';
  const elapsed = Math.max(0, Math.floor((Date.now() - new Date(ref).getTime()) / 1000));
  const mins = Math.floor(elapsed / 60);
  const secs = elapsed % 60;
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

interface MultiAgentStatusCardProps {
  projectId: string;
  initialRun: ResearchRun;
  liveRun?: ResearchRun | null;
  liveEvents?: AgentEvent[];
  sseConnected?: boolean;
  onRunCompleted?: () => void;
}

export function MultiAgentStatusCard({
  projectId,
  initialRun,
  liveRun,
  liveEvents,
  sseConnected = false,
  onRunCompleted,
}: MultiAgentStatusCardProps) {
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
    setElapsed(formatElapsed(run.started_at, run.created_at));
    const ticker = setInterval(() => {
      setElapsed(formatElapsed(run.started_at, run.created_at));
    }, 1000);
    return () => clearInterval(ticker);
  }, [run.started_at, run.created_at]);

  useEffect(() => {
    const isActiveStatus =
      run.status === 'pending' || run.status === 'running' || run.status === 'awaiting_approval';
    if (!isActiveStatus) return;

    const interval = setInterval(async () => {
      try {
        const updated = await getRun(projectId, run.id);
        setRun(updated);
        if (updated.status === 'completed' || updated.status === 'failed') {
          clearInterval(interval);
          if (onRunCompletedRef.current) onRunCompletedRef.current();
        }
      } catch {
        // backend unreachable — keep polling
      }
    }, POLL_INTERVAL);

    return () => clearInterval(interval);
  }, [run.id, run.status, projectId]);

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

  const currentIdx = stageIndex(run.current_stage);
  const isActive =
    run.status === 'pending' || run.status === 'running' || run.status === 'awaiting_approval';
  const isAwaitingApproval = run.status === 'awaiting_approval';
  const isCompleted = run.status === 'completed';
  const isFailed = run.status === 'failed';

  return (
    <div className="space-y-4">
      {/* Run status header */}
      <Card className="tech-panel border-slate-700 bg-slate-900 shadow-2xl relative overflow-hidden">
        {/* Top subtle glow line */}
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-blue-500/20 via-blue-500/60 to-purple-500/20" />

        <CardHeader className="pb-3 border-b border-slate-800">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <CardTitle className="text-sm font-mono font-bold text-white flex items-center gap-2">
              {isAwaitingApproval ? (
                <Hourglass className="h-4 w-4 text-amber-400 animate-pulse" />
              ) : isActive ? (
                <Loader2 className="h-4 w-4 text-blue-400 animate-spin" />
              ) : isCompleted ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              ) : (
                <AlertCircle className="h-4 w-4 text-red-400" />
              )}
              <span>
                {isAwaitingApproval
                  ? 'SWARM STATUS // AWAITING APPROVAL'
                  : isActive
                  ? 'SWARM STATUS // EXECUTING AUTONOMOUS MISSION'
                  : isCompleted
                  ? 'SWARM STATUS // MISSION SYNTHESIS VERIFIED'
                  : 'SWARM STATUS // EXECUTION HALTED'}
              </span>
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

        <CardContent className="space-y-5 pt-4">
          {/* Visual Swarm Pipeline Node Graph Stepper */}
          <div className="space-y-2.5">
            <div className="flex items-center justify-between font-mono text-xs text-slate-200 pb-1">
              <span className="flex items-center gap-2 uppercase tracking-wider font-bold">
                <Network className="h-4 w-4 text-cyan-400" />
                Pipeline Node Execution Graph
              </span>
              <span className="text-slate-300 font-semibold">
                Stage {Math.min(currentIdx + 1, 5)} of 5
              </span>
            </div>

            <div className="grid grid-cols-5 gap-2.5 relative">
              {SWARM_STAGES.map((st, i) => {
                const Icon = st.icon;
                const isPast = isCompleted || i < currentIdx;
                const isCurrent = !isCompleted && !isFailed && i === currentIdx;
                const isStepFailed = isFailed && i === currentIdx;

                return (
                  <div
                    key={st.id}
                    className={`relative rounded-lg p-3 border transition-all duration-300 flex flex-col justify-between ${
                      isPast
                        ? 'border-emerald-500/40 bg-emerald-500/10 text-white'
                        : isCurrent
                        ? 'border-blue-500/80 bg-blue-500/20 shadow-[0_0_15px_rgba(59,130,246,0.25)] text-white'
                        : isStepFailed
                        ? 'border-red-500/60 bg-red-500/15 text-red-200'
                        : 'border-slate-800 bg-slate-950 text-slate-400'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-mono text-[10px] font-bold text-slate-300">
                        0{i + 1}
                      </span>
                      {isPast ? (
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                      ) : isCurrent ? (
                        <span className="h-2.5 w-2.5 rounded-full bg-blue-400 animate-pulse shrink-0" />
                      ) : isStepFailed ? (
                        <AlertCircle className="h-3.5 w-3.5 text-red-400 shrink-0" />
                      ) : (
                        <span className="h-1.5 w-1.5 rounded-full bg-slate-600 shrink-0" />
                      )}
                    </div>

                    <div>
                      <div className="flex items-center gap-1.5">
                        <Icon
                          className={`h-4 w-4 ${
                            isPast
                              ? 'text-emerald-400'
                              : isCurrent
                              ? 'text-blue-300'
                              : isStepFailed
                              ? 'text-red-400'
                              : 'text-slate-500'
                          }`}
                        />
                        <span className="font-mono text-xs font-bold tracking-tight text-white truncate">
                          {st.label}
                        </span>
                      </div>
                      <p className="font-mono text-[10px] text-slate-300 truncate mt-1 hidden sm:block font-medium">
                        {st.description}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Telemetry bar: Clock, Question, Warnings */}
          <div className="grid grid-cols-1 sm:grid-cols-12 gap-4 pt-2 border-t border-slate-800">
            <div className="sm:col-span-8 space-y-1">
              <span className="font-mono text-xs text-slate-300 uppercase tracking-wider font-bold">
                Objective Query
              </span>
              <p className="font-mono text-xs text-white leading-relaxed line-clamp-2 font-medium">
                {run.research_question}
              </p>
            </div>

            <div className="sm:col-span-4 flex flex-col justify-end items-start sm:items-end space-y-1 font-mono text-xs">
              <span className="text-xs text-slate-300 uppercase tracking-wider font-bold">
                Execution Elapsed
              </span>
              <div className="flex items-center gap-1.5 text-white">
                <Clock className="h-4 w-4 text-cyan-400" />
                <span className="font-bold tabular-nums text-sm">{elapsed || '00:00'}</span>
                <span className="text-slate-300 text-xs ml-1 font-medium">
                  ({sseConnected ? 'SSE LIVE' : 'REST POLL'})
                </span>
              </div>
            </div>
          </div>

          {/* Awaiting approval notice */}
          {isAwaitingApproval && (
            <div className="rounded-lg border border-amber-500/40 bg-amber-500/15 p-3.5 font-mono text-xs text-amber-200 flex items-center gap-2 font-semibold">
              <Hourglass className="h-4 w-4 shrink-0 text-amber-400" />
              <span>
                HUMAN-IN-THE-LOOP INTERVENTION: Execution paused. Awaiting plan approval to proceed.
              </span>
            </div>
          )}

          {/* Error message */}
          {isFailed && run.error_message && (
            <div className="rounded-lg border border-red-500/40 bg-red-500/15 p-3.5 font-mono text-xs text-red-200 flex items-center gap-2 font-semibold">
              <AlertCircle className="h-4 w-4 shrink-0 text-red-400" />
              <span>{run.error_message}</span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Research plan with task breakdown */}
      <ResearchPlanView
        projectId={projectId}
        runId={run.id}
        pollingInterval={isActive ? 3000 : 10000}
      />

      {/* Agent activity timeline */}
      <AgentActivityFeed
        projectId={projectId}
        runId={run.id}
        liveEvents={liveEvents}
        sseConnected={sseConnected}
        runCompleted={!isActive}
      />
    </div>
  );
}
