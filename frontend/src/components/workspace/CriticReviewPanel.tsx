'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight, CheckCircle2, AlertTriangle, XCircle, Bot } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { CriticReview } from '@/lib/types/run';

interface CriticReviewPanelProps {
  review: CriticReview;
}

function assessmentConfig(assessment: CriticReview['overall_assessment']) {
  switch (assessment) {
    case 'strong':
      return { label: 'Strong', className: 'bg-emerald-100 text-emerald-700', icon: <CheckCircle2 className="h-4 w-4" /> };
    case 'adequate':
      return { label: 'Adequate', className: 'bg-blue-100 text-blue-700', icon: <CheckCircle2 className="h-4 w-4" /> };
    case 'weak':
      return { label: 'Weak', className: 'bg-amber-100 text-amber-700', icon: <AlertTriangle className="h-4 w-4" /> };
    case 'inadequate':
      return { label: 'Inadequate', className: 'bg-red-100 text-red-700', icon: <XCircle className="h-4 w-4" /> };
  }
}

function reviewStatusConfig(status: CriticReview['review_status']) {
  switch (status) {
    case 'approved':
      return { label: 'Approved', className: 'bg-emerald-100 text-emerald-700' };
    case 'needs_attention':
      return { label: 'Needs Attention', className: 'bg-amber-100 text-amber-700' };
    case 'rejected':
      return { label: 'Rejected', className: 'bg-red-100 text-red-700' };
    default:
      return { label: status, className: 'bg-slate-100 text-slate-600' };
  }
}

function IssueSection({ title, items }: { title: string; items: string[] }) {
  const [open, setOpen] = useState(false);
  if (items.length === 0) return null;

  return (
    <div className="border border-slate-100 rounded-md overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-3 py-2 bg-slate-50 text-left hover:bg-slate-100 transition-colors"
      >
        <span className="text-xs font-medium text-slate-700">
          {title} <span className="text-slate-400 font-normal">({items.length})</span>
        </span>
        {open ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <ChevronRight className="h-4 w-4 text-slate-400" />}
      </button>
      {open && (
        <ul className="px-3 py-2 space-y-1">
          {items.map((item, i) => (
            <li key={i} className="text-xs text-slate-600 flex gap-2">
              <span className="text-slate-300 shrink-0">·</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function CriticReviewPanel({ review }: CriticReviewPanelProps) {
  const assessment = assessmentConfig(review.overall_assessment);
  const statusCfg = reviewStatusConfig(review.review_status);

  const totalIssues =
    review.unsupported_claims.length +
    review.citation_issues.length +
    review.contradictory_findings.length +
    review.missing_evidence.length +
    review.source_quality_issues.length +
    review.reasoning_issues.length;

  return (
    <Card className="shadow-sm">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <CardTitle className="text-sm font-semibold text-slate-800 flex items-center gap-2">
            <Bot className="h-4 w-4 text-violet-600" />
            Critic Review
            <span className="text-xs font-normal text-slate-400">v{review.review_version}</span>
          </CardTitle>
          <div className="flex items-center gap-2">
            <span className={`inline-flex items-center gap-1.5 text-xs px-2 py-1 rounded font-medium ${assessment.className}`}>
              {assessment.icon}
              {assessment.label}
            </span>
            <span className={`text-xs px-2 py-1 rounded font-medium ${statusCfg.className}`}>
              {statusCfg.label}
            </span>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-0 space-y-3">
        {/* Summary */}
        {review.review_summary && (
          <p className="text-sm text-slate-600 leading-relaxed">{review.review_summary}</p>
        )}

        {/* Recommended action */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">Recommended action:</span>
          <Badge variant="secondary" className="text-xs">
            {review.recommended_action.replace(/_/g, ' ')}
          </Badge>
        </div>

        {/* Issue sections */}
        {totalIssues > 0 ? (
          <div className="space-y-1.5">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Issues Found</p>
            <IssueSection title="Unsupported Claims" items={review.unsupported_claims} />
            <IssueSection title="Citation Issues" items={review.citation_issues} />
            <IssueSection title="Contradictory Findings" items={review.contradictory_findings} />
            <IssueSection title="Missing Evidence" items={review.missing_evidence} />
            <IssueSection title="Source Quality Issues" items={review.source_quality_issues} />
            <IssueSection title="Reasoning Issues" items={review.reasoning_issues} />
          </div>
        ) : (
          <div className="flex items-center gap-2 text-xs text-emerald-700 bg-emerald-50 px-3 py-2 rounded">
            <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
            No issues identified.
          </div>
        )}
      </CardContent>
    </Card>
  );
}
