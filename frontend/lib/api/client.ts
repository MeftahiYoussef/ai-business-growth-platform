import { ApiError } from './errors';

type RequestOptions = Omit<RequestInit, 'body'> & {
  body?: unknown;
  retry?: boolean;
};

export async function apiFetch<T>(path: string, options: RequestOptions = {}) {
  const run = async () => {
    const response = await fetch(path.startsWith('/api/') ? path : `/api/backend${path}`, {
      ...options,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {})
      }
    });

    if (response.status === 401) {
      await fetch('/api/auth/logout', { method: 'POST' });
      window.location.assign('/login');
      throw new ApiError('Your session expired. Please log in again.', 401);
    }

    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { message?: string; details?: unknown } | null;
      throw new ApiError(body?.message || 'API request failed', response.status, body?.details);
    }

    return (await response.json()) as T;
  };

  try {
    return await run();
  } catch (error) {
    if (options.retry && error instanceof TypeError) return run();
    throw error;
  }
}
