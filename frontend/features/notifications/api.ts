import { apiFetch } from '@/lib/api/client';
import type { ApiEnvelope, AppNotification } from '@/types/api';

export function listNotifications() {
  return apiFetch<ApiEnvelope<AppNotification[]>>('/notifications', { retry: true });
}

export function markRead(id: string) {
  return apiFetch<ApiEnvelope<AppNotification>>(`/notifications/${id}/read`, { method: 'POST' });
}
