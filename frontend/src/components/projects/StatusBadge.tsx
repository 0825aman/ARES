import { Badge } from '@/components/ui/badge';
import type { ProjectStatus } from '@/lib/types/project';
import { cn } from '@/lib/utils/cn';

const STATUS_CONFIG: Record<
  ProjectStatus,
  { label: string; className: string; dotClass: string }
> = {
  not_started: {
    label: 'QUEUED',
    className: 'bg-slate-800/80 text-slate-400 border-slate-700/80',
    dotClass: 'bg-slate-500',
  },
  in_progress: {
    label: 'RUNNING',
    className: 'bg-blue-500/15 text-blue-400 border-blue-500/30 shadow-[0_0_10px_rgba(59,130,246,0.15)]',
    dotClass: 'bg-blue-400 animate-pulse',
  },
  completed: {
    label: 'COMPLETED',
    className: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30 shadow-[0_0_10px_rgba(16,185,129,0.15)]',
    dotClass: 'bg-emerald-400',
  },
  archived: {
    label: 'ARCHIVED',
    className: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
    dotClass: 'bg-amber-400',
  },
};

interface StatusBadgeProps {
  status: ProjectStatus;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? STATUS_CONFIG.not_started;
  return (
    <Badge
      variant="outline"
      className={cn(
        'font-mono text-[10px] font-semibold px-2 py-0.5 inline-flex items-center gap-1.5 uppercase tracking-wider',
        config.className,
        className,
      )}
    >
      <span className={cn('h-1.5 w-1.5 rounded-full', config.dotClass)} />
      {config.label}
    </Badge>
  );
}
