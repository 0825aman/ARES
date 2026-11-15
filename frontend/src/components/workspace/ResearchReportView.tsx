'use client';

import { useState } from 'react';
import { ExternalLink, FileText, BookOpen, AlertTriangle, Info, CheckCircle2, Terminal } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CitationDetail } from './CitationDetail';
import type { ResearchReport, EvidenceReference, Citation } from '@/lib/types/run';

interface ResearchReportViewProps {
  report: ResearchReport;
  citations?: Citation[];
}

function SourceBadge({ source }: { source: EvidenceReference }) {
  return (
    <span className="inline-flex items-center gap-1 font-mono text-xs bg-slate-950 text-cyan-300 border border-cyan-500/40 px-2 py-0.5 rounded font-bold">
      {source.source_label}
    </span>
  );
}

/**
 * Render a text string with [SOURCE N] patterns replaced by clickable chips.
 */
function TextWithCitations({
  text,
  citations,
  onCitationClick,
}: {
  text: string;
  citations: Citation[];
  onCitationClick: (c: Citation) => void;
}) {
  const citationMap = new Map(citations.map((c) => [c.citation_key, c]));
  const parts = text.split(/(\[SOURCE \d+\])/gi);

  return (
    <>
      {parts.map((part, i) => {
        const citation = citationMap.get(part);
        if (citation) {
          return (
            <button
              key={i}
              onClick={() => onCitationClick(citation)}
              className={`inline-flex items-center font-mono text-xs px-2 py-0.5 rounded border transition-colors mx-0.5 font-bold ${
                citation.is_verified
                  ? 'bg-emerald-500/20 text-emerald-200 border-emerald-500/50 hover:bg-emerald-500/30 shadow-[0_0_8px_rgba(16,185,129,0.25)]'
                  : 'bg-slate-800 text-slate-100 border-slate-600 hover:bg-slate-700'
              }`}
              title={citation.apa_formatted ?? part}
            >
              {citation.is_verified && <CheckCircle2 className="h-3 w-3 mr-1 text-emerald-400" />}
              {part}
            </button>
          );
        }
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}

export function ResearchReportView({ report, citations = [] }: ResearchReportViewProps) {
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);

  const webSources = report.sources.filter((s) => s.type === 'web');
  const docSources = report.sources.filter((s) => s.type === 'document');

  return (
    <>
      <div className="space-y-4">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
          <div>
            <h2 className="font-mono text-base font-bold text-white flex items-center gap-2">
              <Terminal className="h-4 w-4 text-emerald-400" />
              SYNTHESIS REPORT // GROUNDED INTELLIGENCE
            </h2>
            <p className="font-mono text-xs text-slate-300 mt-1 font-medium">
              Generated {new Date(report.generated_at).toLocaleString()}
            </p>
          </div>
          <div className="flex gap-2 shrink-0 font-mono text-xs font-bold">
            {webSources.length > 0 && (
              <Badge
                variant="outline"
                className="border-blue-500/40 bg-blue-500/20 text-blue-300"
              >
                {webSources.length} web source{webSources.length !== 1 ? 's' : ''}
              </Badge>
            )}
            {docSources.length > 0 && (
              <Badge
                variant="outline"
                className="border-cyan-500/40 bg-cyan-500/20 text-cyan-300"
              >
                {docSources.length} document{docSources.length !== 1 ? 's' : ''}
              </Badge>
            )}
          </div>
        </div>

        {/* Executive Summary */}
        <Card className="tech-panel border-slate-800 bg-slate-900 shadow-xl">
          <CardHeader className="py-3 px-5 border-b border-slate-800">
            <CardTitle className="font-mono text-xs font-bold uppercase tracking-wider text-white">
              Executive Summary
            </CardTitle>
          </CardHeader>
          <CardContent className="p-5">
            <p className="text-sm text-slate-100 leading-relaxed font-sans font-normal">
              {report.executive_summary}
            </p>
          </CardContent>
        </Card>

        {/* Key Findings */}
        {report.key_findings.length > 0 && (
          <Card className="tech-panel border-slate-800 bg-slate-900 shadow-xl">
            <CardHeader className="py-3 px-5 border-b border-slate-800">
              <CardTitle className="font-mono text-xs font-bold uppercase tracking-wider text-white">
                Key Verified Findings
              </CardTitle>
            </CardHeader>
            <CardContent className="p-5">
              <ol className="space-y-3">
                {report.key_findings.map((finding, i) => (
                  <li key={i} className="flex gap-3 text-sm text-white">
                    <span className="font-mono font-bold text-blue-400 shrink-0">
                      0{i + 1}.
                    </span>
                    <span className="leading-relaxed font-sans font-normal text-slate-100">
                      {citations.length > 0 ? (
                        <TextWithCitations
                          text={finding}
                          citations={citations}
                          onCitationClick={setSelectedCitation}
                        />
                      ) : (
                        finding
                      )}
                    </span>
                  </li>
                ))}
              </ol>
            </CardContent>
          </Card>
        )}

        {/* Observations */}
        {report.observations && (
          <Card className="tech-panel border-slate-800 bg-slate-900 shadow-xl">
            <CardHeader className="py-3 px-5 border-b border-slate-800">
              <CardTitle className="font-mono text-xs font-bold uppercase tracking-wider text-cyan-300 flex items-center gap-1.5">
                <Info className="h-4 w-4" />
                Cross-Corroborated Observations
              </CardTitle>
            </CardHeader>
            <CardContent className="p-5">
              <p className="text-sm text-slate-100 leading-relaxed font-sans font-normal">
                {report.observations}
              </p>
            </CardContent>
          </Card>
        )}

        {/* Contradictions */}
        {report.contradictions && (
          <Card className="tech-panel border-amber-500/50 bg-amber-950/30 shadow-xl">
            <CardHeader className="py-3 px-5 border-b border-amber-500/40">
              <CardTitle className="font-mono text-xs font-bold uppercase tracking-wider text-amber-300 flex items-center gap-1.5">
                <AlertTriangle className="h-4 w-4" />
                Contradictions &amp; Inconsistencies Detected
              </CardTitle>
            </CardHeader>
            <CardContent className="p-5">
              <p className="text-sm text-amber-100 leading-relaxed font-sans font-normal">
                {report.contradictions}
              </p>
            </CardContent>
          </Card>
        )}

        {/* Limitations */}
        <Card className="tech-panel border-slate-800 bg-slate-950 shadow-xl">
          <CardHeader className="py-3 px-5 border-b border-slate-800">
            <CardTitle className="font-mono text-xs font-bold uppercase tracking-wider text-slate-300">
              Methodological Limitations &amp; Boundary Conditions
            </CardTitle>
          </CardHeader>
          <CardContent className="p-5">
            <p className="text-xs text-slate-200 leading-relaxed font-mono font-medium">
              {report.limitations}
            </p>
          </CardContent>
        </Card>

        {/* Sources & References */}
        {report.sources.length > 0 && (
          <Card className="tech-panel border-slate-800 bg-slate-900 shadow-xl">
            <CardHeader className="py-3 px-5 border-b border-slate-800">
              <CardTitle className="font-mono text-xs font-bold uppercase tracking-wider text-white flex items-center gap-1.5">
                <BookOpen className="h-4 w-4 text-blue-400" />
                Evidence Grounding &amp; Citations
              </CardTitle>
            </CardHeader>
            <CardContent className="p-5">
              <div className="space-y-3.5 divide-y divide-slate-800">
                {report.evidence_used.map((ev, i) => (
                  <div key={i} className="flex gap-3.5 pt-3.5 first:pt-0">
                    <SourceBadge source={ev} />
                    <div className="flex-1 min-w-0">
                      {ev.source_type === 'web' ? (
                        <div>
                          {ev.url && (
                            <a
                              href={ev.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="font-mono text-xs text-blue-300 hover:text-white hover:underline flex items-center gap-1 font-bold"
                            >
                              {ev.title || ev.url}
                              <ExternalLink className="h-3.5 w-3.5 shrink-0" />
                            </a>
                          )}
                          {ev.excerpt && (
                            <p className="text-xs text-slate-200 mt-1 line-clamp-2 leading-relaxed font-normal">
                              {ev.excerpt}
                            </p>
                          )}
                        </div>
                      ) : (
                        <div className="flex items-center gap-2 font-mono text-xs">
                          <FileText className="h-4 w-4 text-slate-400 shrink-0" />
                          <span className="text-white font-bold">{ev.filename}</span>
                          {ev.page_number != null && (
                            <span className="text-slate-300 font-medium">· page {ev.page_number}</span>
                          )}
                          {ev.chunk_index != null && ev.page_number == null && (
                            <span className="text-slate-300 font-medium">· section {ev.chunk_index + 1}</span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Citation detail slide-out */}
      {selectedCitation && (
        <CitationDetail
          citation={selectedCitation}
          onClose={() => setSelectedCitation(null)}
        />
      )}
    </>
  );
}
