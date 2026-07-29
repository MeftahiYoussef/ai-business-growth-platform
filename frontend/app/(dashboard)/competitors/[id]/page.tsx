import { notFound } from 'next/navigation';
import { serverApi } from '@/lib/api/server';
import type { ApiEnvelope, Competitor, CompetitorPost, PaginatedResponse } from '@/types/api';
import { CompetitorDetailClient } from './CompetitorDetailClient';

export default async function CompetitorDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [competitor, posts] = await Promise.all([
    serverApi<ApiEnvelope<Competitor>>(`/competitors/${id}`).catch(() => null),
    serverApi<PaginatedResponse<CompetitorPost>>(`/competitors/${id}/posts?limit=20`).catch(() => empty<CompetitorPost>())
  ]);
  if (!competitor) notFound();
  return <CompetitorDetailClient competitor={competitor.data} posts={posts.items} />;
}

function empty<T>(): PaginatedResponse<T> {
  return { success: true, items: [], pagination: { page: 1, limit: 20, total: 0, pages: 0 } };
}
