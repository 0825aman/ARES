'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Plus, Terminal } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { ProjectGrid } from './ProjectGrid';
import { getProjects } from '@/lib/api/projects';
import type { ProjectListResponse } from '@/lib/types/project';

export function ProjectsClient() {
  const [data, setData] = useState<ProjectListResponse | null | 'loading'>('loading');

  useEffect(() => {
    getProjects({ limit: 100 })
      .then(setData)
      .catch(() => setData(null));
  }, []);

  if (data === 'loading') {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <Skeleton className="h-44 w-full bg-slate-900 border border-slate-800 rounded-xl" />
        <Skeleton className="h-44 w-full bg-slate-900 border border-slate-800 rounded-xl" />
        <Skeleton className="h-44 w-full bg-slate-900 border border-slate-800 rounded-xl" />
      </div>
    );
  }

  if (data === null) {
    return (
      <div className="rounded-lg border border-amber-500/50 bg-amber-500/15 px-4 py-3 font-mono text-xs text-amber-200 font-semibold">
        Cannot reach the backend API. Verify the backend daemon is running at{' '}
        <code className="text-amber-100 underline">localhost:8000</code>, then refresh this view.
      </div>
    );
  }

  if (data.total === 0) {
    return (
      <div className="tech-panel flex flex-col items-center justify-center py-20 text-center px-6 max-w-lg mx-auto">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-slate-700 bg-slate-950 mb-4 shadow-inner">
          <Terminal className="h-6 w-6 text-blue-400" />
        </div>
        <h2 className="font-mono text-base font-bold text-white mb-2">
          NO MISSIONS REGISTERED
        </h2>
        <p className="text-xs text-slate-200 max-w-xs mb-6 font-mono leading-relaxed">
          The autonomous research ledger is currently empty. Dispatch a new multi-agent investigation.
        </p>
        <Button
          asChild
          size="sm"
          className="bg-blue-600 hover:bg-blue-500 text-white font-mono text-xs font-bold border border-blue-400/40 shadow-lg shadow-blue-500/20 px-4 py-2"
        >
          <Link href="/projects/new">
            <Plus className="h-4 w-4 mr-1.5" />
            INITIALIZE MISSION
          </Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between font-mono text-xs text-slate-200 font-bold pb-1">
        <span>ACTIVE RESEARCH MISSIONS ({data.total})</span>
      </div>
      <ProjectGrid projects={data.items} />
    </div>
  );
}
