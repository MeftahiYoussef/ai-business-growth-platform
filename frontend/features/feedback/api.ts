import { apiFetch } from '@/lib/api/client';

export function createFeedback(input: {
  businessId: string;
  contentIdeaId: string;
  liked: boolean;
  comment?: string;
}) {
  return apiFetch<{ success: boolean }>('/feedback', { method: 'POST', body: input });
}
