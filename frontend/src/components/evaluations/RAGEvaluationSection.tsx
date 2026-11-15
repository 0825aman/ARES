'use client';

import { Database, Target, Check, Sparkles, HelpCircle, FileCheck2 } from 'lucide-react';
import type { RAGMetrics } from '@/lib/types/evaluation';

interface RAGEvaluationSectionProps {
  metrics: RAGMetrics;
}

export function RAGEvaluationSection({ metrics }: RAGEvaluationSectionProps) {
  const ragCards = [
    {
      title: 'Context Precision',
      score: metrics.context_precision,
      desc: 'Evaluates whether the retrieved project and web chunks are directly relevant to the user query.',
      status: 'OPTIMAL',
    },
    {
      title: 'Context Recall',
      score: metrics.context_recall,
      desc: 'Measures whether all factual ground-truth information required to answer is present in retrieved chunks.',
      status: 'HIGH COVERAGE',
    },
    {
      title: 'Faithfulness',
      score: metrics.faithfulness,
      desc: 'Checks whether every claim and finding in the answer is strictly inferable from the retrieved context.',
      status: 'GROUNDED',
    },
    {
      title: 'Answer Relevancy',
      score: metrics.answer_relevancy,
      desc: 'Measures how directly the synthesized research report addresses the specific research question.',
      status: 'HIGH ALIGNMENT',
    },
    {
      title: 'Context Relevancy',
      score: metrics.context_relevancy,
      desc: 'Measures the signal-to-noise ratio in retrieved context sentences, penalizing extraneous text.',
      status: 'LOW NOISE',
    },
    {
      title: 'Groundedness',
      score: metrics.groundedness,
      desc: 'Verifies verbatim and semantic claim-to-evidence linkage, backed by verifiable citations.',
      status: 'VERIFIED',
    },
  ];

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-base font-bold text-white flex items-center gap-2">
          <Database className="h-5 w-5 text-emerald-400" />
          2. RAG Evaluation Metrics (Retrieval-Augmented Generation)
        </h3>
        <p className="text-xs text-slate-400">
          Measures context retrieval quality, answer faithfulness, evidence grounding, and semantic hallucination resistance
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
        {ragCards.map((card, idx) => {
          const percent = (card.score * 100).toFixed(1);
          return (
            <div
              key={idx}
              className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 hover:border-emerald-500/30 transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold font-mono text-slate-200">{card.title}</span>
                  <span className="text-[9px] font-mono font-semibold px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    {card.status}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed mb-3">{card.desc}</p>
              </div>

              <div>
                <div className="flex items-baseline justify-between mb-1.5">
                  <span className="text-xs font-mono text-slate-400">Score</span>
                  <span className="text-xl font-bold font-mono text-white tracking-tight">{percent}%</span>
                </div>
                <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 rounded-full"
                    style={{ width: `${percent}%` }}
                  ></div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
