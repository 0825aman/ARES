'use client';

import { CheckCircle2, BarChart2, BookOpen, Layers } from 'lucide-react';
import type { AccuracyMetrics } from '@/lib/types/evaluation';

interface AccuracyQualitySectionProps {
  metrics: AccuracyMetrics;
}

export function AccuracyQualitySection({ metrics }: AccuracyQualitySectionProps) {
  const coreMetrics = [
    { label: 'Accuracy', value: (metrics.accuracy * 100).toFixed(1), desc: 'Correctness of generated factual predictions' },
    { label: 'Precision', value: (metrics.precision * 100).toFixed(1), desc: 'Generated relevant results that are correct' },
    { label: 'Recall', value: (metrics.recall * 100).toFixed(1), desc: 'Relevant reference items successfully retrieved' },
    { label: 'F1 Score', value: (metrics.f1_score * 100).toFixed(1), desc: 'Harmonic mean of precision and recall' },
    { label: 'Exact Match (EM)', value: (metrics.exact_match * 100).toFixed(1), desc: 'Exact string alignment with ground truth' },
    { label: 'Semantic Similarity', value: (metrics.semantic_similarity * 100).toFixed(1), desc: 'Cosine semantic vector alignment' },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-sky-400" />
            1. Accuracy &amp; Quality Metrics
          </h3>
          <p className="text-xs text-slate-400">
            Evaluates factual accuracy, token precision/recall balance, exact match frequency, and lexical overlap
          </p>
        </div>
      </div>

      {/* Grid of Core Metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {coreMetrics.map((item, idx) => (
          <div
            key={idx}
            className="p-3.5 rounded-lg bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition-colors"
          >
            <span className="text-[11px] font-mono text-slate-400 font-semibold block uppercase truncate">
              {item.label}
            </span>
            <div className="flex items-baseline gap-1 mt-1">
              <span className="text-2xl font-bold font-mono text-white tracking-tight">{item.value}</span>
              <span className="text-xs text-slate-500 font-mono">%</span>
            </div>
            <p className="text-[10px] text-slate-500 mt-2 line-clamp-2 leading-relaxed">{item.desc}</p>
          </div>
        ))}
      </div>

      {/* ROUGE & BLEU Comparative Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* ROUGE Overlap */}
        <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <BookOpen className="h-4 w-4 text-emerald-400" />
              <h4 className="text-sm font-bold text-white font-mono">ROUGE Overlap Scores</h4>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              RECALL-FOCUSED
            </span>
          </div>
          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-xs font-mono mb-1">
                <span className="text-slate-300">ROUGE-1 (Unigram Overlap)</span>
                <span className="text-emerald-400 font-bold">{(metrics.rouge_1 * 100).toFixed(1)}%</span>
              </div>
              <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 rounded-full transition-all"
                  style={{ width: `${metrics.rouge_1 * 100}%` }}
                ></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs font-mono mb-1">
                <span className="text-slate-300">ROUGE-2 (Bigram Phrase Overlap)</span>
                <span className="text-emerald-400 font-bold">{(metrics.rouge_2 * 100).toFixed(1)}%</span>
              </div>
              <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 rounded-full transition-all"
                  style={{ width: `${metrics.rouge_2 * 100}%` }}
                ></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs font-mono mb-1">
                <span className="text-slate-300">ROUGE-L (Longest Common Subsequence)</span>
                <span className="text-emerald-400 font-bold">{(metrics.rouge_l * 100).toFixed(1)}%</span>
              </div>
              <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 rounded-full transition-all"
                  style={{ width: `${metrics.rouge_l * 100}%` }}
                ></div>
              </div>
            </div>
          </div>
        </div>

        {/* BLEU Precision */}
        <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Layers className="h-4 w-4 text-cyan-400" />
              <h4 className="text-sm font-bold text-white font-mono">BLEU N-Gram Precision</h4>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              PRECISION-FOCUSED
            </span>
          </div>
          <div className="grid grid-cols-2 gap-3 pt-1">
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80">
              <span className="text-[10px] font-mono text-slate-400">BLEU-1 (Unigrams)</span>
              <div className="text-xl font-bold font-mono text-cyan-300 mt-1">
                {(metrics.bleu_1 * 100).toFixed(1)}%
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80">
              <span className="text-[10px] font-mono text-slate-400">BLEU-2 (Bigrams)</span>
              <div className="text-xl font-bold font-mono text-cyan-300 mt-1">
                {(metrics.bleu_2 * 100).toFixed(1)}%
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80">
              <span className="text-[10px] font-mono text-slate-400">BLEU-3 (Trigrams)</span>
              <div className="text-xl font-bold font-mono text-cyan-300 mt-1">
                {(metrics.bleu_3 * 100).toFixed(1)}%
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80">
              <span className="text-[10px] font-mono text-slate-400">BLEU-4 (4-Grams Cumulative)</span>
              <div className="text-xl font-bold font-mono text-cyan-300 mt-1">
                {(metrics.bleu_4 * 100).toFixed(1)}%
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
