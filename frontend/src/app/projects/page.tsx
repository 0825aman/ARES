import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Plus } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { ProjectsClient } from '@/components/projects/ProjectsClient';

export default function ProjectsPage() {
  return (
    <div className="flex flex-col h-full overflow-hidden">
      <PageHeader
        title="Research Missions Ledger"
        description="Catalog of autonomous investigations, hypotheses, and knowledge synthesis artifacts"
      >
        <Button
          asChild
          size="sm"
          className="bg-blue-600 hover:bg-blue-500 text-white font-mono text-xs font-bold border border-blue-400/40 shadow-lg shadow-blue-500/20 px-4 py-2"
        >
          <Link href="/projects/new">
            <Plus className="h-4 w-4 mr-1.5" />
            INITIALIZE MISSION
          </Link>
        </Button>
      </PageHeader>

      <div className="page-content">
        <div className="max-w-6xl">
          <ProjectsClient />
        </div>
      </div>
    </div>
  );
}
