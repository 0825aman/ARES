import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { PageHeader } from '@/components/layout/PageHeader';
import { WorkspaceClient } from '@/components/workspace/WorkspaceClient';

interface WorkspacePageProps {
  params: { id: string };
}

export default function WorkspacePage({ params }: WorkspacePageProps) {
  return (
    <div className="flex flex-col h-full overflow-hidden">
      <PageHeader title="Research Workspace">
        <Button variant="outline" size="sm" asChild>
          <Link href="/projects">
            <ArrowLeft className="h-4 w-4 mr-2" />
            All Projects
          </Link>
        </Button>
      </PageHeader>
      <WorkspaceClient projectId={params.id} />
    </div>
  );
}
