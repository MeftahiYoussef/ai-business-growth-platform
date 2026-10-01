import { apiFetch } from '@/lib/api/client';
import type { ApiEnvelope, ContentDraft } from '@/types/api';

export function listDrafts() {
  return apiFetch<ApiEnvelope<ContentDraft[]>>('/planner/drafts', { retry: true });
}

export function getDraft(id: string) {
  return apiFetch<ApiEnvelope<ContentDraft>>(`/planner/drafts/${id}`, { retry: true });
}

export function createDraft(input: {
  businessId: string;
  title: string;
  caption: string;
  platform: string;
  contentType?: string;
  hashtags?: string[];
  cta?: string;
}) {
  return apiFetch<ApiEnvelope<ContentDraft>>('/planner/drafts', { method: 'POST', body: input });
}

export function workflowAction(id: string, action: string, body: Record<string, unknown> = {}) {
  return apiFetch<ApiEnvelope<ContentDraft>>(`/planner/drafts/${id}/${action}`, { method: 'POST', body });
}

export function updateDraft(id: string, input: Partial<{
  title: string;
  caption: string;
  cta: string;
  hashtags: string[];
  platform: string;
  contentType: string;
  objective: string;
}>) {
  return apiFetch<ApiEnvelope<ContentDraft>>(`/planner/drafts/${id}`, { method: 'PUT', body: input });
}
