'use client';

import { useEffect, useState } from 'react';
import { Zap, RefreshCw, Download, Terminal, AlertTriangle } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { Button } from '@/components/ui/button';
import { getTokenSummary } from '@/lib/api/tokens';
import type { TokenSummaryResponse } from '@/lib/types/token';
import { TokenOverviewCards } from '@/components/tokens/TokenOverviewCards';
import { TokenPictographMatrix } from '@/components/tokens/TokenPictographMatrix';
import { TokenBurnTimelineChart } from '@/components/tokens/TokenBurnTimelineChart';
import { AgentDistributionDonut } from '@/components/tokens/AgentDistributionDonut';
import { TokenEfficiencyGauge } from '@/components/tokens/TokenEfficiencyGauge';
import { MissionTokenLeaderboard } from '@/components/tokens/MissionTokenLeaderboard';

export default function TokenTrackerPage() {
  const [data, setData] = useState<TokenSummaryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState<boolean>(false);

  const fetchData = async () => {
    try {
      setError(null);
      const res = await getTokenSummary();
      setData(res);
    } catch (err: any) {
      setError(err?.message || 'Failed to load token telemetry data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  const handleExportJSON = () => {
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ares_token_telemetry_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <PageHeader
        title="Token Telemetry & Analytics"
        description="Real-time LLM token utilization, multi-agent resource allocation, and cognitive cost analytics"
      >
        <div className="flex items-center gap-2 flex-wrap">
          <div className="hidden sm:flex items-center gap-1.5 font-mono text-xs font-bold text-sky-400 bg-sky-500/10 px-2.5 py-1 rounded-full border border-sky-500/20">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            LIVE TRACKER
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleExportJSON}
            disabled={!data || loading}
            className="border-slate-800 bg-slate-900 hover:bg-slate-800 font-mono text-xs text-slate-300"
          >
            <Download className="mr-1.5 h-3.5 w-3.5" />
            Export Telemetry
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={loading || refreshing}
            className="border-slate-800 bg-slate-900 hover:bg-slate-800 font-mono text-xs text-sky-400"
          >
            <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </PageHeader>

      <div className="page-content">
        <div className="max-w-6xl space-y-6 pb-12">
          {/* Error state */}
          {error && (
            <div className="flex items-center gap-3 p-4 rounded-xl border border-red-500/40 bg-red-950/20 text-red-200 text-xs font-mono">
              <AlertTriangle className="h-4 w-4 shrink-0 text-red-400" />
              <span>{error}. Please ensure the backend daemon is running at http://127.0.0.1:8000.</span>
            </div>
          )}

          {/* Loading Skeleton */}
          {loading && !data && (
            <div className="space-y-4 animate-pulse">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="h-32 rounded-xl bg-slate-900/60 border border-slate-800" />
                ))}
              </div>
              <div className="h-48 rounded-xl bg-slate-900/60 border border-slate-800" />
              <div className="h-72 rounded-xl bg-slate-900/60 border border-slate-800" />
            </div>
          )}

          {/* Main Content */}
          {data && (
            <>
              {/* Top KPI Cards, Context Split, and Research Equivalents */}
              <TokenOverviewCards data={data} />

              {/* Interactive Pictograph Unit Matrix */}
              <TokenPictographMatrix data={data} />

              {/* Timeline Burn Dynamics Area Graph */}
              <TokenBurnTimelineChart timeline={data.timeline} />

              {/* Agent Distribution Donut & Efficiency Gauges */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                <div className="lg:col-span-6">
                  <AgentDistributionDonut agents={data.by_agent} totalTokens={data.total_tokens} />
                </div>
                <div className="lg:col-span-6">
                  <TokenEfficiencyGauge
                    efficiencyScore={data.efficiency_score}
                    models={data.by_model}
                    totalTokens={data.total_tokens}
                  />
                </div>
              </div>

              {/* Mission Token Leaderboard */}
              <MissionTokenLeaderboard runs={data.top_runs} totalTokens={data.total_tokens} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
