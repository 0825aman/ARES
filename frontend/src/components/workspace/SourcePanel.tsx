'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import {
  ExternalLink,
  BookOpen,
  CheckCircle2,
  Globe,
  FileText,
  GraduationCap,
  Search,
  X,
  ChevronDown,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { getSources, getSourceById } from '@/lib/api/runs';
import { SourceDetailDrawer } from './SourceDetailDrawer';
import type { Source } from '@/lib/types/run';

const PAGE_SIZE = 20;

interface SourcePanelProps {
  /** Static sources passed from a completed run (Phase 4 compat). When provided, skips fetch. */
  sources?: Source[];
  /** Used for live/active runs — component self-fetches using these IDs. */
  projectId?: string;
  runId?: string;
  /** New sources pushed from parent SSE state. */
  liveNewSources?: Source[];
  /** If set, programmatically open the drawer for this source ID (cross-link from Evidence drawer). */
  openSourceId?: string | null;
  /** Called after the cross-link drawer has been opened so parent can clear openSourceId. */
  onSourceOpened?: () => void;
}

type SourceTypeFilter = 'all' | 'web' | 'academic' | 'document' | 'news';

function sourceTypeLabel(type: string): string {
  const map: Record<string, string> = { web: 'Web', academic: 'Academic', news: 'News', document: 'Document' };
  return map[type] ?? type;
}

function SourceTypeIcon({ type }: { type: string }) {
  if (type === 'academic') return <GraduationCap className="h-3.5 w-3.5" />;
  if (type === 'document') return <FileText className="h-3.5 w-3.5" />;
  return <Globe className="h-3.5 w-3.5" />;
}

function formatRelativeTime(iso: string): string {
  try {
    const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return new Date(iso).toLocaleDateString();
  } catch { return ''; }
}

interface SourceRowProps {
  source: Source;
  isNew?: boolean;
  onClick: (source: Source) => void;
}

function SourceRow({ source, isNew, onClick }: SourceRowProps) {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onClick(source)}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onClick(source); }}
      className={`group flex items-start gap-3 rounded-lg border px-4 py-3 cursor-pointer transition-all hover:border-blue-300 hover:bg-blue-50/40 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-1 ${
        isNew
          ? 'border-blue-200 bg-blue-50 animate-fade-in'
          : 'border-slate-100 bg-white'
      }`}
    >
      {/* Type icon */}
      <div className="mt-0.5 text-slate-400 shrink-0 group-hover:text-blue-500 transition-colors">
        <SourceTypeIcon type={source.source_type} />
      </div>

      <div className="flex-1 min-w-0 space-y-1">
        {/* Title row */}
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm font-medium text-slate-800 leading-snug">
            {source.title ?? <span className="italic text-slate-400">Untitled</span>}
          </p>
          <div className="flex gap-1 shrink-0">
            <Badge variant="secondary" className="text-xs px-1.5 py-0">
              {sourceTypeLabel(source.source_type)}
            </Badge>
            {source.is_peer_reviewed && (
              <Badge className="text-xs px-1.5 py-0 bg-emerald-100 text-emerald-700 hover:bg-emerald-100">
                <CheckCircle2 className="h-3 w-3 mr-0.5" />
                Peer-reviewed
              </Badge>
            )}
          </div>
        </div>

        {/* Venue / publisher */}
        {(source.venue || source.publisher) && (
          <p className="text-xs text-slate-500">
            {source.venue ?? source.publisher}
            {source.publication_date && (
              <span className="ml-1 text-slate-400">· {source.publication_date.slice(0, 4)}</span>
            )}
          </p>
        )}

        {/* URL row */}
        <div className="flex items-center gap-3 flex-wrap">
          {source.doi && (
            <a
              href={`https://doi.org/${source.doi}`}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="text-xs text-blue-600 hover:underline flex items-center gap-1"
            >
              DOI: {source.doi}
              <ExternalLink className="h-3 w-3" />
            </a>
          )}
          {!source.doi && source.url && (
            <a
              href={source.url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="text-xs text-blue-600 hover:underline flex items-center gap-1 truncate max-w-xs"
            >
              <BookOpen className="h-3 w-3 shrink-0" />
              {source.url}
              <ExternalLink className="h-3 w-3 shrink-0" />
            </a>
          )}
          <span className="text-xs text-slate-400 ml-auto">{formatRelativeTime(source.retrieved_at)}</span>
        </div>
      </div>
    </div>
  );
}

export function SourcePanel({
  sources: initialSources,
  projectId,
  runId,
  liveNewSources,
  openSourceId,
  onSourceOpened,
}: SourcePanelProps) {
  // If static sources provided (Phase 4 / completed run), use them directly
  const isStaticMode = !!initialSources;

  const [sources, setSources] = useState<Source[]>(initialSources ?? []);
  const [total, setTotal] = useState(initialSources?.length ?? 0);
  const [loading, setLoading] = useState(!isStaticMode);
  const [loadingMore, setLoadingMore] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);

  // New source IDs from SSE — highlighted briefly
  const [newSourceIds, setNewSourceIds] = useState<Set<string>>(new Set());
  const newSourceTimers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  // Filter state
  const [typeFilter, setTypeFilter] = useState<SourceTypeFilter>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Drawer state
  const [selectedSource, setSelectedSource] = useState<Source | null>(null);

  // ── Cross-link: open a specific source by ID (from Evidence drawer) ───────
  useEffect(() => {
    if (!openSourceId) return;
    // First check if the source is already in our local list
    const local = sources.find((s) => s.id === openSourceId);
    if (local) {
      setSelectedSource(local);
      onSourceOpened?.();
      return;
    }
    // Otherwise fetch it
    if (projectId && runId) {
      getSourceById(projectId, runId, openSourceId)
        .then((src) => {
          setSelectedSource(src);
          onSourceOpened?.();
        })
        .catch(() => onSourceOpened?.());
    } else {
      onSourceOpened?.();
    }
  }, [openSourceId]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Initial load (self-fetching mode) ─────────────────────────────────────

  const fetchSources = useCallback(async (p: number, append = false) => {
    if (!projectId || !runId) return;
    try {
      const offset = (p - 1) * PAGE_SIZE;
      const data = await getSources(projectId, runId);
      // Current getSources API returns all items — we slice client-side for pagination
      const allItems = data.items;
      const sliced = allItems.slice(0, p * PAGE_SIZE);

      if (append) {
        setSources((prev) => {
          const existingIds = new Set(prev.map((s) => s.id));
          const newOnes = sliced.filter((s) => !existingIds.has(s.id));
          return [...prev, ...newOnes];
        });
      } else {
        setSources(sliced);
      }
      setTotal(allItems.length);
      setHasMore(sliced.length < allItems.length);
    } catch {
      // keep existing state
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [projectId, runId]);

  useEffect(() => {
    if (!isStaticMode) {
      fetchSources(1);
    }
  }, [isStaticMode, fetchSources]);

  // ── Live SSE updates ───────────────────────────────────────────────────────

  useEffect(() => {
    if (!liveNewSources || liveNewSources.length === 0) return;

    setSources((prev) => {
      const existingIds = new Set(prev.map((s) => s.id));
      const truly_new = liveNewSources.filter((s) => !existingIds.has(s.id));
      if (truly_new.length === 0) return prev;
      return [...truly_new, ...prev];
    });
    setTotal((t) => t + liveNewSources.length);

    // Highlight new items for 3 seconds
    liveNewSources.forEach((s) => {
      setNewSourceIds((prev) => new Set(Array.from(prev).concat(s.id)));
      const timer = setTimeout(() => {
        setNewSourceIds((prev) => { const next = new Set(Array.from(prev)); next.delete(s.id); return next; });
        newSourceTimers.current.delete(s.id);
      }, 3000);
      newSourceTimers.current.set(s.id, timer);
    });
  }, [liveNewSources]);

  // Cleanup highlight timers on unmount
  useEffect(() => {
    const timers = newSourceTimers.current;
    return () => {
      timers.forEach((t) => clearTimeout(t));
    };
  }, []);

  // ── Static mode: sync with prop changes ───────────────────────────────────

  useEffect(() => {
    if (isStaticMode && initialSources) {
      setSources(initialSources);
      setTotal(initialSources.length);
    }
  }, [isStaticMode, initialSources]);

  // ── Filtering (client-side) ────────────────────────────────────────────────

  const filteredSources = sources.filter((s) => {
    if (typeFilter !== 'all' && s.source_type !== typeFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const inTitle = (s.title ?? '').toLowerCase().includes(q);
      const inUrl = (s.url ?? '').toLowerCase().includes(q);
      const inVenue = (s.venue ?? '').toLowerCase().includes(q);
      if (!inTitle && !inUrl && !inVenue) return false;
    }
    return true;
  });

  // ── Load more ─────────────────────────────────────────────────────────────

  async function handleLoadMore() {
    const nextPage = page + 1;
    setPage(nextPage);
    setLoadingMore(true);
    await fetchSources(nextPage, true);
  }

  // ── Render ────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-16 rounded-lg bg-slate-100 animate-pulse" />
        ))}
      </div>
    );
  }

  const typeFilters: { value: SourceTypeFilter; label: string }[] = [
    { value: 'all', label: 'All' },
    { value: 'web', label: 'Web' },
    { value: 'academic', label: 'Academic' },
    { value: 'document', label: 'Document' },
    { value: 'news', label: 'News' },
  ];

  return (
    <>
      <div className="space-y-3">
        {/* Header */}
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-widest text-slate-400">
            Sources
          </span>
          <span className="text-xs text-slate-500">
            {total} collected{filteredSources.length !== total && ` · ${filteredSources.length} shown`}
          </span>
        </div>

        {/* Filter bar */}
        <div className="space-y-2">
          {/* Type chips */}
          <div className="flex items-center gap-1 flex-wrap">
            {typeFilters.map((f) => (
              <button
                key={f.value}
                onClick={() => setTypeFilter(f.value)}
                className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                  typeFilter === f.value
                    ? 'bg-slate-800 text-white border-slate-800'
                    : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* Search box */}
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400 pointer-events-none" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by title or URL…"
              className="pl-8 pr-8 h-8 text-sm"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Empty state */}
        {filteredSources.length === 0 && !loading && (
          <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
            {sources.length === 0
              ? <>
                  No sources collected yet.
                  <p className="text-xs mt-1 text-slate-400">
                    Sources will appear here as the research agents browse the web.
                  </p>
                </>
              : `No sources match the current filters.`
            }
          </div>
        )}

        {/* Source list */}
        <div className="space-y-1.5">
          {filteredSources.map((source) => (
            <SourceRow
              key={source.id}
              source={source}
              isNew={newSourceIds.has(source.id)}
              onClick={setSelectedSource}
            />
          ))}
        </div>

        {/* Load more */}
        {hasMore && !searchQuery && typeFilter === 'all' && (
          <Button
            variant="outline"
            size="sm"
            onClick={handleLoadMore}
            disabled={loadingMore}
            className="w-full"
          >
            {loadingMore ? (
              <span className="flex items-center gap-2">
                <ChevronDown className="h-4 w-4 animate-bounce" />
                Loading…
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <ChevronDown className="h-4 w-4" />
                Load more sources
              </span>
            )}
          </Button>
        )}
      </div>

      {/* Detail drawer */}
      <SourceDetailDrawer
        source={selectedSource}
        onClose={() => setSelectedSource(null)}
      />
    </>
  );
}
