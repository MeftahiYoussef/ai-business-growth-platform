import { serverApi } from '@/lib/api/server';
import type { AIGeneration, ApiEnvelope, Business } from '@/types/api';
import { StudioClient } from './StudioClient';

export default async function StudioPage() {
  const [business, generations] = await Promise.all([
    serverApi<ApiEnvelope<Business | null>>('/business/me').catch(() => ({ success: true, data: null })),
    serverApi<ApiEnvelope<AIGeneration[]>>('/ai/studio/history').catch(() => ({ success: true, data: [] }))
  ]);
  return <StudioClient business={business.data} generations={generations.data} />;
}
