'use client';

import { Users, Bot, GitCommit, CheckCircle2, Split, ArrowRightLeft, Sparkles, AlertCircle } from 'lucide-react';
import type { MultiAgentSystemMetrics } from '@/lib/types/evaluation';

interface MultiAgentSwarmSectionProps {
  metrics: MultiAgentSystemMetrics;
}

export function MultiAgentSwarmSection({ metrics }: MultiAgentSwarmSectionProps) {
  const swarmHighLevel = [
    {
      label: 'End-to-End Completion',
      value: (metrics.end_to_end_completion_rate * 100).toFixed(1) + '%',
      sub: 'Entire 4-agent graph run',
    },
    {
      label: 'Supervisor Routing Accuracy',
      value: (metrics.supervisor_agent_accuracy * 100).toFixed(1) + '%',
      sub: 'Optimal node routing decisions',
    },
    {
      label: 'Conflict Resolution Rate',
      value: (metrics.conflict_resolution_rate * 100).toFixed(1) + '%',
      sub: 'Contradiction reconciliation',
    },
    {
      label: 'Inter-Agent Consistency',
      value: (metrics.inter_agent_consistency * 100).toFixed(1) + '%',
      sub: 'Researcher-Critic score alignment',
    },
    {
      label: 'Task Distribution Efficiency',
      value: (metrics.task_distribution_efficiency * 100).toFixed(1) + '%',
      sub: 'Even swarm workload distribution',
    },
    {
      label: 'Communication Success',
      value: (metrics.communication_success_rate * 100).toFixed(1) + '%',
      sub: 'Zero state transfer loss',
    },
  ];

  const agentRoleColors: Record<string, { border: string; text: string; bg: string }> = {
    planner: { border: 'border-cyan-500/30', text: 'text-cyan-400', bg: 'bg-cyan-500/10' },
    researcher: { border: 'border-emerald-500/30', text: 'text-emerald-400', bg: 'bg-emerald-500/10' },
    supervisor: { border: 'border-violet-500/30', text: 'text-violet-400', bg: 'bg-violet-500/10' },
    critic: { border: 'border-amber-500/30', text: 'text-amber-400', bg: 'bg-amber-500/10' },
  };

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-base font-bold text-white flex items-center gap-2">
          <Users className="h-5 w-5 text-violet-400" />
          6. Multi-Agent System Evaluation (Swarm Coordination &amp; Individual Scorecards)
        </h3>
        <p className="text-xs text-slate-400">
          Evaluates multi-agent orchestration across Planner, Researcher, Supervisor, and Critic agents, measuring conflict resolution and individual accuracy
        </p>
      </div>

      {/* High Level Swarm Metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {swarmHighLevel.map((m, idx) => (
          <div key={idx} className="p-3.5 rounded-lg bg-slate-900/80 border border-slate-800">
            <span className="text-[10px] font-mono text-slate-400 uppercase block truncate">{m.label}</span>
            <div className="text-xl font-bold font-mono text-white mt-1">{m.value}</div>
            <span className="text-[9px] text-slate-500 mt-1 block truncate font-mono">{m.sub}</span>
          </div>
        ))}
      </div>

      {/* Individual Agent Scorecards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 pt-1">
        {Object.entries(metrics.agents).map(([agentKey, agent]) => {
          const color = agentRoleColors[agentKey] || {
            border: 'border-slate-700',
            text: 'text-slate-300',
            bg: 'bg-slate-800/50',
          };

          return (
            <div
              key={agentKey}
              className={`p-4 rounded-xl bg-slate-900/90 border ${color.border} shadow-lg hover:shadow-xl transition-all flex flex-col justify-between`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-xs font-bold font-mono ${color.text} uppercase tracking-wider`}>
                    {agent.agent_name}
                  </span>
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${color.bg} ${color.text}`}>
                    {(agent.accuracy_score * 100).toFixed(0)}% ACC
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed mb-3">{agent.role_description}</p>

                {/* Telemetry Stats */}
                <div className="grid grid-cols-2 gap-2 my-3 p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80 font-mono text-[10px]">
                  <div>
                    <span className="text-slate-500">Tasks:</span>{' '}
                    <span className="text-slate-200 font-bold">{agent.tasks_processed}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">Success:</span>{' '}
                    <span className="text-emerald-400 font-bold">{(agent.success_rate * 100).toFixed(0)}%</span>
                  </div>
                  <div>
                    <span className="text-slate-500">Avg Latency:</span>{' '}
                    <span className="text-slate-200 font-bold">{agent.avg_latency_seconds}s</span>
                  </div>
                  <div>
                    <span className="text-slate-500">Tokens:</span>{' '}
                    <span className="text-indigo-300 font-bold">{agent.token_usage.toLocaleString()}</span>
                  </div>
                </div>

                {/* Key Strengths */}
                <div className="mt-2 space-y-1">
                  <span className="text-[10px] font-mono text-slate-400 font-semibold uppercase block">
                    Key Strengths:
                  </span>
                  {agent.key_strengths.map((str, sIdx) => (
                    <div key={sIdx} className="flex items-start gap-1.5 text-[10px] text-slate-300">
                      <CheckCircle2 className="h-3 w-3 text-emerald-400 shrink-0 mt-0.5" />
                      <span>{str}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Area for improvement */}
              {agent.areas_for_improvement.length > 0 && (
                <div className="mt-3 pt-2.5 border-t border-slate-800/80 text-[10px] text-slate-400">
                  <span className="text-slate-500 font-mono">Tuning Target:</span>{' '}
                  <span className="text-slate-300">{agent.areas_for_improvement[0]}</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
