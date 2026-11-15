'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { ChevronDown, ExternalLink } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { getEvidence } from '@/lib/api/runs';
import { EvidenceDetailDrawer } from './EvidenceDetailDrawer';
import type { EvidenceItem } from '@/lib/types/run';

const PAGE_SIZE = 20;

interface EvidenceExplorerProps {
  /** Static list — used by completed runs (Phase 4 compat). When provided, skips fetch. */
  evidence?: EvidenceItem[];
  /** Used for live/active runs — component self-fetches. */
  projectId?: string;
  runId?: string;
  /** New evidence items pushed from parent SSE state. */
  liveNewEvidence?: EvidenceItem[];
  /** Called to cross-open the SourcePanel drawer for a given source_id */
  onOpenSource?: (sourceId: string) => void;
}

type RelationshipFilter =
  | 'all'
  | 'supports'
  | 'contradicts'
  | 'qualifies'
  | 'contextualizes'
  | 'neutral';

// ── Colour helpers ─────────────────────────────────────────────────────────

function leftBorderClass(rel: string): string {
  switch (rel) {
    case 'supports': return 'border-l-4 border-l-emerald-400';
    case 'contradicts': return 'border-l-4 border-l-red-400';
    case 'qualifies': return 'border-l-4 border-l-amber-400';
    case 'contextualizes': return 'border-l-4 border-l-blue-400';
    default: return 'border-l-4 border-l-slate-200';
  }
}

function relationshipBadgeClass(rel: string): string {
  switch (rel) {
    case 'supports': return 'bg-emerald-100 text-emerald-700';
    case 'contradicts': return 'bg-red-100 text-red-700';
    case 'qualifies': return 'bg-amber-100 text-amber-700';
    case 'contextualizes': return 'bg-blue-100 text-blue-700';
    default: return 'bg-slate-100 text-slate-600';
  }
}

function evidenceTypeBadgeClass(type: string): string {
  switch (type) {
    case 'statistical': return 'bg-violet-100 text-violet-700';
    case 'experimental': return 'bg-blue-100 text-blue-700';
    case 'observational': return 'bg-sky-100 text-sky-700';
    case 'expert_opinion': return 'bg-amber-100 text-amber-700';
    case 'historical': return 'bg-orange-100 text-orange-700';
    case 'official': return 'bg-indigo-100 text-indigo-700';
    default: return 'bg-slate-100 text-slate-600';
  }
}

function formatRelationshipLabel(rel: string): string {
  const map: Record<string, string> = {
    supports: 'Supports',
    contradicts: 'Contradicts',
    qualifies: 'Qualifies',
    contextualizes: 'Contextualizes',
    neutral: 'Neutral',
  };
  return map[rel] ?? rel;
}

// ── EvidenceRow ────────────────────────────────────────────────────────────

interface EvidenceRowProps {
  item: EvidenceItem;
  isNew?: boolean;
  onClick: (item: EvidenceItem) => void;
}

function EvidenceRow({ item, isNew, onClick }: EvidenceRowProps) {
  const excerpt = item.content ? item.content.slice(0, 180) : null;
  const hasMore = item.content && item.content.length > 180;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onClick(item)}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onClick(item); }}
      className={[
        'group rounded-lg border bg-white cursor-pointer transition-all',
        'hover:border-blue-300 hover:bg-blue-50/30',
        'focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-1',
        leftBorderClass(item.evidence_relationship),
        isNew ? 'border-blue-200 bg-blue-50/40' : 'border-slate-100',
      ].join(' ')}
    >
      <div className="px-4 py-3 space-y-2">
        {/* Badge row */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${relationshipBadgeClass(item.evidence_relationship)}`}>
            {formatRelationshipLabel(item.evidence_relationship)}
          </span>
          <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${evidenceTypeBadgeClass(item.evidence_type)}`}>
            {item.evidence_type}
          </span>
          <span className="ml-auto text-xs text-slate-400 tabular-nums">
            {Math.round(item.relevance_score * 100)}% relevance
          </span>
        </div>

        {/* Page title */}
        {item.page_title && (
          <p className="text-xs font-medium text-slate-700 leading-snug">{item.page_title}</p>
        )}

        {/* Content excerpt */}
        {excerpt && (
          <p className="text-xs text-slate-600 leading-relaxed">
            {hasMore ? excerpt + '…' : item.content}
          </p>
        )}

        {/* Source label + URL row */}
        <div className="flex items-center gap-3 flex-wrap pt-0.5">
          <span className="text-xs font-mono bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded truncate max-w-[180px]">
            {item.source_label}
          </span>
          {item.url && (
            <a
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="text-xs text-blue-600 hover:underline flex items-center gap-1"
            >
              Source <ExternalLink className="h-3 w-3" />
            </a>
          )}
          {item.section_name && (
            <span className="text-xs text-slate-400 truncate">§ {item.section_name}</span>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────

export function EvidenceExplorer({
  evidence: initialEvidence,
  projectId,
  runId,
  liveNewEvidence,
  onOpenSource,
}: EvidenceExplorerProps) {
  const isStaticMode = !!initialEvidence;

  const [evidence, setEvidence] = useState<EvidenceItem[]>(initialEvidence ?? []);
  const [total, setTotal] = useState(initialEvidence?.length ?? 0);
  const [loading, setLoading] = useState(!isStaticMode);
  const [loadingMore, setLoadingMore] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);

  // New item IDs from SSE — highlighted briefly
  const [newIds, setNewIds] = useState<Set<string>>(new Set());
  const newIdTimers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  // Filters
  const [relFilter, setRelFilter] = useState<RelationshipFilter>('all');
  const [minRelevance, setMinRelevance] = useState(0);

  // Drawer
  const [selectedEvidence, setSelectedEvidence] = useState<EvidenceItem | null>(null);

  // ── Fetch (self-fetching mode) ─────────────────────────────────────────

  const fetchEvidence = useCallback(async (p: number, append = false) => {
    if (!projectId || !runId) return;
    try {
      const data = await getEvidence(projectId, runId);
      const allItems = data.items;
      const sliced = allItems.slice(0, p * PAGE_SIZE);
      if (append) {
        setEvidence((prev) => {
          const existingIds = new Set(prev.map((e) => e.id));
          return [...prev, ...sliced.filter((e) => !existingIds.has(e.id))];
        });
      } else {
        setEvidence(sliced);
      }
      setTotal(allItems.length);
      setHasMore(sliced.length < allItems.length);
    } catch {
      // keep existing
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [projectId, runId]);

  useEffect(() => {
    if (!isStaticMode) fetchEvidence(1);
  }, [isStaticMode, fetchEvidence]);

  // ── Live SSE updates ───────────────────────────────────────────────────

  useEffect(() => {
    if (!liveNewEvidence || liveNewEvidence.length === 0) return;
    setEvidence((prev) => {
      const existingIds = new Set(prev.map((e) => e.id));
      const truly_new = liveNewEvidence.filter((e) => !existingIds.has(e.id));
      if (truly_new.length === 0) return prev;
      return [...truly_new, ...prev];
    });
    setTotal((t) => t + liveNewEvidence.length);
    liveNewEvidence.forEach((e) => {
      setNewIds((prev) => new Set(Array.from(prev).concat(e.id)));
      const timer = setTimeout(() => {
        setNewIds((prev) => { const next = new Set(Array.from(prev)); next.delete(e.id); return next; });
        newIdTimers.current.delete(e.id);
      }, 3000);
      newIdTimers.current.set(e.id, timer);
    });
  }, [liveNewEvidence]);

  useEffect(() => {
    const timers = newIdTimers.current;
    return () => { timers.forEach((t) => clearTimeout(t)); };
  }, []);

  // ── Static mode sync ──────────────────────────────────────────────────

  useEffect(() => {
    if (isStaticMode && initialEvidence) {
      setEvidence(initialEvidence);
      setTotal(initialEvidence.length);
    }
  }, [isStaticMode, initialEvidence]);

  // ── Filtering ─────────────────────────────────────────────────────────

  const filtered = evidence.filter((e) => {
    if (relFilter !== 'all' && e.evidence_relationship !== relFilter) return false;
    if (e.relevance_score < minRelevance) return false;
    return true;
  });

  // ── Load more ─────────────────────────────────────────────────────────

  async function handleLoadMore() {
    const nextPage = page + 1;
    setPage(nextPage);
    setLoadingMore(true);
    await fetchEvidence(nextPage, true);
  }

  // ── Render ────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-20 rounded-lg bg-slate-100 animate-pulse" />
        ))}
      </div>
    );
  }

  const relFilters: { value: RelationshipFilter; label: string }[] = [
    { value: 'all', label: 'All' },
    { value: 'supports', label: 'Supports' },
    { value: 'contradicts', label: 'Contradicts' },
    { value: 'qualifies', label: 'Qualifies' },
    { value: 'contextualizes', label: 'Contextualizes' },
    { value: 'neutral', label: 'Neutral' },
  ];

  return (
    <>
      <div className="space-y-3">
        {/* Header */}
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-widest text-slate-400">
            Evidence
          </span>
          <span className="text-xs text-slate-500">
            {total} items{filtered.length !== total && ` · ${filtered.length} shown`}
          </span>
        </div>

        {/* Filter bar */}
        <div className="space-y-2">
          {/* Relationship chips */}
          <div className="flex items-center gap-1 flex-wrap">
            {relFilters.map((f) => (
              <button
                key={f.value}
                onClick={() => setRelFilter(f.value)}
                className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                  relFilter === f.value
                    ? 'bg-slate-800 text-white border-slate-800'
                    : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* Min relevance slider */}
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-400 shrink-0">Min relevance</span>
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={Math.round(minRelevance * 100)}
              onChange={(e) => setMinRelevance(parseInt(e.target.value, 10) / 100)}
              className="flex-1 h-1.5 accent-blue-600"
            />
            <span className="text-xs font-medium text-slate-600 w-8 text-right tabular-nums">
              {Math.round(minRelevance * 100)}%
            </span>
            {minRelevance > 0 && (
              <button
                onClick={() => setMinRelevance(0)}
                className="text-xs text-slate-400 hover:text-slate-600"
              >
                ×
              </button>
            )}
          </div>
        </div>

        {/* Empty state */}
        {filtered.length === 0 && (
          <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
            {evidence.length === 0
              ? <>
                  No evidence collected yet.
                  <p className="text-xs mt-1 text-slate-400">
                    Evidence items will appear here as agents analyse sources.
                  </p>
                </>
              : 'No evidence matches the current filters.'
            }
          </div>
        )}

        {/* Evidence list */}
        <div className="space-y-1.5">
          {filtered.map((item) => (
            <EvidenceRow
              key={item.id}
              item={item}
              isNew={newIds.has(item.id)}
              onClick={setSelectedEvidence}
            />
          ))}
        </div>

        {/* Load more */}
        {hasMore && relFilter === 'all' && minRelevance === 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={handleLoadMore}
            disabled={loadingMore}
            className="w-full"
          >
            {loadingMore
              ? <span className="flex items-center gap-2"><ChevronDown className="h-4 w-4 animate-bounce" />Loading…</span>
              : <span className="flex items-center gap-2"><ChevronDown className="h-4 w-4" />Load more evidence</span>
            }
          </Button>
        )}
      </div>

      {/* Detail drawer */}
      <EvidenceDetailDrawer
        evidence={selectedEvidence}
        onClose={() => setSelectedEvidence(null)}
        onOpenSource={onOpenSource}
      />
    </>
  );
}
