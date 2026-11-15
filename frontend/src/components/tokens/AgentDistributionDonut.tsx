'use client';

import { useState } from 'react';
import { Search, Layers, Cpu, ShieldCheck, PieChart } from 'lucide-react';
import type { AgentTokenUsage } from '@/lib/types/token';

interface AgentDistributionDonutProps {
  agents: AgentTokenUsage[];
  totalTokens: number;
}

export function AgentDistributionDonut({ agents, totalTokens }: AgentDistributionDonutProps) {
  const [hoveredAgent, setHoveredAgent] = useState<AgentTokenUsage | null>(null);

  // SVG Donut geometry
  const size = 220;
  const strokeWidth = 28;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  // Compute stroke-dasharray and stroke-dashoffset for each slice
  let accumulatedPercent = 0;
  const slices = agents.map((agent) => {
    const strokeDasharray = `${(agent.percentage / 100) * circumference} ${circumference}`;
    const strokeDashoffset = -((accumulatedPercent / 100) * circumference);
    accumulatedPercent += agent.percentage;
    return {
      agent,
      strokeDasharray,
      strokeDashoffset,
    };
  });

  const getAgentIcon = (iconName: string) => {
    switch (iconName) {
      case 'Search':
        return <Search className="h-4 w-4" />;
      case 'Layers':
        return <Layers className="h-4 w-4" />;
      case 'Cpu':
        return <Cpu className="h-4 w-4" />;
      case 'ShieldCheck':
        return <ShieldCheck className="h-4 w-4" />;
      default:
        return <Cpu className="h-4 w-4" />;
    }
  };

  return (
    <div className="tech-panel rounded-xl border border-slate-800 bg-slate-900/90 p-5 shadow-xl">
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-4 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <PieChart className="h-4 w-4 text-violet-400" />
            <h3 className="font-mono text-sm font-bold uppercase tracking-wider text-white">
              Swarm Agent Token Allocation
            </h3>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Distribution of compute across autonomous agent specializations
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
        {/* SVG Donut Chart */}
        <div className="md:col-span-5 flex justify-center items-center relative">
          <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="transform -rotate-90">
            {/* Background ring */}
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="transparent"
              stroke="#1e293b"
              strokeWidth={strokeWidth}
            />

            {/* Agent slices */}
            {slices.map(({ agent, strokeDasharray, strokeDashoffset }, idx) => {
              const isHovered = hoveredAgent?.agent === agent.agent;
              return (
                <circle
                  key={idx}
                  cx={size / 2}
                  cy={size / 2}
                  r={radius}
                  fill="transparent"
                  stroke={agent.color}
                  strokeWidth={isHovered ? strokeWidth + 6 : strokeWidth}
                  strokeDasharray={strokeDasharray}
                  strokeDashoffset={strokeDashoffset}
                  className="cursor-pointer transition-all duration-300"
                  onMouseEnter={() => setHoveredAgent(agent)}
                  onMouseLeave={() => setHoveredAgent(null)}
                />
              );
            })}
          </svg>

          {/* Center Text Readout */}
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none text-center">
            {hoveredAgent ? (
              <>
                <span className="text-[11px] font-mono uppercase text-slate-400 tracking-wider">
                  {hoveredAgent.agent}
                </span>
                <span className="text-xl font-bold font-mono text-white">
                  {hoveredAgent.percentage}%
                </span>
                <span className="text-[10px] font-mono text-slate-400">
                  {(hoveredAgent.tokens / 1000).toFixed(0)}K Tokens
                </span>
              </>
            ) : (
              <>
                <span className="text-[10px] font-mono uppercase text-slate-500 tracking-wider">
                  Swarm Total
                </span>
                <span className="text-xl font-bold font-mono text-white">
                  {(totalTokens / 1000).toFixed(0)}K
                </span>
                <span className="text-[10px] font-mono text-emerald-400 font-semibold">
                  4 Active Nodes
                </span>
              </>
            )}
          </div>
        </div>

        {/* Agent Cards Legend */}
        <div className="md:col-span-7 space-y-2.5">
          {agents.map((agent) => {
            const isHovered = hoveredAgent?.agent === agent.agent;
            return (
              <div
                key={agent.agent}
                onMouseEnter={() => setHoveredAgent(agent)}
                onMouseLeave={() => setHoveredAgent(null)}
                className={`p-3 rounded-lg border transition-all duration-200 cursor-pointer ${
                  isHovered
                    ? `${agent.bgColor} ${agent.borderColor} shadow-md ring-1 ring-white/20`
                    : 'bg-slate-950/60 border-slate-800/80 hover:bg-slate-800/40'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span style={{ color: agent.color }}>{getAgentIcon(agent.icon)}</span>
                    <span className="text-xs font-mono font-bold text-white">{agent.label}</span>
                  </div>
                  <div className="flex items-center gap-2 font-mono text-xs">
                    <span className="text-slate-400">{agent.calls} calls</span>
                    <span style={{ color: agent.color }} className="font-bold">
                      {agent.tokens.toLocaleString()} tok ({agent.percentage}%)
                    </span>
                  </div>
                </div>
                <p className="text-[11px] text-slate-400 mt-1 line-clamp-1">{agent.description}</p>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
