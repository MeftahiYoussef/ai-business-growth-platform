import { apiFetch } from '@/lib/api/client';
import type { ApiEnvelope, Strategy } from '@/types/api';

export function getStrategy() {
  return apiFetch<ApiEnvelope<Strategy | null>>('/strategy', { retry: true });
}

export function generateStrategy(businessId: string) {
  return apiFetch<ApiEnvelope<Strategy>>('/strategy/generate', {
    method: 'POST',
    body: { businessId }
  });
}
