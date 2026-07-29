import { serverApi } from '@/lib/api/server';
import type { ApiEnvelope, Business, ContentDraft } from '@/types/api';
import { CalendarClient } from './CalendarClient';

export default async function CalendarPage() {
  const [business, drafts] = await Promise.all([
    serverApi<ApiEnvelope<Business | null>>('/business/me').catch(() => ({ success: true, data: null })),
    serverApi<ApiEnvelope<ContentDraft[]>>('/planner/drafts').catch(() => ({ success: true, data: [] }))
  ]);
  return <CalendarClient business={business.data} drafts={drafts.data} />;
}
