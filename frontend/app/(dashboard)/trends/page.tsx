import { serverApi } from '@/lib/api/server';
import type { ApiEnvelope, Business, PaginatedResponse, Trend } from '@/types/api';
import { TrendsClient } from './TrendsClient';

export default async function TrendsPage() {
  const [trends, business] = await Promise.all([
    serverApi<PaginatedResponse<Trend>>('/trends?limit=50').catch(() => empty<Trend>()),
    serverApi<ApiEnvelope<Business | null>>('/business/me').catch(() => ({ success: true, data: null }))
  ]);
  return <TrendsClient trends={trends.items} business={business.data} />;
}

function empty<T>(): PaginatedResponse<T> {
  return { success: true, items: [], pagination: { page: 1, limit: 50, total: 0, pages: 0 } };
}
