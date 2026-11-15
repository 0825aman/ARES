'use client';

import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { Badge } from '@/components/ui/badge';
import { ExternalLink, FileText, Globe, Hash, BookOpen } from 'lucide-react';
import type { EvidenceItem } from '@/lib/types/run';

interface EvidenceDetailDrawerProps {
  evidence: EvidenceItem | null;
  onClose: () => void;
  /** Called when user clicks the source link to cross-open the SourcePanel drawer */
  onOpenSource?: (sourceId: string) => void;
}

function relationshipBadgeClass(rel: string): string {
  switch (rel) {
    case 'supports': return 'bg-emerald-100 text-emerald-700 border-emerald-200';
    case 'contradicts': return 'bg-red-100 text-red-700 border-red-200';
    case 'qualifies': return 'bg-amber-100 text-amber-700 border-amber-200';
    case 'contextualizes': return 'bg-blue-100 text-blue-700 border-blue-200';
    default: return 'bg-slate-100 text-slate-600 border-slate-200';
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

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString([], {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch { return iso; }
}

export function EvidenceDetailDrawer({
  evidence,
  onClose,
  onOpenSource,
}: EvidenceDetailDrawerProps) {
  return (
    <Sheet open={evidence !== null} onOpenChange={(open) => { if (!open) onClose(); }}>
      <SheetContent side="right" className="w-full sm:max-w-lg overflow-y-auto">
        {evidence && (
          <>
            <SheetHeader className="pb-4 border-b border-slate-100">
              <div className="space-y-2">
                {/* Relationship + type badges */}
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${relationshipBadgeClass(evidence.evidence_relationship)}`}>
                    {formatRelationshipLabel(evidence.evidence_relationship)}
                  </span>
                  <span className={`text-xs font-medium px-2 py-0.5 rounded ${evidenceTypeBadgeClass(evidence.evidence_type)}`}>
                    {evidence.evidence_type}
                  </span>
                  {evidence.extraction_confidence !== null && (
                    <span className="text-xs text-slate-400 ml-auto">
                      Confidence: {Math.round((evidence.extraction_confidence ?? 0) * 100)}%
                    </span>
                  )}
                </div>

                {/* Page title */}
                {evidence.page_title && (
                  <SheetTitle className="text-sm font-medium text-slate-800 leading-snug">
                    {evidence.page_title}
                  </SheetTitle>
                )}

                {/* Relevance score */}
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400">Relevance</span>
                  <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500 rounded-full"
                      style={{ width: `${Math.round(evidence.relevance_score * 100)}%` }}
                    />
                  </div>
                  <span className="text-xs font-medium text-slate-600 tabular-nums w-8 text-right">
                    {Math.round(evidence.relevance_score * 100)}%
                  </span>
                </div>
              </div>
            </SheetHeader>

            <div className="mt-4 space-y-5">
              {/* Evidence content */}
              {evidence.content && (
                <div className="space-y-1.5">
                  <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">
                    Evidence Content
                  </p>
                  <div className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-3 text-sm text-slate-700 leading-relaxed max-h-48 overflow-y-auto">
                    {evidence.content}
                  </div>
                </div>
              )}

              {/* Section context */}
              {evidence.section_name && (
                <div className="space-y-1">
                  <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">
                    Section
                  </p>
                  <p className="text-sm text-slate-600">§ {evidence.section_name}</p>
                </div>
              )}

              {/* Source origin */}
              <div className="space-y-1.5">
                <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">
                  Source
                </p>
                <div className="rounded-lg border border-slate-100 bg-white px-3 py-2.5 space-y-2">
                  {/* Source label + type */}
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400 shrink-0">
                      {evidence.source_type === 'document'
                        ? <FileText className="h-3.5 w-3.5" />
                        : <Globe className="h-3.5 w-3.5" />
                      }
                    </span>
                    <span className="text-sm font-medium text-slate-700 truncate">
                      {evidence.source_label}
                    </span>
                    <Badge variant="secondary" className="text-xs ml-auto shrink-0">
                      {evidence.source_type}
                    </Badge>
                  </div>

                  {/* URL */}
                  {evidence.url && (
                    <a
                      href={evidence.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-blue-600 hover:underline flex items-center gap-1 break-all"
                    >
                      <BookOpen className="h-3 w-3 shrink-0" />
                      {evidence.url}
                      <ExternalLink className="h-3 w-3 shrink-0" />
                    </a>
                  )}

                  {/* Document chunk info */}
                  {evidence.document_id && (
                    <div className="text-xs text-slate-400 flex items-center gap-1.5">
                      <Hash className="h-3 w-3" />
                      {evidence.chunk_index !== null && `Chunk ${evidence.chunk_index}`}
                      {evidence.page_number !== null && ` · Page ${evidence.page_number}`}
                    </div>
                  )}

                  {/* Cross-link to source drawer */}
                  {evidence.source_id && onOpenSource && (
                    <button
                      onClick={() => { onClose(); onOpenSource(evidence.source_id!); }}
                      className="text-xs text-blue-600 hover:underline flex items-center gap-1 mt-1"
                    >
                      View source details →
                    </button>
                  )}
                </div>
              </div>

              {/* Extraction metadata */}
              <div className="space-y-1.5">
                <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">
                  Extraction
                </p>
                <div className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2.5 space-y-1 text-xs text-slate-600">
                  {evidence.extraction_method && (
                    <div className="flex justify-between">
                      <span className="text-slate-400">Method</span>
                      <span className="font-medium">{evidence.extraction_method}</span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="text-slate-400">Retrieved</span>
                    <span>{formatDate(evidence.retrieved_at)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Evidence ID</span>
                    <span className="font-mono text-xs text-slate-400 truncate max-w-[180px]">
                      {evidence.id}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
