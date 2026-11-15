'use client';

import Link from 'next/link';
import { Globe, FileText, ChevronRight } from 'lucide-react';
import { StatusBadge } from '@/components/projects/StatusBadge';
import type { ResearchRun } from '@/lib/types/run';
import type { ProjectStatus } from '@/lib/types/project';

// StatusBadge accepts ProjectStatus but RunStatus overlaps for completed/in_progress
// Create a mapping:
function runStatusToProjectStatus(status: string): ProjectStatus {
  if (status === 'completed') return 'completed';
  if (status === 'running' || status === 'pending') return 'in_progress';
  return 'not_started';
}

interface RunHistoryProps {
  projectId: string;
  runs: ResearchRun[];
}

export function RunHistory({ projectId, runs }: RunHistoryProps) {
  if (runs.length === 0) {
    return <p className="text-sm text-slate-400 py-4 text-center">No previous research runs.</p>;
  }

  return (
    <div className="divide-y divide-slate-100">
      {runs.map((run) => (
        <div key={run.id} className="flex items-center gap-3 py-3">
          <StatusBadge status={runStatusToProjectStatus(run.status)} />
          <div className="flex-1 min-w-0">
            <p className="text-xs text-slate-700 truncate">{run.research_question}</p>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-[10px] text-slate-400">
                {new Date(run.created_at).toLocaleDateString()}
              </span>
              {run.use_web && <Globe className="h-3 w-3 text-slate-400" />}
              {run.use_documents && <FileText className="h-3 w-3 text-slate-400" />}
            </div>
          </div>
          {run.status === 'completed' && (
            <Link
              href={`/projects/${projectId}/runs/${run.id}`}
              className="text-xs text-blue-600 hover:underline flex items-center gap-0.5 shrink-0"
            >
              View <ChevronRight className="h-3 w-3" />
            </Link>
          )}
        </div>
      ))}
    </div>
  );
}
