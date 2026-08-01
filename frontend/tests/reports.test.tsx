import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ToastProvider } from '@/components/feedback/ToastProvider';
import { ReportsClient } from '@/app/(dashboard)/reports/ReportsClient';
import * as reportsApi from '@/features/reports/api';
import type { Business, Report, ReportJobStatusResponse } from '@/types/api';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() })
}));

const business: Business = {
  _id: 'business-1',
  ownerId: 'user-1',
  name: 'Nova Studio',
  industry: 'SaaS',
  country: 'US',
  productOrService: 'AI launch kits',
  targetAudience: 'Founders',
  goals: ['engagement'],
  knownCompetitors: ['GrowthPilot'],
  brandVoice: 'Sharp'
};

function report(): Report {
  return {
    _id: 'report-1',
    businessId: 'business-1',
    jobId: 'job-1',
    title: 'Business performance report',
    reportType: 'business_performance',
    status: 'ready',
    summary: { draft_total: 2, approved_total: 1 },
    structuredContent: {
      report_type: 'business_performance',
      period: { start: '2026-07-01', end: '2026-07-31' },
      business_overview: {
        name: 'Nova Studio',
        industry: 'SaaS',
        country: 'US',
        product_or_service: 'AI launch kits',
        target_audience: 'Founders',
        goals: ['engagement']
      },
      metrics: { draft_total: 2, approved_total: 1, scheduled_total: 0 },
      platform_breakdown: [],
      content_type_breakdown: [],
      objective_breakdown: [],
      recent_trends: [],
      competitor_observations: [],
      highlights: ['Draft pipeline is active.'],
      risks: ['No scheduled content is recorded.'],
      recommendations: [{ text: 'Review drafts before scheduling.', requires_human_review: true }],
      data_limitations: ['Only stored application data is included.']
    }
  };
}

function completedStatus(): ReportJobStatusResponse {
  return {
    success: true,
    job_id: 'job-1',
    status: 'completed',
    progress: 100,
    progress_label: 'completed',
    attempt_count: 1,
    report_id: 'report-1',
    result_available: true,
    error: null,
    report: report(),
    created_at: '2026-07-31T00:00:00Z'
  };
}

function renderReports(existingReports: Report[] = []) {
  return render(
    <ToastProvider>
      <ReportsClient business={business} reports={existingReports} />
    </ToastProvider>
  );
}

describe('reports client', () => {
  afterEach(() => {
    delete process.env.NEXT_PUBLIC_ASYNC_REPORTS_ENABLED;
    window.sessionStorage.clear();
    vi.restoreAllMocks();
  });

  it('uses synchronous report generation by default', async () => {
    vi.spyOn(reportsApi, 'generateReport').mockResolvedValue({ success: true, data: report() });
    vi.spyOn(reportsApi, 'queueBusinessPerformanceReport').mockResolvedValue({ success: true, job_id: 'job-1', status: 'queued', status_url: '' });
    renderReports();
    await userEvent.click(screen.getByRole('button', { name: /generate business report/i }));
    await waitFor(() => expect(reportsApi.generateReport).toHaveBeenCalledWith('business-1'));
    expect(reportsApi.queueBusinessPerformanceReport).not.toHaveBeenCalled();
  });

  it('queues and polls an async report until completion', async () => {
    process.env.NEXT_PUBLIC_ASYNC_REPORTS_ENABLED = 'true';
    vi.spyOn(reportsApi, 'queueBusinessPerformanceReport').mockResolvedValue({ success: true, job_id: 'job-1', status: 'queued', status_url: '/api/reports/jobs/job-1/status/' });
    vi.spyOn(reportsApi, 'getReportJobStatus').mockResolvedValue(completedStatus());
    renderReports();
    await userEvent.click(screen.getByRole('button', { name: /generate business report/i }));
    await waitFor(() => expect(reportsApi.queueBusinessPerformanceReport).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByText(/draft pipeline is active/i)).toBeInTheDocument());
    expect(reportsApi.getReportJobStatus).toHaveBeenCalledWith('job-1');
    expect(screen.getByText(/human review required: true/i)).toBeInTheDocument();
  });

  it('recovers an active report job from session storage', async () => {
    process.env.NEXT_PUBLIC_ASYNC_REPORTS_ENABLED = 'true';
    window.sessionStorage.setItem('activeBusinessReportJobId', 'job-1');
    vi.spyOn(reportsApi, 'getReportJobStatus').mockResolvedValue(completedStatus());
    renderReports();
    await waitFor(() => expect(reportsApi.getReportJobStatus).toHaveBeenCalledWith('job-1'));
    await waitFor(() => expect(screen.getByText(/business performance report/i)).toBeInTheDocument());
  });

  it('clears loading after async report failure', async () => {
    process.env.NEXT_PUBLIC_ASYNC_REPORTS_ENABLED = 'true';
    vi.spyOn(reportsApi, 'queueBusinessPerformanceReport').mockRejectedValue(new Error('Report queue unavailable'));
    renderReports();
    await userEvent.click(screen.getByRole('button', { name: /generate business report/i }));
    await waitFor(() => expect(screen.getByText(/report queue unavailable/i)).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /generate business report/i })).not.toBeDisabled();
  });
});
