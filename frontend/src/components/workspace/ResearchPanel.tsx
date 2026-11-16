'use client';

import { useCallback, useEffect, useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { ResearchForm } from './ResearchForm';
import { RunStatusCard } from './RunStatusCard';
import { MultiAgentStatusCard } from './MultiAgentStatusCard';
import { ResearchReportView } from './ResearchReportView';
import { RunHistory } from './RunHistory';
import { SourcePanel } from './SourcePanel';
import { EvidenceExplorer } from './EvidenceExplorer';
import { ClaimVerificationPanel } from './ClaimVerificationPanel';
import { CriticReviewPanel } from './CriticReviewPanel';
import { SSEConnectionIndicator } from './SSEConnectionIndicator';
import { ApprovalBanner } from './ApprovalBanner';
import { ApprovalModal } from './ApprovalModal';
import { ExportPanel } from './ExportPanel';
import { LiveBadge } from './LiveBadge';
import { useSSE } from '@/lib/hooks/useSSE';
import {
  getRuns,
  getRun,
  getReport,
  getSources,
  getEvidence,
  getClaims,
  getCriticReview,
  getCitations,
  getPendingApproval,
} from '@/lib/api/runs';
import type {
  ResearchRun,
  ResearchReport,
  Source,
  EvidenceItem,
  Claim,
  CriticReview,
  Citation,
  AgentEvent,
  ApprovalRequest,
} from '@/lib/types/run';

interface ResearchPanelProps {
  projectId: string;
  researchQuestion: string;
}

type PanelState = 'loading' | 'empty' | 'active' | 'completed' | 'failed';

/** Phase 4 data, loaded lazily when their tab is first opened. */
interface Phase4Data {
  sources: Source[] | null;
  evidence: EvidenceItem[] | null;
  claims: Claim[] | null;
  criticReview: CriticReview | null;
  /** null = not loaded yet; undefined = endpoint returned 404 */
  criticReviewMissing?: boolean;
  citations: Citation[] | null;
}

export function ResearchPanel({ projectId, researchQuestion }: ResearchPanelProps) {
  const [state, setState] = useState<PanelState>('loading');
  const [runs, setRuns] = useState<ResearchRun[]>([]);
  const [activeRun, setActiveRun] = useState<ResearchRun | null>(null);
  const [report, setReport] = useState<ResearchReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  // ── SSE-derived live state ─────────────────────────────────────────────────
  const [liveRun, setLiveRun] = useState<ResearchRun | null>(null);
  const [liveEvents, setLiveEvents] = useState<AgentEvent[]>([]);
  const [liveNewSources, setLiveNewSources] = useState<Source[]>([]);
  const [liveNewEvidence, setLiveNewEvidence] = useState<EvidenceItem[]>([]);

  // ── Approval state (M5.5) ──────────────────────────────────────────────────
  const [pendingApproval, setPendingApproval] = useState<ApprovalRequest | null>(null);
  const [approvalModalOpen, setApprovalModalOpen] = useState(false);

  // ── Tab and cross-link state (M5.7) ───────────────────────────────────────
  const [activeTab, setActiveTab] = useState('current');
  const [crossLinkSourceId, setCrossLinkSourceId] = useState<string | null>(null);

  // Phase 4 lazy-loaded data
  const [phase4, setPhase4] = useState<Phase4Data>({
    sources: null,
    evidence: null,
    claims: null,
    criticReview: null,
    citations: null,
  });

  const loadRuns = useCallback(async () => {
    try {
      const data = await getRuns(projectId);
      setRuns(data.items);

      if (data.items.length === 0) {
        setState('empty');
        return;
      }

      const latest = data.items[0];
      setActiveRun(latest);

      if (latest.status === 'pending' || latest.status === 'running' || latest.status === 'awaiting_approval') {
        setState('active');
      } else if (latest.status === 'completed') {
        try {
          const r = await getReport(projectId, latest.id);
          setReport(r);
          setState('completed');
        } catch {
          setState('completed');
        }
      } else {
        setState('failed');
      }
    } catch {
      setError('Cannot reach the backend. Make sure the API server is running.');
      setState('empty');
    }
  }, [projectId]);

  useEffect(() => {
    loadRuns();
  }, [loadRuns]);

  // Reset Phase 4 + approval state when active run changes
  useEffect(() => {
    setPhase4({
      sources: null,
      evidence: null,
      claims: null,
      criticReview: null,
      criticReviewMissing: false,
      citations: null,
    });
    setLiveRun(null);
    setLiveEvents([]);
    setLiveNewSources([]);
    setLiveNewEvidence([]);
    setPendingApproval(null);
    setApprovalModalOpen(false);
    setActiveTab('current');
    setCrossLinkSourceId(null);
  }, [activeRun?.id]);

  // Load pending approval when run enters awaiting_approval state.
  // We deliberately depend on the primitive id/status to avoid re-running on
  // every render — eslint-disable is intentional.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    const runToCheck = liveRun ?? activeRun;
    if (!runToCheck || runToCheck.status !== 'awaiting_approval') return;
    getPendingApproval(projectId, runToCheck.id)
      .then((approval) => setPendingApproval(approval))
      .catch(() => {/* ignore — banner stays hidden */});
  }, [liveRun?.status, activeRun?.status, projectId, activeRun?.id, liveRun?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── SSE hook ───────────────────────────────────────────────────────────────

  // Only connect SSE when run is active
  const isRunActive =
    state === 'active' &&
    activeRun !== null &&
    (activeRun.status === 'pending' ||
      activeRun.status === 'running' ||
      activeRun.status === 'awaiting_approval');

  const { connected: sseConnected } = useSSE(
    isRunActive ? activeRun?.id ?? null : null,
    isRunActive ? projectId : null,
    {
      onRunStatusChanged: (data) => {
        // SSE status_change payload: { run_id, status, current_stage, changed_at }
        const payload = data as { status?: string; current_stage?: string };
        if (activeRun && payload.status) {
          setLiveRun((prev) => {
            const base = prev ?? activeRun;
            return {
              ...base,
              status: (payload.status as ResearchRun['status']) ?? base.status,
              current_stage: payload.current_stage ?? base.current_stage,
            };
          });
        }
      },
      onActivityEvent: (data) => {
        // SSE activity payload: AgentEvent shape
        const event = data as AgentEvent;
        if (event?.id) {
          setLiveEvents((prev) => {
            if (prev.some((e) => e.id === event.id)) return prev;
            return [...prev, event];
          });
        }
      },
      onSourceAdded: (data) => {
        const source = data as Source;
        if (source?.id) {
          setLiveNewSources((prev) => {
            if (prev.some((s) => s.id === source.id)) return prev;
            return [source, ...prev];
          });
        }
      },
      onEvidenceAdded: (data) => {
        const item = data as EvidenceItem;
        if (item?.id) {
          setLiveNewEvidence((prev) => {
            if (prev.some((e) => e.id === item.id)) return prev;
            return [item, ...prev];
          });
        }
      },
      onApprovalRequired: (data) => {
        // approval_required SSE: { run_id, approval_id, checkpoint_name, node_name, context_snapshot }
        const payload = data as {
          approval_id?: string;
          checkpoint_name?: string;
          node_name?: string;
          context_snapshot?: Record<string, unknown>;
          run_id?: string;
        };
        if (payload?.approval_id && activeRun) {
          const now = new Date().toISOString();
          const constructed: ApprovalRequest = {
            id: payload.approval_id,
            run_id: activeRun.id,
            checkpoint_name: payload.checkpoint_name ?? '',
            node_name: payload.node_name ?? '',
            context_snapshot: payload.context_snapshot ?? {},
            status: 'pending',
            decision: null,
            decision_notes: null,
            created_at: now,
            decided_at: null,
            expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
          };
          setPendingApproval(constructed);
        }
      },
      onApprovalResolved: (data) => {
        const payload = data as { decision?: string; run_continuing?: boolean };
        if (!payload?.run_continuing) {
          // Rejected — reload runs to pick up the failed status
          loadRuns();
        }
        setPendingApproval(null);
        setApprovalModalOpen(false);
      },
      onRunCompleted: (data) => {
        const payload = data as { run_id?: string; report_id?: string };
        if (activeRun && payload.run_id === activeRun.id) {
          loadRuns();
        }
      },
      onRunFailed: (data) => {
        const payload = data as { run_id?: string };
        if (activeRun && payload.run_id === activeRun.id) {
          loadRuns();
        }
      },
    },
  );

  // ── Active run polling synchronization (2.5s) ──────────────────────────────
  // Guarantees real-time progress, stage updates, and counts even if SSE drops,
  // connects through a buffered proxy, or misses packet bursts.
  useEffect(() => {
    if (state !== 'active' || !activeRun) return;

    let cancelled = false;
    const pollInterval = setInterval(async () => {
      try {
        const updated = await getRun(projectId, activeRun.id);
        if (cancelled) return;
        setActiveRun((prev) => (prev ? { ...prev, ...updated } : updated));
        setLiveRun((prev) => (prev ? { ...prev, ...updated } : updated));
        if (updated.status === 'completed' || updated.status === 'failed') {
          loadRuns();
        }
      } catch {
        // Ignore transient poll failures
      }
    }, 2500);

    return () => {
      cancelled = true;
      clearInterval(pollInterval);
    };
  }, [state, activeRun?.id, projectId, loadRuns]);

  // ── Lazy loaders ───────────────────────────────────────────────────────────

  async function loadSources() {
    if (!activeRun || phase4.sources !== null) return;
    try {
      const res = await getSources(projectId, activeRun.id);
      setPhase4((p) => ({ ...p, sources: res.items }));
    } catch {
      setPhase4((p) => ({ ...p, sources: [] }));
    }
  }

  async function loadEvidence() {
    if (!activeRun || phase4.evidence !== null) return;
    try {
      const res = await getEvidence(projectId, activeRun.id);
      setPhase4((p) => ({ ...p, evidence: res.items }));
    } catch {
      setPhase4((p) => ({ ...p, evidence: [] }));
    }
  }

  async function loadClaims() {
    if (!activeRun || phase4.claims !== null) return;
    try {
      const res = await getClaims(projectId, activeRun.id);
      setPhase4((p) => ({ ...p, claims: res.items }));
    } catch {
      setPhase4((p) => ({ ...p, claims: [] }));
    }
  }

  async function loadCriticReview() {
    if (!activeRun || phase4.criticReview !== null || phase4.criticReviewMissing) return;
    try {
      const res = await getCriticReview(projectId, activeRun.id);
      setPhase4((p) => ({ ...p, criticReview: res }));
    } catch {
      // 404 = no critic review (sequential run) — mark as missing
      setPhase4((p) => ({ ...p, criticReviewMissing: true }));
    }
  }

  async function loadCitations() {
    if (!activeRun || phase4.citations !== null) return;
    try {
      const res = await getCitations(projectId, activeRun.id);
      setPhase4((p) => ({ ...p, citations: res.citations }));
    } catch {
      setPhase4((p) => ({ ...p, citations: [] }));
    }
  }

  function handleRunStarted(run: ResearchRun) {
    setActiveRun(run);
    setRuns((prev) => [run, ...prev]);
    setState('active');
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  if (state === 'loading') {
    return (
      <div className="space-y-3">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
        {error}
      </div>
    );
  }

  if (state === 'empty') {
    return (
      <ResearchForm
        projectId={projectId}
        defaultQuestion={researchQuestion}
        onRunStarted={handleRunStarted}
      />
    );
  }

  const isCompleted = state === 'completed';
  const isMultiAgent = activeRun?.workflow_mode === 'multi_agent';

  return (
    <>
    <Tabs value={activeTab} onValueChange={setActiveTab}>
      <TabsList className="mb-4 flex-wrap h-auto gap-y-1">
        <TabsTrigger value="current">
          {state === 'active' ? 'In Progress' : 'Latest Run'}
        </TabsTrigger>

        {/* Sources and Evidence — shown for active AND completed runs */}
        {(isCompleted || state === 'active') && activeRun && (
          <>
            <TabsTrigger value="sources" onClick={isCompleted ? loadSources : undefined}>
              Sources
              {state === 'active' && liveNewSources.length > 0 ? (
                <LiveBadge count={liveNewSources.length} active />
              ) : (phase4.sources !== null && phase4.sources.length > 0) ? (
                <Badge variant="secondary" className="ml-1.5 text-xs px-1.5 py-0 h-4">
                  {phase4.sources.length}
                </Badge>
              ) : null}
            </TabsTrigger>

            <TabsTrigger value="evidence" onClick={isCompleted ? loadEvidence : undefined}>
              Evidence
              {state === 'active' && liveNewEvidence.length > 0 ? (
                <LiveBadge count={liveNewEvidence.length} active />
              ) : (phase4.evidence !== null && phase4.evidence.length > 0) ? (
                <Badge variant="secondary" className="ml-1.5 text-xs px-1.5 py-0 h-4">
                  {phase4.evidence.length}
                </Badge>
              ) : null}
            </TabsTrigger>
          </>
        )}

        {/* Claims, Critic Review, Citations — only shown for completed runs */}
        {isCompleted && (
          <>
            <TabsTrigger value="claims" onClick={loadClaims}>
              Claims
              {phase4.claims !== null && phase4.claims.length > 0 && (
                <Badge variant="secondary" className="ml-1.5 text-xs px-1.5 py-0 h-4">
                  {phase4.claims.length}
                </Badge>
              )}
            </TabsTrigger>

            {/* Critic Review tab — only for multi-agent runs */}
            {isMultiAgent && (
              <TabsTrigger value="critic" onClick={loadCriticReview}>
                Critic Review
              </TabsTrigger>
            )}

            <TabsTrigger value="citations" onClick={loadCitations}>
              Citations
              {phase4.citations !== null && phase4.citations.length > 0 && (
                <Badge variant="secondary" className="ml-1.5 text-xs px-1.5 py-0 h-4">
                  {phase4.citations.length}
                </Badge>
              )}
            </TabsTrigger>
          </>
        )}

        <TabsTrigger value="history">History ({runs.length})</TabsTrigger>
        <TabsTrigger value="new">New Run</TabsTrigger>

        {/* SSE indicator — shown only during active run */}
        {state === 'active' && (
          <div className="ml-auto flex items-center px-1">
            <SSEConnectionIndicator connected={sseConnected} />
          </div>
        )}
      </TabsList>

      {/* ── Latest / In-Progress ─────────────────────────────────────────── */}
      <TabsContent value="current" className="mt-0">
        {/* Approval banner — shown when awaiting_approval */}
        {state === 'active' && pendingApproval && activeRun && (
          <ApprovalBanner
            approval={pendingApproval}
            onOpenModal={() => setApprovalModalOpen(true)}
          />
        )}

        {state === 'active' && activeRun && (
          isMultiAgent
            ? (
              <MultiAgentStatusCard
                projectId={projectId}
                initialRun={activeRun}
                liveRun={liveRun}
                liveEvents={liveEvents.length > 0 ? liveEvents : undefined}
                sseConnected={sseConnected}
                onRunCompleted={loadRuns}
              />
            )
            : (
              <RunStatusCard
                projectId={projectId}
                initialRun={activeRun}
                liveRun={liveRun}
                sseConnected={sseConnected}
                onRunCompleted={loadRuns}
              />
            )
        )}
        {state === 'completed' && report && activeRun && (
          <>
            <ResearchReportView
              report={report}
              citations={phase4.citations ?? []}
            />
            <ExportPanel
              projectId={projectId}
              runId={activeRun.id}
              reportId={report.id}
            />
          </>
        )}
        {state === 'completed' && !report && activeRun && (
          <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
            Report not available for this run.
          </div>
        )}
        {state === 'failed' && activeRun && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            <p className="font-medium">Research run failed</p>
            {activeRun.error_message && (
              <p className="mt-1">{activeRun.error_message}</p>
            )}
          </div>
        )}
      </TabsContent>

      {/* ── Sources tab — works for both active and completed runs ─────────── */}
      <TabsContent value="sources" className="mt-0">
        {activeRun && (
          state === 'active'
            ? (
              // Active run: SourcePanel self-fetches and receives live SSE sources
              <SourcePanel
                projectId={projectId}
                runId={activeRun.id}
                liveNewSources={liveNewSources.length > 0 ? liveNewSources : undefined}
                openSourceId={crossLinkSourceId}
                onSourceOpened={() => setCrossLinkSourceId(null)}
              />
            )
            : phase4.sources === null
              ? <Skeleton className="h-32 w-full" />
              : (
                <SourcePanel
                  sources={phase4.sources}
                  projectId={projectId}
                  runId={activeRun.id}
                  openSourceId={crossLinkSourceId}
                  onSourceOpened={() => setCrossLinkSourceId(null)}
                />
              )
        )}
      </TabsContent>

      {/* ── Evidence tab ─────────────────────────────────────────────────── */}
      <TabsContent value="evidence" className="mt-0">
        {activeRun && (
          state === 'active'
            ? (
              // Active run: EvidenceExplorer self-fetches and receives live SSE evidence
              <EvidenceExplorer
                projectId={projectId}
                runId={activeRun.id}
                liveNewEvidence={liveNewEvidence.length > 0 ? liveNewEvidence : undefined}
                onOpenSource={(sourceId) => {
                  setCrossLinkSourceId(sourceId);
                  setActiveTab('sources');
                }}
              />
            )
            : phase4.evidence === null
              ? <Skeleton className="h-32 w-full" />
              : (
                <EvidenceExplorer
                  evidence={phase4.evidence}
                  onOpenSource={(sourceId) => {
                    setCrossLinkSourceId(sourceId);
                    setActiveTab('sources');
                  }}
                />
              )
        )}
      </TabsContent>

      <TabsContent value="claims" className="mt-0">
        {phase4.claims === null
          ? <Skeleton className="h-32 w-full" />
          : <ClaimVerificationPanel claims={phase4.claims} />
        }
      </TabsContent>

      <TabsContent value="critic" className="mt-0">
        {phase4.criticReviewMissing ? (
          <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
            No Critic Review available for this run.
            <p className="text-xs mt-1 text-slate-400">Critic reviews are produced only by multi-agent workflow runs.</p>
          </div>
        ) : phase4.criticReview === null ? (
          <Skeleton className="h-32 w-full" />
        ) : (
          <CriticReviewPanel review={phase4.criticReview} />
        )}
      </TabsContent>

      <TabsContent value="citations" className="mt-0">
        {phase4.citations === null
          ? <Skeleton className="h-32 w-full" />
          : phase4.citations.length === 0
            ? (
              <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
                No citations for this run.
                <p className="text-xs mt-1 text-slate-400">Citations are generated after claim verification and report review.</p>
              </div>
            )
            : (
              <div className="space-y-2">
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <span className="text-xs text-slate-500">
                    {phase4.citations.length} citation{phase4.citations.length !== 1 ? 's' : ''}
                  </span>
                  {phase4.citations.filter((c) => c.is_verified).length > 0 && (
                    <span className="text-xs text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
                      {phase4.citations.filter((c) => c.is_verified).length} verified
                    </span>
                  )}
                </div>
                {phase4.citations.map((citation) => (
                  <div
                    key={citation.id}
                    className="flex gap-3 rounded-md border border-slate-100 bg-white px-4 py-3 text-sm"
                  >
                    <span className="font-mono text-xs text-slate-500 shrink-0 pt-0.5 w-24 truncate">
                      {citation.citation_key}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-slate-700 leading-relaxed">
                        {citation.apa_formatted ?? citation.ieee_formatted ?? 'No formatted citation available.'}
                      </p>
                      {citation.url && (
                        <a
                          href={citation.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-blue-600 hover:underline mt-1 inline-block"
                        >
                          {citation.url}
                        </a>
                      )}
                    </div>
                    {citation.is_verified && (
                      <span className="text-xs text-emerald-600 shrink-0 pt-0.5">✓</span>
                    )}
                  </div>
                ))}
              </div>
            )
        }
      </TabsContent>

      {/* ── History / New Run ─────────────────────────────────────────────── */}
      <TabsContent value="history" className="mt-0">
        <RunHistory projectId={projectId} runs={runs} />
      </TabsContent>

      <TabsContent value="new" className="mt-0">
        <ResearchForm
          projectId={projectId}
          defaultQuestion={researchQuestion}
          onRunStarted={handleRunStarted}
        />
      </TabsContent>
    </Tabs>

    {/* Approval modal — rendered at component root so it overlays all tabs */}
    {activeRun && (
      <ApprovalModal
        open={approvalModalOpen}
        approval={pendingApproval}
        projectId={projectId}
        runId={activeRun.id}
        onClose={() => setApprovalModalOpen(false)}
        onResolved={(decision) => {
          setPendingApproval(null);
          setApprovalModalOpen(false);
          if (decision === 'rejected') {
            loadRuns();
          }
        }}
      />
    )}
    </>
  );
}
