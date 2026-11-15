'use client';

import Link from 'next/link';
import { Layers, ExternalLink, CheckCircle2, AlertCircle } from 'lucide-react';
import type { TopRunToken } from '@/lib/types/token';

interface MissionTokenLeaderboardProps {
  runs: TopRunToken[];
  totalTokens: number;
}

export function MissionTokenLeaderboard({ runs, totalTokens }: MissionTokenLeaderboardProps) {
  if (!runs || runs.length === 0) {
    return null;
  }

  const maxRunTokens = Math.max(...runs.map((r) => r.tokens), 1);

  return (
    <div className="tech-panel rounded-xl border border-slate-800 bg-slate-900/90 p-5 shadow-xl">
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-4 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <Layers className="h-4 w-4 text-sky-400" />
            <h3 className="font-mono text-sm font-bold uppercase tracking-wider text-white">
              Research Mission Token Consumption Leaderboard
            </h3>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Ranked token consumption by individual autonomous research mission
          </p>
        </div>
        <span className="text-xs font-mono text-slate-400">
          Showing Top {runs.length} Missions
        </span>
      </div>

      <div className="space-y-3.5">
        {runs.map((run, idx) => {
          const barWidth = Math.max((run.tokens / maxRunTokens) * 100, 4);

          return (
            <div
              key={run.run_id}
              className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80 hover:border-slate-700 transition-colors"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                <div className="flex items-center gap-2.5 min-w-0">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-slate-800 text-[10px] font-mono font-bold text-slate-300">
                    {idx + 1}
                  </span>
                  <Link
                    href={`/projects/${run.project_id}/runs/${run.run_id}`}
                    className="font-mono text-xs font-bold text-white hover:text-sky-300 hover:underline flex items-center gap-1 truncate"
                  >
                    <span className="truncate">{run.project_title}</span>
                    <ExternalLink className="h-3 w-3 shrink-0 text-slate-400" />
                  </Link>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 uppercase">
                    {run.project_category}
                  </span>
                </div>

                <div className="flex items-center gap-3 shrink-0 font-mono text-xs">
                  {run.status === 'completed' ? (
                    <span className="flex items-center gap-1 text-[10px] text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                      <CheckCircle2 className="h-3 w-3" />
                      COMPLETED
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-[10px] text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20">
                      <AlertCircle className="h-3 w-3" />
                      {run.status.toUpperCase()}
                    </span>
                  )}
                  <span className="text-slate-400">{run.calls} calls</span>
                  <span className="font-bold text-sky-400">
                    {run.tokens.toLocaleString()} tok
                  </span>
                  <span className="text-[11px] text-slate-500">
                    ({run.percentage}%)
                  </span>
                </div>
              </div>

              {/* Research Question Snippet */}
              <p className="text-xs text-slate-300 line-clamp-1 mb-2 font-sans font-normal">
                {run.research_question}
              </p>

              {/* Progress Bar */}
              <div className="h-2 w-full rounded-full bg-slate-900 overflow-hidden">
                <div
                  style={{ width: `${barWidth}%` }}
                  className="h-full rounded-full bg-gradient-to-r from-sky-600 via-blue-500 to-indigo-500"
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
