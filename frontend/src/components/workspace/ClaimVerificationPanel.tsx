'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight, AlertTriangle, CheckCircle2, XCircle, Info, Zap } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import type { Claim, VerificationStatus } from '@/lib/types/run';

interface ClaimVerificationPanelProps {
  claims: Claim[];
}

function statusConfig(status: VerificationStatus): {
  label: string;
  className: string;
  icon: React.ReactNode;
} {
  switch (status) {
    case 'supported':
      return {
        label: 'Supported',
        className: 'bg-emerald-100 text-emerald-700',
        icon: <CheckCircle2 className="h-3.5 w-3.5" />,
      };
    case 'partially_supported':
      return {
        label: 'Partial',
        className: 'bg-amber-100 text-amber-700',
        icon: <Info className="h-3.5 w-3.5" />,
      };
    case 'contradicted':
      return {
        label: 'Contradicted',
        className: 'bg-red-100 text-red-700',
        icon: <XCircle className="h-3.5 w-3.5" />,
      };
    case 'insufficient_evidence':
      return {
        label: 'Insufficient',
        className: 'bg-slate-100 text-slate-600',
        icon: <AlertTriangle className="h-3.5 w-3.5" />,
      };
    case 'unverified':
      return {
        label: 'Unverified',
        className: 'bg-slate-100 text-slate-500',
        icon: <AlertTriangle className="h-3.5 w-3.5" />,
      };
    default:
      return {
        label: status,
        className: 'bg-slate-100 text-slate-500',
        icon: <Info className="h-3.5 w-3.5" />,
      };
  }
}

function ConfidenceMeter({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  const color =
    pct >= 75 ? 'bg-emerald-500' : pct >= 50 ? 'bg-amber-500' : 'bg-red-500';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-slate-100 rounded-full h-1.5 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-slate-500 shrink-0 w-8 text-right">{pct}%</span>
    </div>
  );
}

function ClaimRow({ claim }: { claim: Claim }) {
  const [expanded, setExpanded] = useState(false);
  const v = claim.verification;
  const cfg = v ? statusConfig(v.verification_status) : {
    label: 'Unverified',
    className: 'bg-slate-100 text-slate-500',
    icon: <AlertTriangle className="h-3.5 w-3.5" />,
  };

  return (
    <Card className="shadow-sm">
      <CardContent className="px-4 py-3">
        {/* Summary row */}
        <button
          onClick={() => setExpanded((x) => !x)}
          className="w-full text-left"
        >
          <div className="flex items-start gap-3">
            <span className={`inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded font-medium shrink-0 mt-0.5 ${cfg.className}`}>
              {cfg.icon}
              {cfg.label}
            </span>
            <p className="text-sm text-slate-800 leading-snug flex-1">{claim.claim_text}</p>
            <div className="flex items-center gap-1.5 shrink-0">
              {claim.is_high_impact && (
                <span title="High-impact claim">
                  <Zap className="h-3.5 w-3.5 text-amber-500" />
                </span>
              )}
              {expanded
                ? <ChevronDown className="h-4 w-4 text-slate-400" />
                : <ChevronRight className="h-4 w-4 text-slate-400" />
              }
            </div>
          </div>
        </button>

        {/* Expanded detail */}
        {expanded && v && (
          <div className="mt-3 pt-3 border-t border-slate-100 space-y-3">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge variant="secondary" className="text-xs">{claim.claim_type}</Badge>
              <span className="text-xs text-slate-400">§ {claim.originating_section}</span>
            </div>

            {v.reasoning_summary && (
              <div>
                <p className="text-xs font-medium text-slate-600 mb-1">Reasoning</p>
                <p className="text-xs text-slate-600 leading-relaxed">{v.reasoning_summary}</p>
              </div>
            )}

            <div>
              <p className="text-xs font-medium text-slate-600 mb-1">Confidence</p>
              <ConfidenceMeter confidence={v.confidence} />
            </div>

            {v.supporting_evidence_ids.length > 0 && (
              <p className="text-xs text-slate-500">
                {v.supporting_evidence_ids.length} supporting evidence item{v.supporting_evidence_ids.length !== 1 ? 's' : ''}
              </p>
            )}
            {v.contradicting_evidence_ids.length > 0 && (
              <p className="text-xs text-red-600">
                {v.contradicting_evidence_ids.length} contradicting evidence item{v.contradicting_evidence_ids.length !== 1 ? 's' : ''}
              </p>
            )}
            {v.evidence_limitations && (
              <p className="text-xs text-amber-700 bg-amber-50 px-2 py-1.5 rounded">
                {v.evidence_limitations}
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function ClaimVerificationPanel({ claims }: ClaimVerificationPanelProps) {
  if (claims.length === 0) {
    return (
      <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
        No claim verification data for this run.
        <p className="text-xs mt-1 text-slate-400">Claims are extracted and verified automatically after report generation.</p>
      </div>
    );
  }

  const supported = claims.filter((c) => c.verification?.verification_status === 'supported').length;
  const contradicted = claims.filter((c) => c.verification?.verification_status === 'contradicted').length;
  const partial = claims.filter((c) => c.verification?.verification_status === 'partially_supported').length;

  return (
    <div className="space-y-3">
      {/* Summary row */}
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-xs text-slate-500">
          {claims.length} claim{claims.length !== 1 ? 's' : ''}
        </span>
        {supported > 0 && (
          <span className="text-xs text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
            {supported} supported
          </span>
        )}
        {partial > 0 && (
          <span className="text-xs text-amber-700 bg-amber-50 px-2 py-0.5 rounded">
            {partial} partial
          </span>
        )}
        {contradicted > 0 && (
          <span className="text-xs text-red-700 bg-red-50 px-2 py-0.5 rounded">
            {contradicted} contradicted
          </span>
        )}
      </div>

      {/* Claim rows */}
      <div className="space-y-2">
        {claims.map((claim) => (
          <ClaimRow key={claim.id} claim={claim} />
        ))}
      </div>
    </div>
  );
}
