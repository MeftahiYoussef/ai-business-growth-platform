import { apiFetch } from '@/lib/api/client';
import type { ApiEnvelope, ContentDraft } from '@/types/api';

export function listDrafts() {
  return apiFetch<ApiEnvelope<ContentDraft[]>>('/planner/drafts', { retry: true });
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
