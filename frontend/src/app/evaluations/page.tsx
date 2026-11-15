'use client';

import { useEffect, useState } from 'react';
import {
  Activity,
  RefreshCw,
  Play,
  Download,
  AlertTriangle,
  Award,
  CheckCircle2,
  Database,
  Bot,
  ShieldCheck,
  Clock,
  Users,
} from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { Button } from '@/components/ui/button';
import { getEvaluationDashboard, runEvaluationBenchmark } from '@/lib/api/evaluations';
import type { EvaluationDashboardResponse } from '@/lib/types/evaluation';
import { EvaluationOverviewCards } from '@/components/evaluations/EvaluationOverviewCards';
import { AccuracyQualitySection } from '@/components/evaluations/AccuracyQualitySection';
import { RAGEvaluationSection } from '@/components/evaluations/RAGEvaluationSection';
import { AgenticAIMetricsSection } from '@/components/evaluations/AgenticAIMetricsSection';
import { SafetyGuardrailsSection } from '@/components/evaluations/SafetyGuardrailsSection';
import { PerformanceCostSection } from '@/components/evaluations/PerformanceCostSection';
import { MultiAgentSwarmSection } from '@/components/evaluations/MultiAgentSwarmSection';

export default function EvaluationsDashboardPage() {
  const [data, setData] = useState<EvaluationDashboardResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [runningBenchmark, setRunningBenchmark] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<string>('all');
  const [benchmarkNotification, setBenchmarkNotification] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setError(null);
      const res = await getEvaluationDashboard();
      setData(res);
    } catch (err: any) {
      setError(err?.message || 'Failed to load evaluation metrics');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  const handleRunBenchmark = async () => {
    try {
      setRunningBenchmark(true);
      setBenchmarkNotification(null);
      const res = await runEvaluationBenchmark();
      setData(res.results);
      setBenchmarkNotification('Live benchmark suite executed across all 6 dimensions successfully!');
      setTimeout(() => setBenchmarkNotification(null), 5000);
    } catch (err: any) {
      setError(err?.message || 'Failed to run evaluation benchmark suite');
    } finally {
      setRunningBenchmark(false);
    }
  };

  const handleExportJSON = () => {
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ares_llm_evaluation_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const tabs = [
    { id: 'all', label: 'All Dimensions', icon: Activity },
    { id: 'accuracy', label: '1. Accuracy & Quality', icon: CheckCircle2 },
    { id: 'rag', label: '2. RAG Metrics', icon: Database },
    { id: 'agentic', label: '3. Agentic AI', icon: Bot },
    { id: 'safety', label: '4. Safety & Guardrails', icon: ShieldCheck },
    { id: 'performance', label: '5. Performance & Cost', icon: Clock },
    { id: 'multi-agent', label: '6. Multi-Agent Swarm', icon: Users },
  ];

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Page Header */}
      <PageHeader
        title="LLM Agent &amp; Performance Dashboard"
        description="Comprehensive evaluation across accuracy, RAG faithfulness, agent autonomy, safety guardrails, latency, and multi-agent coordination"
      >
        <div className="flex items-center gap-2 flex-wrap">
          <div className="hidden sm:flex items-center gap-1.5 font-mono text-xs font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            EVAL ENGINE v2.0
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={handleRunBenchmark}
            disabled={runningBenchmark}
            className="border-sky-500/40 text-sky-400 hover:bg-sky-500/10 gap-1.5"
          >
            <Play className={`h-3.5 w-3.5 ${runningBenchmark ? 'animate-spin' : ''}`} />
            {runningBenchmark ? 'Evaluating...' : 'Run Benchmark'}
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={refreshing || loading}
            className="border-slate-700 text-slate-300 hover:text-white hover:bg-slate-800 gap-1.5"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handleExportJSON}
            disabled={!data}
            className="border-slate-700 text-slate-300 hover:text-white hover:bg-slate-800 gap-1.5"
          >
            <Download className="h-3.5 w-3.5" />
            Export JSON
          </Button>
        </div>
      </PageHeader>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Benchmark Notification Toast */}
        {benchmarkNotification && (
          <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs font-mono flex items-center gap-2 shadow-lg animate-fadeIn">
            <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
            <span>{benchmarkNotification}</span>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-mono">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={handleRefresh}
              className="text-xs border-rose-500/30 text-rose-300 hover:bg-rose-500/20"
            >
              Retry
            </Button>
          </div>
        )}

        {/* Loading Skeleton */}
        {loading && !data && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="h-28 rounded-xl bg-slate-900/60 border border-slate-800 animate-pulse"></div>
              ))}
            </div>
            <div className="h-96 rounded-xl bg-slate-900/60 border border-slate-800 animate-pulse"></div>
          </div>
        )}

        {/* Dashboard Data */}
        {data && (
          <>
            {/* 1. Overview Summary Cards */}
            <EvaluationOverviewCards data={data} />

            {/* 2. Dimension Filter Tabs */}
            <div className="flex items-center gap-1.5 border-b border-slate-800 pb-2 overflow-x-auto no-scrollbar pt-2">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                const active = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-mono transition-all whitespace-nowrap ${
                      active
                        ? 'bg-sky-500/15 text-sky-400 border border-sky-500/30 font-bold shadow-sm'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                    }`}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>

            {/* Dimension Sections */}
            <div className="space-y-8 pt-2">
              {(activeTab === 'all' || activeTab === 'accuracy') && (
                <section className="p-5 rounded-2xl bg-slate-950/40 border border-slate-800/80 shadow-inner">
                  <AccuracyQualitySection metrics={data.accuracy_and_quality} />
                </section>
              )}

              {(activeTab === 'all' || activeTab === 'rag') && (
                <section className="p-5 rounded-2xl bg-slate-950/40 border border-slate-800/80 shadow-inner">
                  <RAGEvaluationSection metrics={data.rag_metrics} />
                </section>
              )}

              {(activeTab === 'all' || activeTab === 'agentic') && (
                <section className="p-5 rounded-2xl bg-slate-950/40 border border-slate-800/80 shadow-inner">
                  <AgenticAIMetricsSection metrics={data.agentic_metrics} />
                </section>
              )}

              {(activeTab === 'all' || activeTab === 'safety') && (
                <section className="p-5 rounded-2xl bg-slate-950/40 border border-slate-800/80 shadow-inner">
                  <SafetyGuardrailsSection metrics={data.safety_metrics} />
                </section>
              )}

              {(activeTab === 'all' || activeTab === 'performance') && (
                <section className="p-5 rounded-2xl bg-slate-950/40 border border-slate-800/80 shadow-inner">
                  <PerformanceCostSection metrics={data.performance_metrics} />
                </section>
              )}

              {(activeTab === 'all' || activeTab === 'multi-agent') && (
                <section className="p-5 rounded-2xl bg-slate-950/40 border border-slate-800/80 shadow-inner">
                  <MultiAgentSwarmSection metrics={data.multi_agent_system} />
                </section>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
