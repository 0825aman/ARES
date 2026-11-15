'use client';

import { useState } from 'react';
import { Layers, Info, Filter, Cpu, Search, ShieldCheck } from 'lucide-react';
import type { PictographBlock, TokenSummaryResponse } from '@/lib/types/token';

interface TokenPictographMatrixProps {
  data: TokenSummaryResponse;
}

export function TokenPictographMatrix({ data }: TokenPictographMatrixProps) {
  const [selectedAgent, setSelectedAgent] = useState<string>('all');
  const [hoveredBlock, setHoveredBlock] = useState<PictographBlock | null>(null);

  const { blocks, quantum_size, unit_label } = data.pictograph;

  const filteredBlocks = selectedAgent === 'all'
    ? blocks
    : blocks.filter((b) => b.agent === selectedAgent);

  const agentCounts: Record<string, number> = {
    all: blocks.length,
    researcher: blocks.filter((b) => b.agent === 'researcher').length,
    supervisor: blocks.filter((b) => b.agent === 'supervisor').length,
    planner: blocks.filter((b) => b.agent === 'planner').length,
    critic: blocks.filter((b) => b.agent === 'critic').length,
  };

  return (
    <div className="tech-panel rounded-xl border border-slate-800 bg-slate-900/90 p-5 shadow-xl">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/80 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <h3 className="font-mono text-sm font-bold uppercase tracking-wider text-white">
              Interactive Token Pictograph Matrix (Isotype Unit Grid)
            </h3>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Each glyph represents <span className="text-sky-300 font-mono font-semibold">{quantum_size.toLocaleString()} tokens</span> consumed across multi-agent autonomous threads
          </p>
        </div>

        {/* Filter buttons */}
        <div className="flex flex-wrap items-center gap-1.5 font-mono text-[11px]">
          <button
            onClick={() => setSelectedAgent('all')}
            className={`px-2.5 py-1 rounded-md border transition-colors ${
              selectedAgent === 'all'
                ? 'bg-sky-500/20 text-sky-300 border-sky-500/40 font-bold'
                : 'bg-slate-800/70 text-slate-400 border-slate-700/60 hover:text-white'
            }`}
          >
            All Swarm ({agentCounts.all})
          </button>
          <button
            onClick={() => setSelectedAgent('researcher')}
            className={`px-2.5 py-1 rounded-md border transition-colors flex items-center gap-1 ${
              selectedAgent === 'researcher'
                ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 font-bold'
                : 'bg-slate-800/70 text-slate-400 border-slate-700/60 hover:text-white'
            }`}
          >
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
            Researcher ({agentCounts.researcher})
          </button>
          <button
            onClick={() => setSelectedAgent('supervisor')}
            className={`px-2.5 py-1 rounded-md border transition-colors flex items-center gap-1 ${
              selectedAgent === 'supervisor'
                ? 'bg-violet-500/20 text-violet-300 border-violet-500/40 font-bold'
                : 'bg-slate-800/70 text-slate-400 border-slate-700/60 hover:text-white'
            }`}
          >
            <span className="h-1.5 w-1.5 rounded-full bg-violet-400"></span>
            Supervisor ({agentCounts.supervisor})
          </button>
          <button
            onClick={() => setSelectedAgent('planner')}
            className={`px-2.5 py-1 rounded-md border transition-colors flex items-center gap-1 ${
              selectedAgent === 'planner'
                ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40 font-bold'
                : 'bg-slate-800/70 text-slate-400 border-slate-700/60 hover:text-white'
            }`}
          >
            <span className="h-1.5 w-1.5 rounded-full bg-cyan-400"></span>
            Planner ({agentCounts.planner})
          </button>
          <button
            onClick={() => setSelectedAgent('critic')}
            className={`px-2.5 py-1 rounded-md border transition-colors flex items-center gap-1 ${
              selectedAgent === 'critic'
                ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 font-bold'
                : 'bg-slate-800/70 text-slate-400 border-slate-700/60 hover:text-white'
            }`}
          >
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400"></span>
            Critic ({agentCounts.critic})
          </button>
        </div>
      </div>

      {/* Pictograph Quantum Grid */}
      <div className="pt-4">
        <div className="min-h-[140px] rounded-lg bg-slate-950/80 p-4 border border-slate-800/60">
          <div className="flex flex-wrap gap-1.5 sm:gap-2">
            {filteredBlocks.map((block) => {
              const isHovered = hoveredBlock?.id === block.id;

              return (
                <div
                  key={block.id}
                  onMouseEnter={() => setHoveredBlock(block)}
                  onMouseLeave={() => setHoveredBlock(null)}
                  style={{
                    backgroundColor: `${block.color}25`,
                    borderColor: `${block.color}70`,
                  }}
                  className={`group relative h-6 w-6 sm:h-7 sm:w-7 rounded-md border flex items-center justify-center cursor-pointer transition-all duration-200 transform ${
                    isHovered ? 'scale-125 z-20 shadow-lg ring-2 ring-white/60' : 'hover:scale-110 hover:z-10'
                  }`}
                >
                  {/* Subtle inner glyph dot */}
                  <span
                    style={{ backgroundColor: block.color }}
                    className="h-1.5 w-1.5 rounded-full"
                  />
                </div>
              );
            })}
          </div>

          {/* Interactive Inspection Bar */}
          <div className="mt-4 pt-3 border-t border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between text-xs font-mono text-slate-400 gap-2">
            {hoveredBlock ? (
              <div className="flex items-center gap-2">
                <span className="text-white font-bold">Quantum Block #{hoveredBlock.id}</span>
                <span className="text-slate-600">|</span>
                <span style={{ color: hoveredBlock.color }} className="font-semibold">
                  {hoveredBlock.label}
                </span>
                <span className="text-slate-600">|</span>
                <span className="text-slate-200">
                  {hoveredBlock.tokens.toLocaleString()} Tokens ({((hoveredBlock.tokens / data.total_tokens) * 100).toFixed(2)}% of total)
                </span>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-slate-500">
                <Info className="h-3.5 w-3.5" />
                <span>Hover over any token block to inspect individual swarm quantum telemetry</span>
              </div>
            )}

            <div className="flex items-center gap-3">
              <span className="text-slate-400">
                Viewing <strong className="text-white">{filteredBlocks.length}</strong> of{' '}
                <strong className="text-white">{blocks.length}</strong> total blocks
              </span>
              <span className="text-slate-600">•</span>
              <span className="text-sky-400 font-semibold">{unit_label}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
