'use client';

import { X, ExternalLink, CheckCircle2, XCircle, FileText, BookOpen, ArrowRight } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { Citation } from '@/lib/types/run';

interface CitationDetailProps {
  citation: Citation;
  onClose: () => void;
}

export function CitationDetail({ citation, onClose }: CitationDetailProps) {
  return (
    <div className="fixed inset-0 z-50 flex justify-end" onClick={onClose}>
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/20" />

      {/* Slide-out panel */}
      <div
        className="relative z-10 w-full max-w-md bg-white shadow-xl flex flex-col h-full border-l border-slate-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200">
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm font-semibold text-slate-800">
              {citation.citation_key}
            </span>
            <Badge
              variant="secondary"
              className={`text-xs ${
                citation.is_verified
                  ? 'bg-emerald-100 text-emerald-700'
                  : 'bg-slate-100 text-slate-500'
              }`}
            >
              {citation.is_verified ? (
                <><CheckCircle2 className="h-3 w-3 mr-1" /> Verified</>
              ) : (
                <><XCircle className="h-3 w-3 mr-1" /> Unverified</>
              )}
            </Badge>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} className="h-7 w-7">
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
          {/* APA formatted citation */}
          {citation.apa_formatted && (
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-1.5">
                APA Citation
              </p>
              <p className="text-sm text-slate-700 leading-relaxed bg-slate-50 px-3 py-2.5 rounded border border-slate-100">
                {citation.apa_formatted}
              </p>
            </div>
          )}

          {/* Traceability chain */}
          <div>
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">
              Traceability Chain
            </p>
            <div className="space-y-2">
              {/* Report → Citation */}
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <FileText className="h-3.5 w-3.5 text-blue-500" />
                <span className="font-medium text-slate-700">Report</span>
                <ArrowRight className="h-3 w-3 text-slate-300" />
                <span className="font-mono text-slate-600">{citation.citation_key}</span>
              </div>

              {/* Reference details */}
              <div className="ml-5 space-y-1 text-xs text-slate-500">
                {citation.page_reference && (
                  <p><span className="font-medium">Page:</span> {citation.page_reference}</p>
                )}
                {citation.section_reference && (
                  <p><span className="font-medium">Section:</span> {citation.section_reference}</p>
                )}
              </div>

              {/* Citation → Evidence */}
              <div className="flex items-center gap-2 text-xs text-slate-500 mt-1">
                <BookOpen className="h-3.5 w-3.5 text-violet-500" />
                <span className="font-medium text-slate-700">Evidence Record</span>
              </div>
              <div className="ml-5 text-xs text-slate-400 font-mono break-all">
                {citation.evidence_id}
              </div>

              {/* Evidence → Source */}
              {citation.source_id && (
                <>
                  <div className="flex items-center gap-2 text-xs text-slate-500 mt-1">
                    <BookOpen className="h-3.5 w-3.5 text-emerald-500" />
                    <span className="font-medium text-slate-700">Source</span>
                  </div>
                  <div className="ml-5 text-xs text-slate-400 font-mono break-all">
                    {citation.source_id}
                  </div>
                </>
              )}
            </div>
          </div>

          {/* DOI / URL */}
          {(citation.doi || citation.url) && (
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-1.5">
                External Link
              </p>
              {citation.doi ? (
                <a
                  href={`https://doi.org/${citation.doi}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-blue-600 hover:underline flex items-center gap-1"
                >
                  DOI: {citation.doi}
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
              ) : citation.url ? (
                <a
                  href={citation.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-blue-600 hover:underline flex items-center gap-1 break-all"
                >
                  {citation.url}
                  <ExternalLink className="h-3.5 w-3.5 shrink-0" />
                </a>
              ) : null}
            </div>
          )}

          {/* Validation notes */}
          {citation.validation_notes && (
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-1.5">
                Validation Notes
              </p>
              <p className="text-xs text-amber-700 bg-amber-50 px-3 py-2 rounded leading-relaxed">
                {citation.validation_notes}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
