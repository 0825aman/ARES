import Link from 'next/link';
import { StatusBadge } from './StatusBadge';
import { CategoryBadge } from './CategoryBadge';
import { formatDate } from '@/lib/utils/format';
import type { Project } from '@/lib/types/project';
import { ArrowRight } from 'lucide-react';

interface ProjectCardProps {
  project: Project;
}

export function ProjectCard({ project }: ProjectCardProps) {
  const shortId = project.id ? project.id.slice(0, 8) : '00000000';

  return (
    <Link href={`/projects/${project.id}`} className="block group h-full">
      <div className="tech-panel p-5 h-full flex flex-col justify-between relative overflow-hidden transition-all duration-200 group-hover:border-blue-500/60 group-hover:shadow-[0_0_25px_rgba(59,130,246,0.2)]">
        {/* Top hover accent line */}
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-blue-500/0 to-transparent group-hover:via-blue-400/90 transition-all duration-500" />

        <div>
          {/* Top row: status badge and ID */}
          <div className="flex items-center justify-between mb-3.5">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-semibold text-blue-300 bg-slate-950 border border-slate-700 px-2 py-0.5 rounded">
                #{shortId}
              </span>
              <StatusBadge status={project.status} />
            </div>
            {project.category && <CategoryBadge category={project.category} />}
          </div>

          {/* Title */}
          <h3 className="font-mono text-sm font-bold text-white leading-snug line-clamp-2 mb-2 group-hover:text-blue-300 transition-colors">
            {project.title}
          </h3>

          {/* Research question preview */}
          <p className="text-xs text-slate-200 line-clamp-2 leading-relaxed mb-4 font-normal">
            {project.research_question}
          </p>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between mt-auto pt-3 border-t border-slate-800 font-mono text-xs">
          <span className="text-slate-300 font-medium">{formatDate(project.created_at)}</span>
          <div className="flex items-center gap-1.5 text-blue-400 group-hover:translate-x-1 transition-transform font-bold">
            <span>WORKSPACE</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </div>
        </div>
      </div>
    </Link>
  );
}
