'use client';

import { Clock, DollarSign, Gauge, Activity, Server, Zap, AlertCircle } from 'lucide-react';
import type { PerformanceMetrics } from '@/lib/types/evaluation';

interface PerformanceCostSectionProps {
  metrics: PerformanceMetrics;
}

export function PerformanceCostSection({ metrics }: PerformanceCostSectionProps) {
  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-base font-bold text-white flex items-center gap-2">
          <Clock className="h-5 w-5 text-amber-400" />
          5. Performance &amp; Cost Metrics (Latency, Throughput &amp; Expenditure)
        </h3>
        <p className="text-xs text-slate-400">
          Measures generation latency percentiles, stream responsiveness (TTFT), token velocity, and financial cost per task
        </p>
      </div>

      {/* Latency Percentiles Card */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Gauge className="h-4 w-4 text-amber-400" />
              <h4 className="text-sm font-bold text-white font-mono">Response Latency Distribution</h4>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
              P50 / P95 / P99
            </span>
          </div>
          <div className="grid grid-cols-4 gap-2 text-center pt-2">
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400">Mean</span>
              <div className="text-xl font-bold font-mono text-white mt-1">
                {metrics.response_latency_mean}s
              </div>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400">Median (p50)</span>
              <div className="text-xl font-bold font-mono text-emerald-400 mt-1">
                {metrics.response_latency_p50}s
              </div>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400">p95</span>
              <div className="text-xl font-bold font-mono text-amber-400 mt-1">
                {metrics.response_latency_p95}s
              </div>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400">p99 Tail</span>
              <div className="text-xl font-bold font-mono text-rose-400 mt-1">
                {metrics.response_latency_p99}s
              </div>
            </div>
          </div>
          <p className="text-[11px] text-slate-500 mt-3 font-mono">
            Time to First Token (TTFT):{' '}
            <span className="text-slate-300 font-bold">{metrics.time_to_first_token_seconds}s</span> | Generation Speed:{' '}
            <span className="text-slate-300 font-bold">{metrics.tokens_per_second} tokens/sec</span>
          </p>
        </div>

        {/* Cost & Resource Breakdown Card */}
        <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <DollarSign className="h-4 w-4 text-indigo-400" />
              <h4 className="text-sm font-bold text-white font-mono">Token Volume &amp; Cost Efficiency</h4>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              BUDGET ALIGNED
            </span>
          </div>
          <div className="grid grid-cols-2 gap-3 pt-1">
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400">Input / Prompt Tokens</span>
              <div className="text-xl font-bold font-mono text-indigo-300 mt-1">
                {metrics.input_tokens_total.toLocaleString()}
              </div>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400">Output / Completion Tokens</span>
              <div className="text-xl font-bold font-mono text-indigo-300 mt-1">
                {metrics.output_tokens_total.toLocaleString()}
              </div>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400">Cost per Request</span>
              <div className="text-xl font-bold font-mono text-emerald-400 mt-1">
                ${metrics.cost_per_request_usd}
              </div>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
              <span className="text-[10px] font-mono text-slate-400">Cost per Successful Task</span>
              <div className="text-xl font-bold font-mono text-emerald-400 mt-1">
                ${metrics.cost_per_successful_task_usd}
              </div>
            </div>
          </div>
          <p className="text-[11px] text-slate-500 mt-3 font-mono">
            Throughput: <span className="text-slate-300 font-bold">{metrics.throughput_requests_per_minute} req/min</span> |
            Error Rate: <span className="text-emerald-400 font-bold">{(metrics.error_rate * 100).toFixed(1)}%</span>
          </p>
        </div>
      </div>
    </div>
  );
}
