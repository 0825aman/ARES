'use client';

import { ShieldCheck, AlertTriangle, Lock, EyeOff, UserX, FileWarning, Sliders } from 'lucide-react';
import type { SafetyMetrics } from '@/lib/types/evaluation';

interface SafetyGuardrailsSectionProps {
  metrics: SafetyMetrics;
}

export function SafetyGuardrailsSection({ metrics }: SafetyGuardrailsSectionProps) {
  const safetyCards = [
    {
      title: 'Prompt Injection Resistance',
      value: (metrics.prompt_injection_resistance * 100).toFixed(1) + '%',
      badge: 'DEFENSE ACTIVE',
      badgeColor: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
      desc: 'Percentage of adversarial prompt injections and jailbreak personas safely neutralized.',
      isGood: true,
    },
    {
      title: 'PII Leakage Rate',
      value: (metrics.pii_leakage_rate * 100).toFixed(1) + '%',
      badge: '100% REDACTED',
      badgeColor: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
      desc: 'Frequency of unmasked emails, phone numbers, SSNs, or API keys in outputs (0% is ideal).',
      isGood: metrics.pii_leakage_rate === 0,
    },
    {
      title: 'Hallucination Rate',
      value: (metrics.hallucination_rate * 100).toFixed(1) + '%',
      badge: 'VERY LOW',
      badgeColor: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
      desc: 'Proportion of synthesized claims flagged as refuted or lacking evidentiary support.',
      isGood: metrics.hallucination_rate < 0.08,
    },
    {
      title: 'Toxicity Score',
      value: (metrics.toxicity_score * 100).toFixed(1) + '%',
      badge: 'SAFE',
      badgeColor: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
      desc: 'Detection probability of abusive, illegal, violent, or dangerous language.',
      isGood: metrics.toxicity_score < 0.05,
    },
    {
      title: 'Bias Score',
      value: (metrics.bias_score * 100).toFixed(1) + '%',
      badge: 'MINIMAL',
      badgeColor: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
      desc: 'Evaluation of demographic, gender, racial, or cultural stereotyping heuristics.',
      isGood: metrics.bias_score < 0.05,
    },
    {
      title: 'Policy Violation Rate',
      value: (metrics.policy_violation_rate * 100).toFixed(1) + '%',
      badge: 'COMPLIANT',
      badgeColor: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
      desc: 'Requests or generated responses triggering organizational and security policy alerts.',
      isGood: metrics.policy_violation_rate < 0.03,
    },
    {
      title: 'Guardrail Interventions',
      value: (metrics.guardrail_intervention_rate * 100).toFixed(1) + '%',
      badge: 'ACTIVE PROTECTION',
      badgeColor: 'text-sky-400 bg-sky-500/10 border-sky-500/20',
      desc: 'Frequency with which input/output guardrails intervened to redact, sanitize, or block.',
      isGood: true,
    },
  ];

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-base font-bold text-white flex items-center gap-2">
          <ShieldCheck className="h-5 w-5 text-purple-400" />
          4. Safety &amp; Guardrail Evaluation Metrics (ARES Multi-Layer Defense)
        </h3>
        <p className="text-xs text-slate-400">
          Measures prompt injection resistance, zero PII leakage, hallucination mitigation, toxicity, and policy compliance
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {safetyCards.map((card, idx) => (
          <div
            key={idx}
            className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 hover:border-purple-500/30 transition-all flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold font-mono text-slate-200">{card.title}</span>
                <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded border ${card.badgeColor}`}>
                  {card.badge}
                </span>
              </div>
              <div className="text-2xl font-bold font-mono text-white tracking-tight my-2">
                {card.value}
              </div>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed mt-1">{card.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
