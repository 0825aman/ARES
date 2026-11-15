'use client';

import { useState } from 'react';
import { TrendingUp, Calendar, Zap } from 'lucide-react';
import type { TimelinePoint } from '@/lib/types/token';

interface TokenBurnTimelineChartProps {
  timeline: TimelinePoint[];
}

export function TokenBurnTimelineChart({ timeline }: TokenBurnTimelineChartProps) {
  const [mode, setMode] = useState<'cumulative' | 'daily'>('cumulative');
  const [hoveredPoint, setHoveredPoint] = useState<TimelinePoint | null>(null);

  if (!timeline || timeline.length === 0) {
    return (
      <div className="tech-panel rounded-xl border border-slate-800 bg-slate-900/90 p-5 text-center text-slate-500 font-mono text-xs">
        No historical token timeline points recorded yet.
      </div>
    );
  }

  // Calculate scales for SVG rendering
  const width = 800;
  const height = 240;
  const padding = { top: 20, right: 30, bottom: 35, left: 60 };

  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;

  const values = timeline.map((d) => (mode === 'cumulative' ? d.cumulative : d.tokens));
  const maxValue = Math.max(...values, 1000);

  const getX = (index: number) => {
    if (timeline.length === 1) return padding.left + innerWidth / 2;
    return padding.left + (index / (timeline.length - 1)) * innerWidth;
  };

  const getY = (val: number) => {
    return padding.top + innerHeight - (val / maxValue) * innerHeight;
  };

  // Generate SVG path for line and area
  const points = timeline.map((d, i) => {
    const val = mode === 'cumulative' ? d.cumulative : d.tokens;
    return { x: getX(i), y: getY(val), data: d };
  });

  const pathD = points.reduce((acc, curr, idx) => {
    return idx === 0 ? `M ${curr.x} ${curr.y}` : `${acc} L ${curr.x} ${curr.y}`;
  }, '');

  const areaD = points.length > 0
    ? `${pathD} L ${points[points.length - 1].x} ${padding.top + innerHeight} L ${points[0].x} ${padding.top + innerHeight} Z`
    : '';

  // Generate Y-axis grid ticks (4 ticks)
  const yTicks = [0, 0.33, 0.66, 1].map((pct) => Math.round(maxValue * pct));

  return (
    <div className="tech-panel rounded-xl border border-slate-800 bg-slate-900/90 p-5 shadow-xl">
      {/* Header & Mode Switcher */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/80 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-sky-400" />
            <h3 className="font-mono text-sm font-bold uppercase tracking-wider text-white">
              Token Burn Dynamics &amp; Timeline Velocity
            </h3>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Historical consumption curve tracking multi-agent research runs over time
          </p>
        </div>

        <div className="flex items-center gap-1.5 rounded-lg bg-slate-950 p-1 border border-slate-800 text-xs font-mono">
          <button
            onClick={() => setMode('cumulative')}
            className={`px-3 py-1 rounded-md transition-colors ${
              mode === 'cumulative'
                ? 'bg-sky-500/20 text-sky-300 font-bold border border-sky-500/30'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Cumulative Burn
          </button>
          <button
            onClick={() => setMode('daily')}
            className={`px-3 py-1 rounded-md transition-colors ${
              mode === 'daily'
                ? 'bg-sky-500/20 text-sky-300 font-bold border border-sky-500/30'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Daily Velocity
          </button>
        </div>
      </div>

      {/* SVG Chart Area */}
      <div className="pt-4 relative">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto overflow-visible select-none"
        >
          <defs>
            <linearGradient id="tokenBurnGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.4" />
              <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.0" />
            </linearGradient>
            <linearGradient id="tokenLineGradient" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#06b6d4" />
              <stop offset="50%" stopColor="#38bdf8" />
              <stop offset="100%" stopColor="#818cf8" />
            </linearGradient>
          </defs>

          {/* Horizontal Gridlines & Y-labels */}
          {yTicks.map((val, idx) => {
            const y = getY(val);
            return (
              <g key={idx}>
                <line
                  x1={padding.left}
                  y1={y}
                  x2={width - padding.right}
                  y2={y}
                  stroke="#334155"
                  strokeDasharray="4 4"
                  strokeOpacity="0.6"
                />
                <text
                  x={padding.left - 10}
                  y={y + 3}
                  textAnchor="end"
                  className="text-[10px] fill-slate-500 font-mono"
                >
                  {val >= 1000 ? `${(val / 1000).toFixed(0)}K` : val}
                </text>
              </g>
            );
          })}

          {/* Area Fill */}
          <path d={areaD} fill="url(#tokenBurnGradient)" />

          {/* Curve Line */}
          <path
            d={pathD}
            fill="none"
            stroke="url(#tokenLineGradient)"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Data Points */}
          {points.map((pt, idx) => {
            const isHovered = hoveredPoint?.date === pt.data.date;
            return (
              <g
                key={idx}
                className="cursor-pointer"
                onMouseEnter={() => setHoveredPoint(pt.data)}
                onMouseLeave={() => setHoveredPoint(null)}
              >
                <circle
                  cx={pt.x}
                  cy={pt.y}
                  r={isHovered ? 6 : 4}
                  className="fill-slate-900 stroke-sky-400 transition-all duration-150"
                  strokeWidth={isHovered ? 3 : 2}
                />
                {/* X-axis date label */}
                <text
                  x={pt.x}
                  y={height - 10}
                  textAnchor="middle"
                  className={`text-[10px] font-mono transition-colors ${
                    isHovered ? 'fill-sky-300 font-bold' : 'fill-slate-400'
                  }`}
                >
                  {pt.data.date.slice(5)}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Floating Tooltip readout */}
        {hoveredPoint && (
          <div className="mt-3 p-3 rounded-lg bg-slate-950 border border-sky-500/40 shadow-xl flex items-center justify-between text-xs font-mono">
            <div className="flex items-center gap-2">
              <Calendar className="h-4 w-4 text-sky-400" />
              <span className="text-white font-bold">{hoveredPoint.date}</span>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-slate-400">
                Missions: <strong className="text-white">{hoveredPoint.runs}</strong>
              </span>
              <span className="text-slate-400">
                LLM Calls: <strong className="text-blue-300">{hoveredPoint.calls}</strong>
              </span>
              <span className="text-slate-400">
                Tokens: <strong className="text-emerald-400">{(hoveredPoint.tokens).toLocaleString()}</strong>
              </span>
              <span className="text-slate-400">
                Cumulative: <strong className="text-sky-300">{(hoveredPoint.cumulative).toLocaleString()}</strong>
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
