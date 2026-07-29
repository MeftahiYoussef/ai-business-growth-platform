import { apiFetch } from '@/lib/api/client';
import type { ApiEnvelope, Competitor, CompetitorPost, PaginatedResponse } from '@/types/api';

export type ListQuery = {
  page?: number;
  limit?: number;
  search?: string;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
};

function qs(query: ListQuery = {}) {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== '') params.set(key, String(value));
  });
  const value = params.toString();
  return value ? `?${value}` : '';
}

export function listCompetitors(query?: ListQuery) {
  return apiFetch<PaginatedResponse<Competitor>>(`/competitors${qs(query)}`, { retry: true });
}

export function getCompetitor(id: string) {
  return apiFetch<ApiEnvelope<Competitor>>(`/competitors/${id}`, { retry: true });
}

export function createCompetitor(input: {
  businessId: string;
  name: string;
  platform: string;
  profileUrl?: string;
}) {
  return apiFetch<ApiEnvelope<Competitor>>('/competitors', { method: 'POST', body: input });
}

export function deleteCompetitor(id: string) {
  return apiFetch<ApiEnvelope<{ id: string }>>(`/competitors/${id}`, { method: 'DELETE' });
}

export function listCompetitorPosts(id: string, query?: ListQuery) {
  return apiFetch<PaginatedResponse<CompetitorPost>>(`/competitors/${id}/posts${qs(query)}`, { retry: true });
}

export function generateCompetitorPosts(id: string) {
  return apiFetch<ApiEnvelope<CompetitorPost[]>>(`/competitors/${id}/posts/mock-generate`, {
    method: 'POST',
    body: { count: 6 }
  });
}
