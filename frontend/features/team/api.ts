import { apiFetch } from '@/lib/api/client';
import type { ApiEnvelope, TeamMember } from '@/types/api';

export function listTeam() {
  return apiFetch<ApiEnvelope<TeamMember[]>>('/team', { retry: true });
}

export function inviteMember(input: { businessId: string; email: string; role: string }) {
  return apiFetch<ApiEnvelope<unknown>>('/team/invite', { method: 'POST', body: input });
}
