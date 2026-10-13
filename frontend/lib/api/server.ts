import { getToken } from '@/lib/auth/cookies';
import { backendApiUrl } from './config';
import { parseApiError } from './errors';

export async function serverApi<T>(path: string, init: RequestInit = {}) {
  const token = await getToken();
  const headers = new Headers(init.headers);
  headers.set('Content-Type', headers.get('Content-Type') || 'application/json');
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const controller = new AbortController();
  const timeoutMs = Number(process.env.BACKEND_FETCH_TIMEOUT_MS || '20000');
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  let response: Response;
  try {
    response = await fetch(backendApiUrl(path), {
      ...init,
      headers,
      cache: 'no-store',
      signal: init.signal ?? controller.signal
    });
  } finally {
    clearTimeout(timeout);
  }

  if (!response.ok) {
    throw await parseApiError(response);
  }

  return (await response.json()) as T;
}
