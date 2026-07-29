import { serverApi } from '@/lib/api/server';
import type { ApiEnvelope, Business, Competitor, PaginatedResponse } from '@/types/api';
import { CompetitorsClient } from './CompetitorsClient';

export default async function CompetitorsPage({
  searchParams
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (typeof value === 'string') query.set(key, value);
  }
  const [competitors, business] = await Promise.all([
    serverApi<PaginatedResponse<Competitor>>(`/competitors?${query.toString()}`).catch(() => empty<Competitor>()),
    serverApi<ApiEnvelope<Business | null>>('/business/me').catch(() => ({ success: true, data: null }))
  ]);

  return <CompetitorsClient initial={competitors} business={business.data} />;
}

function empty<T>(): PaginatedResponse<T> {
  return { success: true, items: [], pagination: { page: 1, limit: 10, total: 0, pages: 0 } };
}
