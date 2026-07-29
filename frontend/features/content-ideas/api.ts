import { apiFetch } from '@/lib/api/client';
import type { ApiEnvelope, ContentIdea, PaginatedResponse } from '@/types/api';
import type { ListQuery } from '@/features/competitors/api';

function qs(query: ListQuery = {}) {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== '') params.set(key, String(value));
  });
  const value = params.toString();
  return value ? `?${value}` : '';
}

export function listContentIdeas(query?: ListQuery) {
  return apiFetch<PaginatedResponse<ContentIdea>>(`/content-ideas${qs(query)}`, { retry: true });
}

export function generateContentIdeas(businessId: string) {
  return apiFetch<ApiEnvelope<ContentIdea[]>>('/content-ideas/generate', {
    method: 'POST',
    body: { businessId, count: 10 }
  });
}

export function saveContentIdea(id: string) {
  return apiFetch<ApiEnvelope<ContentIdea>>(`/content-ideas/${id}/save`, { method: 'PUT' });
}

export function deleteContentIdea(id: string) {
  return apiFetch<ApiEnvelope<{ id: string }>>(`/content-ideas/${id}`, { method: 'DELETE' });
}
