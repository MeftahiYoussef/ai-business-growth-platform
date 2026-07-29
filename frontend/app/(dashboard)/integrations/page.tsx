import { serverApi } from '@/lib/api/server';
import type { ApiEnvelope, Business, SocialConnection } from '@/types/api';
import { IntegrationsClient } from './IntegrationsClient';

export default async function IntegrationsPage() {
  const [business, connections] = await Promise.all([
    serverApi<ApiEnvelope<Business | null>>('/business/me').catch(() => ({ success: true, data: null })),
    serverApi<ApiEnvelope<SocialConnection[]>>('/integrations/connections').catch(() => ({ success: true, data: [] }))
  ]);
  return <IntegrationsClient business={business.data} connections={connections.data} />;
}
