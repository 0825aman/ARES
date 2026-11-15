import { apiFetch } from './client';
import type { TokenSummaryResponse } from '@/lib/types/token';

export async function getTokenSummary(): Promise<TokenSummaryResponse> {
  return apiFetch<TokenSummaryResponse>('/api/v1/tokens/summary');
}

export async function triggerTokenBackfill(): Promise<{ status: string; runs_backfilled: number }> {
  return apiFetch<{ status: string; runs_backfilled: number }>('/api/v1/tokens/backfill', {
    method: 'POST',
  });
}
