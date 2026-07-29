import { apiFetch } from '@/lib/api/client';
import type { AnalyticsSummary, ApiEnvelope } from '@/types/api';

export function getAnalyticsSummary() {
  return apiFetch<ApiEnvelope<AnalyticsSummary>>('/analytics/summary', { retry: true });
}
