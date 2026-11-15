'use client';

import { useEffect, useState } from 'react';
import {
  CheckCircle2,
  Circle,
  Loader2,
  XCircle,
  AlertCircle,
  ChevronDown,
  ChevronRight,
  Settings2,
  Terminal,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { getPlan } from '@/lib/api/runs';
import type { ResearchPlan, ResearchTask } from '@/lib/types/run';

interface ResearchPlanViewProps {
  projectId: string;
  runId: string;
  pollingInterval?: number;
}

function TaskStatusIcon({ status }: { status: ResearchTask['status'] }) {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />;
    case 'partial':
      return <AlertCircle className="h-4 w-4 text-amber-400 shrink-0" />;
    case 'failed':
    case 'fatal_error':
      return <XCircle className="h-4 w-4 text-red-400 shrink-0" />;
    case 'running':
      return <Loader2 className="h-4 w-4 text-blue-400 animate-spin shrink-0" />;
    default:
      return <Circle className="h-4 w-4 text-slate-500 shrink-0" />;
  }
}

function taskStatusBadge(status: ResearchTask['status']) {
  const variants: Record<ResearchTask['status'], { label: string; className: string }> = {
    pending: {
      label: 'PENDING',
      className: 'bg-slate-800 text-slate-200 border-slate-700',
    },
    running: {
      label: 'EXECUTING',
      className: 'bg-blue-500/20 text-blue-300 border-blue-500/50 shadow-[0_0_8px_rgba(59,130,246,0.25)]',
    },
    completed: {
      label: 'VERIFIED',
      className: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/50 shadow-[0_0_8px_rgba(16,185,129,0.25)]',
    },
    partial: {
      label: 'PARTIAL',
      className: 'bg-amber-500/20 text-amber-300 border-amber-500/50',
    },
    failed: {
      label: 'FAILED',
      className: 'bg-red-500/20 text-red-300 border-red-500/50',
    },
    fatal_error: {
      label: 'FATAL',
      className: 'bg-red-500/30 text-red-200 border-red-500/60 font-bold',
    },
  };
  const v = variants[status] ?? variants.pending;
  return (
    <span
      className={`font-mono text-xs font-bold uppercase tracking-wider px-2.5 py-0.5 rounded border ${v.className}`}
    >
      {v.label}
    </span>
  );
}

function TaskRow({ task, index }: { task: ResearchTask; index: number }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-slate-800 rounded-lg overflow-hidden bg-slate-950/60 hover:bg-slate-950 transition-all">
      <button
        className="w-full flex items-start gap-3 px-4 py-3.5 text-left hover:bg-slate-900/60 transition-colors"
        onClick={() => setExpanded((e) => !e)}
      >
        <div className="pt-0.5">
          <TaskStatusIcon status={task.status} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs text-blue-300 font-bold">
              TASK 0{index + 1}
            </span>
            <p className="text-xs font-bold text-white leading-snug">
              {task.objective}
            </p>
          </div>
          <p className="font-mono text-xs text-cyan-300 mt-1 truncate font-medium">
            ❯ {task.search_query}
          </p>
        </div>
        <div className="flex items-center gap-2.5 shrink-0 pt-0.5">
          {taskStatusBadge(task.status)}
          {task.evidence_count > 0 && (
            <span className="font-mono text-xs text-slate-200 border border-slate-700 px-2 py-0.5 rounded bg-slate-900 font-medium">
              {task.evidence_count} evidence
            </span>
          )}
          {expanded ? (
            <ChevronDown className="h-4 w-4 text-slate-300" />
          ) : (
            <ChevronRight className="h-4 w-4 text-slate-300" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-3.5 pt-3 border-t border-slate-800 bg-slate-950 space-y-3 font-mono text-xs">
          {task.findings && (
            <div>
              <p className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-1.5">
                Extracted Findings
              </p>
              <p className="text-slate-100 leading-relaxed font-sans text-xs font-normal">
                {task.findings}
              </p>
            </div>
          )}
          {task.error_message && (
            <div className="border border-red-500/40 bg-red-500/15 p-3 rounded text-red-200">
              <p className="text-xs font-bold uppercase tracking-wider mb-1">
                Execution Fault
              </p>
              <p className="text-xs">{task.error_message}</p>
            </div>
          )}
          {task.unanswered_questions.length > 0 && (
            <div>
              <p className="text-xs font-bold text-amber-300 uppercase tracking-wider mb-1.5">
                Unanswered Queries
              </p>
              <ul className="space-y-1">
                {task.unanswered_questions.map((q, i) => (
                  <li key={i} className="text-xs text-slate-200 flex gap-2">
                    <span className="text-amber-400 font-bold">❯</span>
                    <span>{q}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {!task.findings && !task.error_message && task.status === 'pending' && (
            <p className="text-slate-400 italic">Queued in execution sequence…</p>
          )}
        </div>
      )}
    </div>
  );
}

export function ResearchPlanView({
  projectId,
  runId,
  pollingInterval = 4000,
}: ResearchPlanViewProps) {
  const [plan, setPlan] = useState<ResearchPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function fetchPlan() {
      try {
        const data = await getPlan(projectId, runId);
        if (!cancelled) {
          setPlan(data);
          setLoading(false);
          setNotFound(false);
        }
      } catch (err: unknown) {
        if (!cancelled) {
          const status = (err as { status?: number })?.status;
          if (status === 404) {
            setNotFound(true);
          }
          setLoading(false);
        }
      }
    }

    fetchPlan();
    const interval = setInterval(fetchPlan, pollingInterval);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [projectId, runId, pollingInterval]);

  if (loading) {
    return (
      <Card className="tech-panel border-slate-800 bg-slate-900 shadow-lg">
        <CardHeader className="py-3 px-5 border-b border-slate-800">
          <CardTitle className="font-mono text-xs font-bold uppercase tracking-wider text-slate-200 flex items-center gap-2">
            <Settings2 className="h-4 w-4 text-blue-400" />
            Loading Plan DAG…
          </CardTitle>
        </CardHeader>
        <CardContent className="p-5 space-y-2">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-12 rounded-lg bg-slate-950 border border-slate-800 animate-pulse"
            />
          ))}
        </CardContent>
      </Card>
    );
  }

  if (notFound || !plan) {
    return (
      <Card className="tech-panel border-slate-800 bg-slate-900 shadow-lg">
        <CardContent className="py-8 text-center">
          <div className="flex flex-col items-center gap-2 text-slate-300 font-mono text-xs font-medium">
            <Loader2 className="h-5 w-5 text-blue-400 animate-spin" />
            <p>Planner Agent formulating investigation DAG…</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const completedCount = plan.tasks.filter((t) =>
    ['completed', 'partial'].includes(t.status),
  ).length;
  const totalCount = plan.tasks.length;

  return (
    <Card className="tech-panel border-slate-800 bg-slate-900 shadow-lg">
      <CardHeader className="py-3 px-5 border-b border-slate-800">
        <div className="flex items-center justify-between">
          <CardTitle className="font-mono text-xs font-bold uppercase tracking-wider text-white flex items-center gap-2">
            <Terminal className="h-4 w-4 text-blue-400" />
            Research Plan DAG
            <span className="text-xs text-blue-300 font-bold ml-1">
              [{completedCount}/{totalCount} TASKS DONE]
            </span>
          </CardTitle>
          <div className="flex items-center gap-2 font-mono text-xs font-bold">
            {plan.plan_version > 1 && (
              <Badge
                variant="outline"
                className="border-slate-700 bg-slate-800 text-slate-200 px-2 py-0.5"
              >
                v{plan.plan_version}
              </Badge>
            )}
            <span className="telemetry-chip font-mono text-xs text-emerald-300 border-emerald-500/40 bg-emerald-500/20 font-bold">
              ACTIVE
            </span>
          </div>
        </div>

        {plan.objectives.length > 0 && (
          <div className="mt-3 pt-2.5 border-t border-slate-800 font-mono text-xs">
            <p className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
              Decomposed Objectives
            </p>
            <ul className="space-y-1.5">
              {plan.objectives.map((obj, i) => (
                <li key={i} className="text-xs text-slate-100 flex items-start gap-2.5 font-normal">
                  <span className="text-blue-400 font-bold shrink-0">❯</span>
                  <span className="leading-snug">{obj}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardHeader>
      <CardContent className="p-4 space-y-2">
        {plan.tasks.map((task, idx) => (
          <TaskRow key={task.id} task={task} index={idx} />
        ))}
      </CardContent>
    </Card>
  );
}
