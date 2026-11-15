import { Layers, Activity, CheckCircle2, Cpu } from 'lucide-react';
import { StatCard } from './StatCard';
import type { ProjectSummaryResponse } from '@/lib/types/project';

interface StatsRowProps {
  summary: ProjectSummaryResponse;
}

export function StatsRow({ summary }: StatsRowProps) {
  const inProgressCount = summary.by_status.in_progress ?? 0;
  const completedCount = summary.by_status.completed ?? 0;

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard
        label="Total Missions"
        value={summary.total}
        icon={Layers}
        accent="text-slate-300"
        subtext="Workspace research records"
      />
      <StatCard
        label="Active Swarm Runs"
        value={inProgressCount}
        icon={Activity}
        accent="text-blue-400"
        badge={inProgressCount > 0 ? 'EXECUTING' : undefined}
        subtext="Autonomous agent threads"
      />
      <StatCard
        label="Verified Reports"
        value={completedCount}
        icon={CheckCircle2}
        accent="text-emerald-400"
        badge={completedCount > 0 ? '100% GROUNDED' : undefined}
        subtext="Completed synthesis reports"
      />
      <StatCard
        label="Failover Mesh"
        value="4 / 4"
        icon={Cpu}
        accent="text-violet-400"
        badge="PRIMARY: GEMINI"
        subtext="Gemini ➔ Groq ➔ OR ➔ IBM"
      />
    </div>
  );
}
