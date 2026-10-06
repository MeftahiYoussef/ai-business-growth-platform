import { apiFetch } from '@/lib/api/client';
import type {
  AIGeneration,
  ApiEnvelope,
  ContentDraft,
  ContentPlanGenerationResponse,
  ContentPlanItem,
  ContentPlanQueueResponse,
  ContentPlanStatusResponse
} from '@/types/api';

export function listGenerations() {
  return apiFetch<ApiEnvelope<AIGeneration[]>>('/ai/studio/history', { retry: true });
}

export function generateStudioContent(input: {
  businessId: string;
  objective: string;
  platform: string;
  audience?: string;
  tone?: string;
  language?: string;
  contentFormat?: string;
  productOrService?: string;
  additionalInstructions?: string;
}) {
  return apiFetch<ApiEnvelope<AIGeneration>>('/ai/studio/generate', { method: 'POST', body: input });
}

export function aiAction(id: string, action: string) {
  return apiFetch<ApiEnvelope<AIGeneration>>(`/ai/studio/${id}/action`, { method: 'POST', body: { action } });
}

export function generateWeeklyContentPlan(input: {
  businessId: string;
  platforms: string[];
  startDate: string;
  goal?: string;
  additionalInstructions?: string;
}) {
  return apiFetch<ContentPlanGenerationResponse>('/ai/content-plans/generate', {
    method: 'POST',
    body: {
      business_id: input.businessId,
      platforms: input.platforms,
      start_date: input.startDate,
      goal: input.goal || '',
      additional_instructions: input.additionalInstructions || ''
    }
  });
}

export function queueWeeklyContentPlan(input: {
  businessId: string;
  platforms: string[];
  startDate: string;
  goal?: string;
  additionalInstructions?: string;
  idempotencyKey?: string;
}) {
  return apiFetch<ContentPlanQueueResponse>('/ai/content-plans/queue', {
    method: 'POST',
    headers: input.idempotencyKey ? { 'Idempotency-Key': input.idempotencyKey } : undefined,
    body: {
      business_id: input.businessId,
      platforms: input.platforms,
      start_date: input.startDate,
      goal: input.goal || '',
      additional_instructions: input.additionalInstructions || ''
    }
  });
}

export function getContentPlanStatus(id: string) {
  return apiFetch<ContentPlanStatusResponse>(`/ai/content-plans/${id}/status`, { retry: true });
}

export function createDraftsFromPlan(id: string, itemDayNumbers: number[], editedItems: Record<string, Partial<ContentPlanItem>>) {
  return apiFetch<ApiEnvelope<ContentDraft[]>>(`/ai/content-plans/${id}/create-drafts`, {
    method: 'POST',
    body: {
      item_day_numbers: itemDayNumbers,
      edited_items: editedItems
    }
  });
}
