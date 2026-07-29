import { apiFetch } from '@/lib/api/client';
import type { ApiEnvelope, Report } from '@/types/api';

export function listReports() {
  return apiFetch<ApiEnvelope<Report[]>>('/reports', { retry: true });
}

export function generateReport(businessId: string) {
  return apiFetch<ApiEnvelope<Report>>('/reports', {
    method: 'POST',
    body: { businessId, title: 'Executive performance summary', reportType: 'executive_summary' }
  });
}
