import { apiFetch } from '@/lib/api/client';
import type { User } from '@/types/api';

export type AuthMeResponse = { success: boolean; data: User; hasBusiness: boolean };

export function login(input: { email: string; password: string }) {
  return apiFetch<{ success: boolean; data: User }>('/api/auth/login', {
    method: 'POST',
    body: input
  });
}

export function register(input: { fullName: string; email: string; password: string }) {
  return apiFetch<{ success: boolean; data: User }>('/api/auth/register', {
    method: 'POST',
    body: input
  });
}

export function logout() {
  return apiFetch<{ success: boolean }>('/api/auth/logout', { method: 'POST' });
}

export function me() {
  return apiFetch<AuthMeResponse>('/api/auth/me');
}
