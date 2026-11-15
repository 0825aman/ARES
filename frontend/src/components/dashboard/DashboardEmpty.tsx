import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Plus } from 'lucide-react';

export function DashboardEmpty() {
  return (
    <div className="ares-card flex flex-col items-center justify-center py-16 text-center px-6">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100 mb-5">
        <Plus className="h-6 w-6 text-slate-400" />
      </div>
      <h2 className="text-base font-semibold text-slate-900 mb-2">No research projects yet</h2>
      <p className="text-sm text-slate-500 max-w-xs mb-6 leading-relaxed">
        Create your first research project to get started with ARES.
      </p>
      <Button asChild>
        <Link href="/projects/new">
          <Plus className="h-4 w-4 mr-2" />
          Create Research Project
        </Link>
      </Button>
    </div>
  );
}
