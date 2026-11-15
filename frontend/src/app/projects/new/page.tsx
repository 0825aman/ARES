import Link from 'next/link';
import { ArrowLeft, Terminal } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { PageHeader } from '@/components/layout/PageHeader';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ProjectForm } from '@/components/projects/ProjectForm';

export default function NewProjectPage() {
  return (
    <div className="flex flex-col h-full overflow-hidden">
      <PageHeader
        title="Initialize Research Mission"
        description="Configure target hypothesis and investigation directives for the autonomous swarm"
      >
        <Button
          variant="outline"
          size="sm"
          asChild
          className="font-mono text-xs border-slate-800 bg-slate-900/80 text-slate-300 hover:bg-slate-800"
        >
          <Link href="/projects">
            <ArrowLeft className="h-3.5 w-3.5 mr-1.5" />
            RETURN TO LEDGER
          </Link>
        </Button>
      </PageHeader>

      <div className="page-content">
        <div className="max-w-2xl">
          <Card className="tech-panel border-slate-800 bg-slate-900/90 shadow-2xl relative overflow-hidden">
            {/* Top subtle glow line */}
            <div className="absolute top-0 left-0 right-0 h-[1.5px] bg-gradient-to-r from-transparent via-blue-500/50 to-transparent" />

            <CardHeader className="pb-4 border-b border-slate-800/80">
              <CardTitle className="font-mono text-sm font-bold text-slate-100 flex items-center gap-2">
                <Terminal className="h-4 w-4 text-blue-400" />
                MISSION PARAMETERS & DIRECTIVES
              </CardTitle>
              <CardDescription className="font-mono text-xs text-slate-400">
                Define the primary research question. The Planner agent will decompose this into an executable task DAG.
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-5">
              <ProjectForm />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
