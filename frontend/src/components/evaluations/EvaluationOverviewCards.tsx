'use client';

import { Award, ShieldCheck, Target, Zap, Clock, DollarSign, Activity } from 'lucide-react';
import type { EvaluationDashboardResponse } from '@/lib/types/evaluation';

interface OverviewCardsProps {
  data: EvaluationDashboardResponse;
}

export function EvaluationOverviewCards({ data }: OverviewCardsProps) {
  const { composite_score, rag_metrics, agentic_metrics, safety_metrics, performance_metrics } = data;

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      {/* 1. Composite Score */}
      <div className="relative overflow-hidden rounded-xl bg-slate-900/90 border border-sky-500/30 p-4 shadow-lg shadow-sky-500/10">
        <div className="absolute top-0 right-0 h-16 w-16 bg-sky-500/10 rounded-full blur-xl -mr-4 -mt-4"></div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-mono font-semibold uppercase text-slate-400">Composite Score</span>
          <Award className="h-4 w-4 text-sky-400" />
        </div>
        <div className="flex items-baseline gap-1">
          <span className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight font-mono">
            {composite_score}
          </span>
          <span className="text-xs text-slate-500 font-mono">/ 100</span>
        </div>
        <div className="mt-2 flex items-center gap-1.5 text-[10px] font-mono text-emerald-400 font-medium">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
          HIGH ACCURACY
        </div>
      </div>

      {/* 2. RAG Grounding */}
      <div className="relative overflow-hidden rounded-xl bg-slate-900/90 border border-emerald-500/30 p-4 shadow-lg shadow-emerald-500/10">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-mono font-semibold uppercase text-slate-400">RAG Groundedness</span>
          <Target className="h-4 w-4 text-emerald-400" />
        </div>
        <div className="flex items-baseline gap-1">
          <span className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight font-mono">
            {(rag_metrics.groundedness * 100).toFixed(1)}
          </span>
          <span className="text-xs text-slate-500 font-mono">%</span>
        </div>
        <div className="mt-2 text-[10px] font-mono text-slate-400 truncate">
          Faithfulness: {(rag_metrics.faithfulness * 100).toFixed(1)}%
        </div>
      </div>

      {/* 3. Agent Autonomy */}
      <div className="relative overflow-hidden rounded-xl bg-slate-900/90 border border-cyan-500/30 p-4 shadow-lg shadow-cyan-500/10">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-mono font-semibold uppercase text-slate-400">Task Completion</span>
          <Zap className="h-4 w-4 text-cyan-400" />
        </div>
        <div className="flex items-baseline gap-1">
          <span className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight font-mono">
            {(agentic_metrics.task_completion_rate * 100).toFixed(1)}
          </span>
          <span className="text-xs text-slate-500 font-mono">%</span>
        </div>
        <div className="mt-2 text-[10px] font-mono text-slate-400 truncate">
          Goal: {(agentic_metrics.goal_achievement * 100).toFixed(0)}% reached
        </div>
      </div>

      {/* 4. Safety & Alignment */}
      <div className="relative overflow-hidden rounded-xl bg-slate-900/90 border border-purple-500/30 p-4 shadow-lg shadow-purple-500/10">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-mono font-semibold uppercase text-slate-400">Safety &amp; Guardrails</span>
          <ShieldCheck className="h-4 w-4 text-purple-400" />
        </div>
        <div className="flex items-baseline gap-1">
          <span className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight font-mono">
            {(safety_metrics.prompt_injection_resistance * 100).toFixed(1)}
          </span>
          <span className="text-xs text-slate-500 font-mono">%</span>
        </div>
        <div className="mt-2 text-[10px] font-mono text-emerald-400 truncate">
          Hallucination: {(safety_metrics.hallucination_rate * 100).toFixed(1)}%
        </div>
      </div>

      {/* 5. Latency */}
      <div className="relative overflow-hidden rounded-xl bg-slate-900/90 border border-amber-500/30 p-4 shadow-lg shadow-amber-500/10">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-mono font-semibold uppercase text-slate-400">Mean Latency</span>
          <Clock className="h-4 w-4 text-amber-400" />
        </div>
        <div className="flex items-baseline gap-1">
          <span className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight font-mono">
            {performance_metrics.response_latency_mean}
          </span>
          <span className="text-xs text-slate-500 font-mono">s</span>
        </div>
        <div className="mt-2 text-[10px] font-mono text-slate-400 truncate">
          TTFT: {performance_metrics.time_to_first_token_seconds}s
        </div>
      </div>

      {/* 6. Cost Efficiency */}
      <div className="relative overflow-hidden rounded-xl bg-slate-900/90 border border-indigo-500/30 p-4 shadow-lg shadow-indigo-500/10">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-mono font-semibold uppercase text-slate-400">Cost per Task</span>
          <DollarSign className="h-4 w-4 text-indigo-400" />
        </div>
        <div className="flex items-baseline gap-0.5">
          <span className="text-xs text-slate-400 font-mono">$</span>
          <span className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight font-mono">
            {performance_metrics.cost_per_successful_task_usd}
          </span>
        </div>
        <div className="mt-2 text-[10px] font-mono text-slate-400 truncate">
          {performance_metrics.tokens_per_second} tok/s speed
        </div>
      </div>
    </div>
  );
}
