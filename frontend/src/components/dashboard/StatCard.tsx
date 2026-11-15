import { type LucideIcon } from 'lucide-react';

interface StatCardProps {
  label: string;
  value: number | string;
  icon: LucideIcon;
  accent?: string;
  badge?: string;
  subtext?: string;
}

export function StatCard({
  label,
  value,
  icon: Icon,
  accent = 'text-blue-400',
  badge,
  subtext,
}: StatCardProps) {
  return (
    <div className="stat-card relative overflow-hidden group">
      {/* Top subtle glow highlight */}
      <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-blue-500/40 to-transparent group-hover:via-blue-400/80 transition-all duration-500" />
      
      <div className="flex items-center justify-between mb-3">
        <span className="font-mono text-xs font-bold text-slate-200 uppercase tracking-wider">
          {label}
        </span>
        <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-700 bg-slate-950 shadow-inner">
          <Icon className={`h-4 w-4 ${accent}`} />
        </div>
      </div>

      <div className="flex items-baseline justify-between gap-2">
        <p className="font-mono text-3xl font-extrabold tracking-tight text-white tabular-nums">
          {value}
        </p>
        {badge && (
          <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded border border-emerald-500/40 bg-emerald-500/20 text-emerald-300">
            {badge}
          </span>
        )}
      </div>

      {subtext && (
        <p className="mt-2.5 font-mono text-xs text-slate-300 font-medium truncate">
          {subtext}
        </p>
      )}
    </div>
  );
}
