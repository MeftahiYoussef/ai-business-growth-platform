'use client';

import useSWR, { mutate } from 'swr';
import { apiFetch } from '@/lib/api/client';

export function useApi<T>(path: string | null) {
  return useSWR<T>(path, (url: string) => apiFetch<T>(url, { retry: true }), {
    revalidateOnFocus: false
  });
}

export function refreshApi(path: string) {
  return mutate(path);
}
