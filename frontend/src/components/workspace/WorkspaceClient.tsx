'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Terminal, FileText, HelpCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { ProjectDetails } from './ProjectDetails';
import { ResearchPanel } from './ResearchPanel';
import { WorkspaceHeader } from './WorkspaceHeader';
import { ApiConnectionError } from '@/components/common/ApiConnectionError';
import { getProject } from '@/lib/api/projects';
import { ApiError } from '@/lib/api/client';
import type { Project } from '@/lib/types/project';

interface WorkspaceClientProps {
  projectId: string;
}

export function WorkspaceClient({ projectId }: WorkspaceClientProps) {
  const [project, setProject] = useState<Project | null | 'loading' | 'not_found'>('loading');

  const loadProject = () => {
    setProject('loading');
    getProject(projectId)
      .then(setProject)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 404) {
          setProject('not_found');
        } else {
          setProject(null);
        }
      });
  };

  useEffect(() => {
    loadProject();
  }, [projectId]);

  if (project === 'loading') {
    return (
      <div className="page-content">
        <div className="max-w-6xl space-y-4">
          <Skeleton className="h-10 w-72 bg-slate-900 border border-slate-800 rounded-lg" />
          <Skeleton className="h-32 w-full bg-slate-900 border border-slate-800 rounded-xl" />
          <Skeleton className="h-64 w-full bg-slate-900 border border-slate-800 rounded-xl" />
        </div>
      </div>
    );
  }

  if (project === 'not_found') {
    return (
      <div className="page-content">
        <div className="tech-panel p-8 text-center max-w-md mx-auto">
          <p className="font-mono text-base font-bold text-white mb-2">
            MISSION NOT FOUND
          </p>
          <p className="font-mono text-xs text-slate-300 mb-6 font-medium">
            This research record does not exist or has been deleted.
          </p>
          <Button
            variant="outline"
            size="sm"
            asChild
            className="font-mono text-xs font-bold border-slate-700 bg-slate-900 text-slate-100 hover:bg-slate-800 px-4 py-2"
          >
            <Link href="/projects">
              <ArrowLeft className="h-3.5 w-3.5 mr-1.5" />
              RETURN TO LEDGER
            </Link>
          </Button>
        </div>
      </div>
    );
  }

  if (project === null) {
    return (
      <div className="page-content">
        <ApiConnectionError onRetry={loadProject} />
      </div>
    );
  }

  const shortId = project.id ? project.id.slice(0, 8) : '00000000';

  return (
    <div className="page-content">
      <div className="max-w-6xl space-y-5">
        {/* Navigation Breadcrumb / Top Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-slate-800">
          <div className="space-y-1">
            <div className="flex items-center gap-2 font-mono text-xs text-slate-300 font-medium">
              <Link href="/projects" className="hover:text-blue-400 transition-colors flex items-center gap-1 font-bold">
                <ArrowLeft className="h-3.5 w-3.5" />
                <span>MISSIONS</span>
              </Link>
              <span>/</span>
              <span className="text-blue-300 font-bold">#{shortId}</span>
              <span>/</span>
              <span className="text-slate-300 font-bold">WORKSPACE</span>
            </div>
            <h1 className="font-mono text-xl font-bold text-white tracking-tight">
              {project.title}
            </h1>
          </div>
          <WorkspaceHeader project={project} />
        </div>

        <div className="flex flex-col lg:flex-row gap-6">
          {/* Main content */}
          <div className="flex-1 min-w-0 space-y-5">
            {/* Research Question Card */}
            <Card className="tech-panel border-slate-800 bg-slate-900 shadow-xl">
              <CardHeader className="py-3 px-5 border-b border-slate-800">
                <CardTitle className="font-mono text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <HelpCircle className="h-4 w-4 text-blue-400" />
                  Objective Research Question
                </CardTitle>
              </CardHeader>
              <CardContent className="p-5">
                <p className="font-mono text-sm text-slate-100 leading-relaxed font-medium">
                  {project.research_question}
                </p>
              </CardContent>
            </Card>

            {/* Description Card */}
            {project.description && (
              <Card className="tech-panel border-slate-800 bg-slate-900 shadow-xl">
                <CardHeader className="py-3 px-5 border-b border-slate-800">
                  <CardTitle className="font-mono text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                    <FileText className="h-4 w-4 text-cyan-400" />
                    Context &amp; Constraints
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-5">
                  <p className="text-sm text-slate-200 leading-relaxed font-normal">
                    {project.description}
                  </p>
                </CardContent>
              </Card>
            )}

            {/* Multi-Agent Research Orchestration Panel */}
            <div className="space-y-3 pt-1">
              <div className="flex items-center gap-2 font-mono text-xs font-bold uppercase tracking-wider text-white">
                <Terminal className="h-4 w-4 text-blue-400" />
                <span>Multi-Agent Swarm Orchestration</span>
              </div>
              <ResearchPanel
                projectId={project.id}
                researchQuestion={project.research_question}
              />
            </div>
          </div>

          {/* Sidebar */}
          <div className="w-full lg:w-72 shrink-0">
            <ProjectDetails project={project} />
          </div>
        </div>
      </div>
    </div>
  );
}
