'use client';

import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { Badge } from '@/components/ui/badge';
import {
  ExternalLink,
  Globe,
  FileText,
  GraduationCap,
  CheckCircle2,
  Calendar,
  Building2,
} from 'lucide-react';
import type { Source } from '@/lib/types/run';

interface SourceDetailDrawerProps {
  source: Source | null;
  onClose: () => void;
}

function SourceTypeIcon({ type }: { type: string }) {
  if (type === 'academic') return <GraduationCap className="h-4 w-4" />;
  if (type === 'document') return <FileText className="h-4 w-4" />;
  return <Globe className="h-4 w-4" />;
}

function sourceTypeLabel(type: string): string {
  const map: Record<string, string> = {
    web: 'Web',
    academic: 'Academic',
    news: 'News',
    document: 'Document',
  };
  return map[type] ?? type;
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString([], {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

export function SourceDetailDrawer({ source, onClose }: SourceDetailDrawerProps) {
  return (
    <Sheet open={source !== null} onOpenChange={(open) => { if (!open) onClose(); }}>
      <SheetContent side="right" className="w-full sm:max-w-lg overflow-y-auto">
        {source && (
          <>
            <SheetHeader className="pb-4 border-b border-slate-100">
              <div className="flex items-start gap-3">
                <div className="mt-1 text-slate-500 shrink-0">
                  <SourceTypeIcon type={source.source_type} />
                </div>
                <div className="flex-1 min-w-0">
                  <SheetTitle className="text-base font-semibold text-slate-900 leading-snug pr-6">
                    {source.title ?? <span className="italic text-slate-400">Untitled Source</span>}
                  </SheetTitle>
                  <div className="flex items-center gap-2 mt-2 flex-wrap">
                    <Badge variant="secondary" className="text-xs">
                      {sourceTypeLabel(source.source_type)}
                    </Badge>
                    {source.is_peer_reviewed && (
                      <Badge className="text-xs bg-emerald-100 text-emerald-700 hover:bg-emerald-100">
                        <CheckCircle2 className="h-3 w-3 mr-1" />
                        Peer-reviewed
                      </Badge>
                    )}
                    {!source.is_accessible && (
                      <Badge variant="destructive" className="text-xs">
                        Inaccessible
                      </Badge>
                    )}
                  </div>
                </div>
              </div>
            </SheetHeader>

            <div className="mt-4 space-y-5">
              {/* URL / DOI */}
              {(source.url || source.doi) && (
                <div className="space-y-1.5">
                  <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">
                    Link
                  </p>
                  {source.doi && (
                    <a
                      href={`https://doi.org/${source.doi}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-blue-600 hover:underline flex items-center gap-1.5 break-all"
                    >
                      DOI: {source.doi}
                      <ExternalLink className="h-3.5 w-3.5 shrink-0" />
                    </a>
                  )}
                  {!source.doi && source.url && (
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-blue-600 hover:underline flex items-center gap-1.5 break-all"
                    >
                      {source.url}
                      <ExternalLink className="h-3.5 w-3.5 shrink-0" />
                    </a>
                  )}
                </div>
              )}

              {/* Publication metadata */}
              {(source.venue || source.publisher || source.publication_date || source.authors) && (
                <div className="space-y-1.5">
                  <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">
                    Publication
                  </p>
                  <div className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2.5 space-y-1.5 text-sm">
                    {source.venue && (
                      <div className="flex items-start gap-2">
                        <Building2 className="h-3.5 w-3.5 text-slate-400 mt-0.5 shrink-0" />
                        <span className="text-slate-700">{source.venue}</span>
                      </div>
                    )}
                    {source.publisher && !source.venue && (
                      <div className="flex items-start gap-2">
                        <Building2 className="h-3.5 w-3.5 text-slate-400 mt-0.5 shrink-0" />
                        <span className="text-slate-700">{source.publisher}</span>
                      </div>
                    )}
                    {source.publication_date && (
                      <div className="flex items-center gap-2">
                        <Calendar className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                        <span className="text-slate-700">{source.publication_date}</span>
                      </div>
                    )}
                    {source.authors && (
                      <p className="text-slate-500 text-xs pl-5">
                        {(() => {
                          try {
                            const parsed = JSON.parse(source.authors);
                            return Array.isArray(parsed) ? parsed.join(', ') : source.authors;
                          } catch {
                            return source.authors;
                          }
                        })()}
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* Credibility notes */}
              {source.credibility_notes && (
                <div className="space-y-1.5">
                  <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">
                    Credibility Notes
                  </p>
                  <p className="text-sm text-slate-600 leading-relaxed">
                    {source.credibility_notes}
                  </p>
                </div>
              )}

              {/* Retrieval metadata */}
              <div className="space-y-1.5">
                <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">
                  Retrieval
                </p>
                <div className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2.5 space-y-1 text-xs text-slate-600">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Provider</span>
                    <span className="font-medium">{source.retrieval_provider}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Retrieved</span>
                    <span>{formatDate(source.retrieved_at)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Source ID</span>
                    <span className="font-mono text-xs text-slate-400 truncate max-w-[180px]">
                      {source.id}
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
