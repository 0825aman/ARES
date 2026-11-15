'use client';

import { Gauge, Cpu, CheckCircle2, ShieldCheck, Zap } from 'lucide-react';
import type { ModelTokenUsage } from '@/lib/types/token';

interface TokenEfficiencyGaugeProps {
  efficiencyScore: number;
  models: ModelTokenUsage[];
  totalTokens: number;
}

export function TokenEfficiencyGauge({ efficiencyScore, models, totalTokens }: TokenEfficiencyGaugeProps) {
  // Speedometer geometry (180 degree semi-circle)
  const size = 180;
  const strokeWidth = 18;
  const radius = (size - strokeWidth) / 2;
  const arcLength = Math.PI * radius;
  const fillOffset = arcLength * (1 - efficiencyScore / 100);

  // Daily quota utilization (1,000,000 token reference limit)
  const quotaLimit = 1000000;
  const quotaPct = Math.min(Math.round((totalTokens / quotaLimit) * 100), 100);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Efficiency Gauge Card */}
      <div className="tech-panel rounded-xl border border-slate-800 bg-slate-900/90 p-5 shadow-xl flex flex-col justify-between">
        <div className="border-b border-slate-800/80 pb-3 mb-3">
          <div className="flex items-center gap-2">
            <Gauge className="h-4 w-4 text-emerald-400" />
            <h3 className="font-mono text-sm font-bold uppercase tracking-wider text-white">
              Cognitive Grounding Efficiency
            </h3>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Ratio of tokens contributing to verified citations versus search noise
          </p>
        </div>

        <div className="flex flex-col items-center justify-center my-2 relative">
          <svg width={size} height={size / 2 + 20} viewBox={`0 0 ${size} ${size / 2 + 20}`}>
            {/* Background semi-circle */}
            <path
              d={`M ${strokeWidth / 2} ${size / 2} A ${radius} ${radius} 0 0 1 ${size - strokeWidth / 2} ${size / 2}`}
              fill="transparent"
              stroke="#1e293b"
              strokeWidth={strokeWidth}
              strokeLinecap="round"
            />
            {/* Value semi-circle */}
            <path
              d={`M ${strokeWidth / 2} ${size / 2} A ${radius} ${radius} 0 0 1 ${size - strokeWidth / 2} ${size / 2}`}
              fill="transparent"
              stroke="#10b981"
              strokeWidth={strokeWidth}
              strokeDasharray={arcLength}
              strokeDashoffset={fillOffset}
              strokeLinecap="round"
              className="transition-all duration-1000"
            />
          </svg>

          <div className="text-center mt-[-10px]">
            <span className="font-mono text-3xl font-extrabold text-white">
              {efficiencyScore}%
            </span>
            <p className="text-[11px] font-mono text-emerald-400 font-semibold mt-0.5">
              OPTIMAL GROUNDING
            </p>
          </div>
        </div>

        <div className="pt-3 border-t border-slate-800/60 flex items-center justify-between text-xs font-mono text-slate-400">
          <span>Target Benchmark: &gt;85%</span>
          <span className="text-emerald-400 font-semibold flex items-center gap-1">
            <CheckCircle2 className="h-3.5 w-3.5" /> Verified
          </span>
        </div>
      </div>

      {/* Model Failover Mesh Breakdown */}
      <div className="tech-panel rounded-xl border border-slate-800 bg-slate-900/90 p-5 shadow-xl flex flex-col justify-between">
        <div className="border-b border-slate-800/80 pb-3 mb-3">
          <div className="flex items-center gap-2">
            <Cpu className="h-4 w-4 text-sky-400" />
            <h3 className="font-mono text-sm font-bold uppercase tracking-wider text-white">
              Model Mesh Token Distribution
            </h3>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Failover routing split across multi-tier LLM providers
          </p>
        </div>

        <div className="space-y-3 my-2">
          {models.map((m) => (
            <div key={m.model} className="space-y-1">
              <div className="flex items-center justify-between text-xs font-mono">
                <div className="flex items-center gap-2">
                  <span style={{ backgroundColor: m.color }} className="h-2 w-2 rounded-full" />
                  <span className="font-bold text-white">{m.model}</span>
                  <span className="text-[10px] text-slate-400">({m.tier})</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-slate-300">{(m.tokens / 1000).toFixed(0)}K</span>
                  <span style={{ color: m.color }} className="font-bold">{m.percentage}%</span>
                </div>
              </div>
              <div className="h-2 w-full rounded-full bg-slate-950 overflow-hidden border border-slate-800">
                <div
                  style={{ width: `${m.percentage}%`, backgroundColor: m.color }}
                  className="h-full rounded-full"
                />
              </div>
            </div>
          ))}
        </div>

        <div className="pt-3 border-t border-slate-800/60 flex items-center justify-between text-xs font-mono text-slate-400">
          <span>Tier 1 Primary: Google Gemini</span>
          <span className="text-sky-400 font-semibold">Zero-Downtime Mesh</span>
        </div>
      </div>
    </div>
  );
}
