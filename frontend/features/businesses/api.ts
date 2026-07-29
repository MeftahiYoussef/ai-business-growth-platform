import { apiFetch } from '@/lib/api/client';
import type { ApiEnvelope, Business } from '@/types/api';

export type BusinessInput = {
  name: string;
  industry: string;
  country: string;
  productOrService: string;
  targetAudience: string;
  goals: string[];
  knownCompetitors: string[];
  brandVoice?: string;
};

export function getMyBusiness() {
  return apiFetch<ApiEnvelope<Business | null>>('/business/me', { retry: true });
}

export function createBusiness(input: BusinessInput) {
  return apiFetch<ApiEnvelope<Business>>('/business', { method: 'POST', body: input });
}

export function updateBusiness(id: string, input: Partial<BusinessInput>) {
  return apiFetch<ApiEnvelope<Business>>(`/business/${id}`, { method: 'PUT', body: input });
}
