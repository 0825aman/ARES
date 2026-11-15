import { StatusBadge } from '@/components/projects/StatusBadge';
import { CategoryBadge } from '@/components/projects/CategoryBadge';
import { formatDate } from '@/lib/utils/format';
import type { Project } from '@/lib/types/project';
import { Terminal, Shield, Calendar, Clock } from 'lucide-react';

interface ProjectDetailsProps {
  project: Project;
}

function Row({
  label,
  icon: Icon,
  children,
}: {
  label: string;
  icon?: React.ElementType;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-1.5 font-mono text-xs font-bold text-slate-300 uppercase tracking-wider">
        {Icon && <Icon className="h-3.5 w-3.5 text-blue-400" />}
        <span>{label}</span>
      </div>
      <div>{children}</div>
    </div>
  );
}

export function ProjectDetails({ project }: ProjectDetailsProps) {
  return (
    <div className="tech-panel p-5 sticky top-6 space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <h2 className="font-mono text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
          <Terminal className="h-4 w-4 text-blue-400" />
          Mission Ledger
        </h2>
        <span className="telemetry-chip font-mono text-[10px] font-bold">ISOLATED</span>
      </div>

      <Row label="Execution State" icon={Shield}>
        <StatusBadge status={project.status} />
      </Row>

      {project.category && (
        <Row label="Investigation Domain">
          <CategoryBadge category={project.category} />
        </Row>
      )}

      <Row label="Registered Date" icon={Calendar}>
        <p className="font-mono text-xs text-slate-100 font-semibold">{formatDate(project.created_at)}</p>
      </Row>

      <Row label="Last Activity" icon={Clock}>
        <p className="font-mono text-xs text-slate-100 font-semibold">{formatDate(project.updated_at)}</p>
      </Row>

      <div className="border-t border-slate-800 pt-3">
        <Row label="System UUID">
          <code className="text-[11px] font-mono text-blue-300 bg-slate-950 px-2 py-1 rounded border border-slate-800 break-all block font-semibold">
            {project.id}
          </code>
        </Row>
      </div>
    </div>
  );
}
