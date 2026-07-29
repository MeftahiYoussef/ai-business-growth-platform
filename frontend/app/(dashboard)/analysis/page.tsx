import { serverApi } from '@/lib/api/server';
import type { ApiEnvelope, Business, BusinessAnalysis } from '@/types/api';
import { AnalysisClient } from './AnalysisClient';

export default async function AnalysisPage() {
  const [analysis, business] = await Promise.all([
    serverApi<ApiEnvelope<BusinessAnalysis | null>>('/analysis').catch(() => ({ success: true, data: null })),
    serverApi<ApiEnvelope<Business | null>>('/business/me').catch(() => ({ success: true, data: null }))
  ]);
  return <AnalysisClient analysis={analysis.data} business={business.data} />;
}
