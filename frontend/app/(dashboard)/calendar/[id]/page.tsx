import { notFound } from 'next/navigation';
import { serverApi } from '@/lib/api/server';
import type { ApiEnvelope, ContentDraft } from '@/types/api';
import { DraftEditClient } from './DraftEditClient';

export default async function DraftEditPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const response = await serverApi<ApiEnvelope<ContentDraft>>(`/planner/drafts/${id}`).catch(() => null);
  if (!response?.data) notFound();
  return <DraftEditClient draft={response.data} />;
}
