import { apiFetch } from '@/lib/api/client';
import type { ApiEnvelope, SocialConnection } from '@/types/api';

export function listConnections() {
  return apiFetch<ApiEnvelope<SocialConnection[]>>('/integrations/connections', { retry: true });
}

export function connectSandbox(businessId: string) {
  return apiFetch<ApiEnvelope<SocialConnection>>('/integrations/connections', {
    method: 'POST',
    body: { businessId, provider: 'sandbox' }
  });
}

export function syncConnection(id: string) {
  return apiFetch<ApiEnvelope<{ jobId: string; status: string }>>(`/integrations/connections/${id}/sync`, { method: 'POST' });
}
