import Link from 'next/link';
import { notFound } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { PageHeader } from '@/components/layout/PageHeader';
import { ResearchReportView } from '@/components/workspace/ResearchReportView';
import { getReport } from '@/lib/api/runs';
import { ApiError } from '@/lib/api/client';

export const dynamic = 'force-dynamic';

interface RunReportPageProps {
  params: { id: string; runId: string };
}

export default async function RunReportPage({ params }: RunReportPageProps) {
  let report;
  try {
    report = await getReport(params.id, params.runId);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      notFound();
    }
    return (
      <div className="flex flex-col h-full overflow-hidden">
        <PageHeader title="Research Report">
          <Button variant="outline" size="sm" asChild>
            <Link href={`/projects/${params.id}`}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Project
            </Link>
          </Button>
        </PageHeader>
        <div className="page-content">
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            Cannot reach the backend. Make sure the API server is running.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <PageHeader title="Research Report" description={report.research_question}>
        <Button variant="outline" size="sm" asChild>
          <Link href={`/projects/${params.id}`}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Project
          </Link>
        </Button>
      </PageHeader>
      <div className="page-content">
        <div className="max-w-4xl">
          <ResearchReportView report={report} />
        </div>
      </div>
    </div>
  );
}
