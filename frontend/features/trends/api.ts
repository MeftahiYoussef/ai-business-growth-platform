import { apiFetch } from '@/lib/api/client';
import type { ApiEnvelope, PaginatedResponse, Trend } from '@/types/api';
import type { ListQuery } from '@/features/competitors/api';

function qs(query: ListQuery = {}) {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== '') params.set(key, String(value));
  });
  const value = params.toString();
  return value ? `?${value}` : '';
}

export function listTrends(query?: ListQuery) {
  return apiFetch<PaginatedResponse<Trend>>(`/trends${qs(query)}`, { retry: true });
}

export function analyzeTrends(businessId: string) {
  return apiFetch<ApiEnvelope<Trend[]>>('/trends/analyze', {
    method: 'POST',
    body: { businessId }
  });
}
