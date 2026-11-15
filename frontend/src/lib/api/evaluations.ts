import { apiFetch } from './client';
import type { EvaluationDashboardResponse } from '@/lib/types/evaluation';

export async function getEvaluationDashboard(): Promise<EvaluationDashboardResponse> {
  return apiFetch<EvaluationDashboardResponse>('/api/v1/evaluations/dashboard');
}

export async function runEvaluationBenchmark(): Promise<{
  status: string;
  message: string;
  results: EvaluationDashboardResponse;
}> {
  return apiFetch<{
    status: string;
    message: string;
    results: EvaluationDashboardResponse;
  }>('/api/v1/evaluations/run-benchmark', {
    method: 'POST',
  });
}

export async function evaluateCustomText(data: {
  query?: string;
  generated_text: string;
  reference_text: string;
  retrieved_contexts?: string[];
}): Promise<any> {
  return apiFetch<any>('/api/v1/evaluations/evaluate-custom', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}
