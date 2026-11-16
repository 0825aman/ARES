import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Plus } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { WelcomeBanner } from '@/components/dashboard/WelcomeBanner';
import { DashboardClient } from '@/components/dashboard/DashboardClient';

export default function DashboardPage() {
  return (
    <div className="flex flex-col h-full overflow-hidden">
      <PageHeader
        title="Mission Control Dashboard"
        description="Autonomous multi-agent research telemetry & pipeline orchestration"
      >
        <div className="flex items-center gap-2.5">
          {/* ARES Brand Badge in Title Bar */}
          <Link
            href="/"
            title="Go to Mission Control Dashboard"
            className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-md border border-slate-700 bg-slate-900/90 text-xs font-mono shadow-sm hover:border-blue-500/50 hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <div className="h-6 w-6 rounded overflow-hidden bg-slate-900 border border-blue-500/40 p-0.5 shrink-0 shadow-xs flex items-center justify-center">
              <img
                src="/ares-logo.png"
                alt="ARES Logo"
                className="h-full w-full object-contain"
              />
            </div>
            <span className="text-[11px] text-sky-300 font-bold tracking-wider font-mono">ARES OS</span>
            <span className="text-[9px] px-1 py-0.2 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold">
              ONLINE
            </span>
          </Link>

          <Button
            asChild
            size="sm"
            className="bg-blue-600 hover:bg-blue-500 text-white font-mono text-xs border border-blue-400/30 shadow-lg shadow-blue-500/20"
          >
            <Link href="/projects/new">
              <Plus className="h-3.5 w-3.5 mr-1.5" />
              INITIALIZE MISSION
            </Link>
          </Button>
        </div>
      </PageHeader>

      <div className="page-content">
        <div className="max-w-6xl space-y-6">
          <WelcomeBanner />
          <DashboardClient />
        </div>
      </div>
    </div>
  );
}
