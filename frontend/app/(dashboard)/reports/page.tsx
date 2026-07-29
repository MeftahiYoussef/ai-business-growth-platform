import { serverApi } from '@/lib/api/server';
import type { ApiEnvelope, Business, Report } from '@/types/api';
import { ReportsClient } from './ReportsClient';

export default async function ReportsPage() {
  const [business, reports] = await Promise.all([
    serverApi<ApiEnvelope<Business | null>>('/business/me').catch(() => ({ success: true, data: null })),
    serverApi<ApiEnvelope<Report[]>>('/reports').catch(() => ({ success: true, data: [] }))
  ]);
  return <ReportsClient business={business.data} reports={reports.data} />;
}
