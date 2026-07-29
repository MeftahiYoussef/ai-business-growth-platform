import { serverApi } from '@/lib/api/server';
import type { ApiEnvelope, Business, ContentIdea, PaginatedResponse } from '@/types/api';
import { ContentIdeasClient } from './ContentIdeasClient';

export default async function GeneratePage() {
  const [ideas, business] = await Promise.all([
    serverApi<PaginatedResponse<ContentIdea>>('/content-ideas?limit=50').catch(() => empty<ContentIdea>()),
    serverApi<ApiEnvelope<Business | null>>('/business/me').catch(() => ({ success: true, data: null }))
  ]);
  return <ContentIdeasClient ideas={ideas.items} business={business.data} />;
}

function empty<T>(): PaginatedResponse<T> {
  return { success: true, items: [], pagination: { page: 1, limit: 50, total: 0, pages: 0 } };
}
