import { apiFetch } from '@/lib/api/client';
import type { ApiEnvelope, BusinessAnalysis } from '@/types/api';

export function getAnalysis() {
  return apiFetch<ApiEnvelope<BusinessAnalysis | null>>('/analysis', { retry: true });
}

export function generateAnalysis(businessId: string) {
  return apiFetch<ApiEnvelope<BusinessAnalysis>>('/analysis/generate', {
    method: 'POST',
    body: { businessId }
  });
}
