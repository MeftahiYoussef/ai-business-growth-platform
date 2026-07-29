import { serverApi } from '@/lib/api/server';
import type { ApiEnvelope, Business, Strategy } from '@/types/api';
import { StrategyClient } from './StrategyClient';

export default async function StrategyPage() {
  const [strategy, business] = await Promise.all([
    serverApi<ApiEnvelope<Strategy | null>>('/strategy').catch(() => ({ success: true, data: null })),
    serverApi<ApiEnvelope<Business | null>>('/business/me').catch(() => ({ success: true, data: null }))
  ]);
  return <StrategyClient strategy={strategy.data} business={business.data} />;
}
