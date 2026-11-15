'use client';

import { Zap, Cpu, DollarSign, BookOpen, Clock, FileText, CheckCircle2, TrendingUp } from 'lucide-react';
import type { TokenSummaryResponse } from '@/lib/types/token';

interface TokenOverviewCardsProps {
  data: TokenSummaryResponse;
}

export function TokenOverviewCards({ data }: TokenOverviewCardsProps) {
  const formattedTotal = (data.total_tokens / 1000).toFixed(0);
  const formattedPrompt = (data.prompt_tokens / 1000).toFixed(0);
  const formattedComp = (data.completion_tokens / 1000).toFixed(0);

  return (
    <div className="space-y-4">
      {/* Primary KPI Row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Total Tokens Burned */}
        <div className="tech-panel relative overflow-hidden rounded-xl border border-sky-500/30 bg-slate-900/90 p-5 shadow-lg shadow-sky-950/40">
          <div className="absolute top-0 right-0 h-24 w-24 translate-x-6 -translate-y-6 rounded-full bg-sky-500/10 blur-xl"></div>
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs font-semibold uppercase tracking-wider text-slate-400">
              Total Tokens Used
            </span>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-500/20 text-sky-400 border border-sky-500/30">
              <Zap className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="font-mono text-3xl font-extrabold tracking-tight text-white">
              {data.total_tokens.toLocaleString()}
            </span>
            <span className="font-mono text-xs font-bold text-sky-400">
              ({formattedTotal}K)
            </span>
          </div>
          <div className="mt-2 flex items-center justify-between text-[11px] font-mono text-slate-400">
            <span>Cumulative since launch</span>
            <span className="flex items-center gap-1 text-emerald-400 font-bold">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              ACTIVE
            </span>
          </div>
        </div>

        {/* LLM Invocations */}
        <div className="tech-panel relative overflow-hidden rounded-xl border border-slate-800 bg-slate-900/90 p-5 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs font-semibold uppercase tracking-wider text-slate-400">
              LLM Invocations
            </span>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500/20 text-blue-400 border border-blue-500/30">
              <Cpu className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="font-mono text-3xl font-extrabold tracking-tight text-white">
              {data.total_llm_calls.toLocaleString()}
            </span>
            <span className="font-mono text-xs text-slate-400">calls</span>
          </div>
          <div className="mt-2 flex items-center justify-between text-[11px] font-mono text-slate-400">
            <span>Across {data.total_runs} missions</span>
            <span className="text-slate-300 font-medium">~{data.avg_tokens_per_run.toLocaleString()} tok/run</span>
          </div>
        </div>

        {/* Cloud Compute Cost & Savings */}
        <div className="tech-panel relative overflow-hidden rounded-xl border border-slate-800 bg-slate-900/90 p-5 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs font-semibold uppercase tracking-wider text-slate-400">
              Est. Compute Value
            </span>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
              <DollarSign className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="font-mono text-3xl font-extrabold tracking-tight text-white">
              ${data.estimated_cost_usd.toFixed(3)}
            </span>
            <span className="font-mono text-xs text-slate-400">USD</span>
          </div>
          <div className="mt-2 flex items-center justify-between text-[11px] font-mono">
            <span className="text-slate-400">vs Commercial API:</span>
            <span className="text-emerald-400 font-semibold">+${data.equivalents.savings_usd} Saved</span>
          </div>
        </div>

        {/* Token Efficiency Rating */}
        <div className="tech-panel relative overflow-hidden rounded-xl border border-slate-800 bg-slate-900/90 p-5 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs font-semibold uppercase tracking-wider text-slate-400">
              Grounded Token Ratio
            </span>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-500/20 text-violet-400 border border-violet-500/30">
              <CheckCircle2 className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="font-mono text-3xl font-extrabold tracking-tight text-emerald-400">
              {data.efficiency_score}%
            </span>
            <span className="font-mono text-xs text-slate-400">optimal</span>
          </div>
          <div className="mt-2 flex items-center justify-between text-[11px] font-mono text-slate-400">
            <span>Signal-to-noise index</span>
            <span className="text-sky-400 font-semibold">Tier-1 Grounding</span>
          </div>
        </div>
      </div>

      {/* Prompt vs Completion Context Capacitor */}
      <div className="tech-panel rounded-xl border border-slate-800 bg-slate-900/90 p-5 shadow-lg">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
          <div>
            <h3 className="font-mono text-xs font-bold uppercase tracking-wider text-white flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-cyan-400"></span>
              Prompt (Input) vs Completion (Output) Token Allocation
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Breakdown of tokens spent on ingested context (webpages, citations, prompt engineering) versus generated synthesis
            </p>
          </div>
          <div className="flex items-center gap-4 text-xs font-mono">
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-sm bg-cyan-500"></span>
              <span className="text-slate-300">Prompt: <strong className="text-white">{data.prompt_ratio}%</strong> ({formattedPrompt}K)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-sm bg-amber-500"></span>
              <span className="text-slate-300">Completion: <strong className="text-white">{data.completion_ratio}%</strong> ({formattedComp}K)</span>
            </div>
          </div>
        </div>

        {/* Visual Dual Progress Bar */}
        <div className="h-4 w-full rounded-full bg-slate-950 p-0.5 border border-slate-800 flex overflow-hidden">
          <div
            style={{ width: `${data.prompt_ratio}%` }}
            className="h-full rounded-l-full bg-gradient-to-r from-cyan-600 via-sky-500 to-blue-500 transition-all duration-700"
            title={`Prompt Tokens: ${data.prompt_tokens.toLocaleString()} (${data.prompt_ratio}%)`}
          />
          <div
            style={{ width: `${data.completion_ratio}%` }}
            className="h-full rounded-r-full bg-gradient-to-r from-amber-500 to-orange-500 transition-all duration-700"
            title={`Completion Tokens: ${data.completion_tokens.toLocaleString()} (${data.completion_ratio}%)`}
          />
        </div>
      </div>

      {/* Real-World Research Equivalents Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="flex items-center gap-3.5 p-3.5 rounded-lg bg-slate-900/60 border border-slate-800">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <FileText className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-baseline gap-1.5">
              <span className="font-mono text-xl font-bold text-white">
                {data.equivalents.pages_read.toLocaleString()}
              </span>
              <span className="text-[11px] font-mono text-slate-400">Pages</span>
            </div>
            <p className="text-[11px] text-slate-400">Equivalent dense research literature read</p>
          </div>
        </div>

        <div className="flex items-center gap-3.5 p-3.5 rounded-lg bg-slate-900/60 border border-slate-800">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <BookOpen className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-baseline gap-1.5">
              <span className="font-mono text-xl font-bold text-white">
                {data.equivalents.books_synthesized}
              </span>
              <span className="text-[11px] font-mono text-slate-400">Books</span>
            </div>
            <p className="text-[11px] text-slate-400">Equivalent volumes of knowledge synthesized</p>
          </div>
        </div>

        <div className="flex items-center gap-3.5 p-3.5 rounded-lg bg-slate-900/60 border border-slate-800">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-violet-500/10 text-violet-400 border border-violet-500/20">
            <Clock className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-baseline gap-1.5">
              <span className="font-mono text-xl font-bold text-white">
                {data.equivalents.reading_hours_saved}
              </span>
              <span className="text-[11px] font-mono text-slate-400">Hours</span>
            </div>
            <p className="text-[11px] text-slate-400">Manual research &amp; reading time saved</p>
          </div>
        </div>
      </div>
    </div>
  );
}
