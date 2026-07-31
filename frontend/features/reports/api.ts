import { apiFetch } from '@/lib/api/client';
import type { ApiEnvelope, Report, ReportJobStatusResponse, ReportQueueResponse } from '@/types/api';

export function listReports() {
  return apiFetch<ApiEnvelope<Report[]>>('/reports', { retry: true });
}

export function generateReport(businessId: string) {
  return apiFetch<ApiEnvelope<Report>>('/reports', {
    method: 'POST',
    body: { businessId, title: 'Executive performance summary', reportType: 'executive_summary' }
  });
}

export function queueBusinessPerformanceReport(input: {
  businessId: string;
  periodStart: string;
  periodEnd: string;
  includeAiRecommendations: boolean;
  idempotencyKey?: string;
}) {
  return apiFetch<ReportQueueResponse>('/reports/queue/', {
    method: 'POST',
    headers: input.idempotencyKey ? { 'Idempotency-Key': input.idempotencyKey } : undefined,
    body: {
      business_id: input.businessId,
      report_type: 'business_performance',
      period_start: input.periodStart,
      period_end: input.periodEnd,
      include_ai_recommendations: input.includeAiRecommendations
    }
  });
}

export function getReportJobStatus(jobId: string) {
  return apiFetch<ReportJobStatusResponse>(`/reports/jobs/${jobId}/status/`, { retry: true });
}

export function getReport(reportId: string) {
  return apiFetch<ApiEnvelope<Report>>(`/reports/${reportId}/`, { retry: true });
}

export function reportExportUrl(reportId: string, format: 'json' | 'csv') {
  return `/api/backend/reports/${reportId}/export.${format}/`;
}
