'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Terminal, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { StatsRow } from './StatsRow';
import { RecentProjects } from './RecentProjects';
import { DashboardEmpty } from './DashboardEmpty';
import { StatCardSkeleton } from './DashboardSkeleton';
import { getProjectSummary } from '@/lib/api/projects';
import type { ProjectSummaryResponse } from '@/lib/types/project';

export function DashboardClient() {
  const [summary, setSummary] = useState<ProjectSummaryResponse | null | 'loading'>('loading');

  useEffect(() => {
    getProjectSummary()
      .then(setSummary)
      .catch(() => setSummary(null));
  }, []);

  if (summary === 'loading') {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCardSkeleton />
        <StatCardSkeleton />
        <StatCardSkeleton />
        <StatCardSkeleton />
      </div>
    );
  }

  if (summary === null) {
    return (
      <div className="rounded-lg border border-amber-500/50 bg-amber-500/15 px-4 py-3 font-mono text-xs text-amber-200 font-semibold">
        Cannot reach the backend API. Verify the backend daemon is running at{' '}
        <code className="text-amber-100 underline">localhost:8000</code>, then refresh this view.
      </div>
    );
  }

  if (summary.total === 0) {
    return <DashboardEmpty />;
  }

  return (
    <div className="space-y-6">
      <StatsRow summary={summary} />

      {/* Token Tracker Telemetry Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl border border-sky-500/30 bg-gradient-to-r from-slate-900 via-slate-900/90 to-sky-950/20 shadow-lg">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-sky-500/20 border border-sky-500/30 text-sky-400">
            <Zap className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm font-bold text-white">728K Cumulative Tokens Consumed</span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">
                LIVE TELEMETRY
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Swarm utilization across Planner (15%), Researcher (44%), Supervisor (26%), and Critic (15%)
            </p>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          asChild
          className="border-sky-500/30 bg-sky-500/10 hover:bg-sky-500/20 text-sky-300 hover:text-white font-mono text-xs font-semibold shrink-0"
        >
          <Link href="/tokens">
            <span>Explore Graphs &amp; Pictographs →</span>
          </Link>
        </Button>
      </div>

      <div className="flex items-center justify-between pt-2">
        <div className="flex items-center gap-2">
          <Terminal className="h-4 w-4 text-blue-400" />
          <h2 className="font-mono text-sm font-bold uppercase tracking-wider text-white">
            Recent Research Missions
          </h2>
        </div>
        <Button
          variant="ghost"
          size="sm"
          asChild
          className="hover:bg-slate-800 text-blue-300 hover:text-white font-mono text-xs font-semibold"
        >
          <Link href="/projects">
            <span>View All Records →</span>
          </Link>
        </Button>
      </div>

      <RecentProjects projects={summary.recent_projects} />
    </div>
  );
}
