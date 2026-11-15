import Link from 'next/link';
import { StatusBadge } from '@/components/projects/StatusBadge';
import { CategoryBadge } from '@/components/projects/CategoryBadge';
import { formatDate } from '@/lib/utils/format';
import type { ProjectBrief } from '@/lib/types/project';
import { ArrowRight, Terminal } from 'lucide-react';

interface RecentProjectsProps {
  projects: ProjectBrief[];
}

export function RecentProjects({ projects }: RecentProjectsProps) {
  return (
    <div className="tech-panel overflow-hidden">
      {/* Top telemetry column bar */}
      <div className="hidden sm:grid grid-cols-12 gap-4 px-5 py-3 bg-slate-950 border-b border-slate-800 font-mono text-xs uppercase tracking-wider text-slate-200 font-bold">
        <div className="col-span-6 flex items-center gap-2">
          <Terminal className="h-3.5 w-3.5 text-blue-400" />
          <span>Mission Topic & Identifier</span>
        </div>
        <div className="col-span-2">Domain</div>
        <div className="col-span-2">Registered</div>
        <div className="col-span-2 text-right">Status</div>
      </div>

      <div className="divide-y divide-slate-800/80">
        {projects.map((project) => {
          const shortId = project.id ? project.id.slice(0, 8) : '00000000';
          return (
            <Link
              key={project.id}
              href={`/projects/${project.id}`}
              className="group flex flex-col sm:grid sm:grid-cols-12 gap-3 sm:gap-4 px-5 py-4 hover:bg-slate-800/50 transition-all duration-150 items-start sm:items-center relative"
            >
              {/* Left hover indicator bar */}
              <div className="absolute left-0 top-0 bottom-0 w-1 bg-blue-500 opacity-0 group-hover:opacity-100 transition-opacity" />

              {/* Title & Short ID */}
              <div className="col-span-6 min-w-0 pr-2">
                <div className="flex items-center gap-2.5">
                  <span className="font-mono text-xs font-semibold text-blue-300 bg-slate-950 border border-slate-700 px-2 py-0.5 rounded">
                    #{shortId}
                  </span>
                  <p className="text-sm font-semibold text-white group-hover:text-blue-300 transition-colors truncate">
                    {project.title}
                  </p>
                </div>
              </div>

              {/* Category */}
              <div className="col-span-2">
                <CategoryBadge category={project.category} />
              </div>

              {/* Date */}
              <div className="col-span-2">
                <span className="font-mono text-xs text-slate-200 font-medium">
                  {formatDate(project.created_at)}
                </span>
              </div>

              {/* Status & Arrow */}
              <div className="col-span-2 flex items-center justify-between sm:justify-end gap-3 w-full sm:w-auto">
                <StatusBadge status={project.status} />
                <ArrowRight className="h-4 w-4 text-slate-400 group-hover:text-blue-400 group-hover:translate-x-1 transition-all shrink-0" />
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
