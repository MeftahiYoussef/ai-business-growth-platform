import { getToken } from '@/lib/auth/cookies';
import { backendApiUrl } from './config';
import { parseApiError } from './errors';

export async function serverApi<T>(path: string, init: RequestInit = {}) {
  const token = await getToken();
  const headers = new Headers(init.headers);
  headers.set('Content-Type', headers.get('Content-Type') || 'application/json');
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const response = await fetch(backendApiUrl(path), {
    ...init,
    headers,
    cache: 'no-store'
  });

  if (!response.ok) {
    throw await parseApiError(response);
  }

  return (await response.json()) as T;
}
