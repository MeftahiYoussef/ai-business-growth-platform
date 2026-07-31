'use client';

import { Download, FileText } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';
import { AppCard } from '@/components/ui/AppCard';
import { Button } from '@/components/ui/Button';
import { useToast } from '@/components/feedback/ToastProvider';
import { generateReport, getReportJobStatus, queueBusinessPerformanceReport, reportExportUrl } from '@/features/reports/api';
import type { Business, Report, ReportJobStatusResponse } from '@/types/api';

const asyncReportsEnabled = () => process.env.NEXT_PUBLIC_ASYNC_REPORTS_ENABLED === 'true';
const activeReportJobStorageKey = 'activeBusinessReportJobId';

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function daysAgoIso(days: number) {
  return new Date(Date.now() - days * 86400000).toISOString().slice(0, 10);
}

function statusLabel(status: string | null) {
  if (status === 'queued') return 'Queued...';
  if (status === 'running') return 'Generating report...';
  if (status === 'retrying') return 'Retrying...';
  return 'Generate business report';
}

function metricLabel(key: string) {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
}

function ReportDetails({ report }: { report: Report }) {
  const structured = report.structuredContent;
  const metrics = structured?.metrics || report.summary || {};
  return (
    <div className="page-stack compact">
      <div className="row-between">
        <span>
          <strong>{report.title}</strong>
          <small>{report.reportType} · {report.status}</small>
        </span>
        <span className="chip">{report.generatedAt || report.createdAt || 'Pending'}</span>
      </div>
      <div className="form-grid">
        {Object.entries(metrics).slice(0, 8).map(([key, value]) => (
          <div key={key} className="metric-card">
            <small>{metricLabel(key)}</small>
            <strong>{String(value ?? 0)}</strong>
          </div>
        ))}
      </div>
      {structured ? (
        <>
          <div className="form-grid">
            <div>
              <strong>Computed highlights</strong>
              <ul>{structured.highlights.map((item) => <li key={item}>{item}</li>)}</ul>
            </div>
            <div>
              <strong>Risks</strong>
              <ul>{structured.risks.map((item) => <li key={item}>{item}</li>)}</ul>
            </div>
          </div>
          <div>
            <strong>Recommendations</strong>
            <ul>
              {structured.recommendations.map((item) => (
                <li key={item.text}>{item.text} <small>Human review required: {String(item.requires_human_review)}</small></li>
              ))}
            </ul>
          </div>
          <div>
            <strong>Data limitations</strong>
            <ul>{structured.data_limitations.map((item) => <li key={item}>{item}</li>)}</ul>
          </div>
          <div className="action-row">
            <a className="button button-secondary" href={reportExportUrl(report._id, 'json')}><Download size={16} /> JSON</a>
            <a className="button button-secondary" href={reportExportUrl(report._id, 'csv')}><Download size={16} /> CSV</a>
          </div>
        </>
      ) : null}
    </div>
  );
}

export function ReportsClient({ business, reports }: { business: Business | null; reports: Report[] }) {
  const router = useRouter();
  const { showToast } = useToast();
  const [periodStart, setPeriodStart] = useState(daysAgoIso(30));
  const [periodEnd, setPeriodEnd] = useState(todayIso());
  const [includeAiRecommendations, setIncludeAiRecommendations] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [loadingReport, setLoadingReport] = useState(false);
  const [currentReport, setCurrentReport] = useState<Report | null>(reports[0] || null);
  const useAsyncReports = asyncReportsEnabled();
  const history = useMemo(() => reports.filter((report) => report._id !== currentReport?._id), [reports, currentReport]);

  useEffect(() => {
    if (!useAsyncReports) return;
    const existingId = window.sessionStorage.getItem(activeReportJobStorageKey);
    if (existingId) {
      setActiveJobId(existingId);
      setLoadingReport(true);
    }
  }, [useAsyncReports]);

  useEffect(() => {
    if (!useAsyncReports || !activeJobId || !loadingReport) return;
    const jobId = activeJobId;
    let cancelled = false;
    let timeoutId: ReturnType<typeof setTimeout> | undefined;

    async function poll() {
      try {
        const status: ReportJobStatusResponse = await getReportJobStatus(jobId);
        if (cancelled) return;
        setJobStatus(status.status);
        setProgress(status.progress);
        if (status.status === 'completed' && status.result_available && status.report) {
          setCurrentReport(status.report);
          window.sessionStorage.removeItem(activeReportJobStorageKey);
          setActiveJobId(null);
          setLoadingReport(false);
          showToast('Business report generated');
          router.refresh();
          return;
        }
        if (status.status === 'failed' || status.status === 'cancelled') {
          window.sessionStorage.removeItem(activeReportJobStorageKey);
          setActiveJobId(null);
          setLoadingReport(false);
          showToast(status.error?.message || 'Report generation failed', 'error');
          return;
        }
        timeoutId = setTimeout(poll, 3000);
      } catch (error) {
        if (cancelled) return;
        window.sessionStorage.removeItem(activeReportJobStorageKey);
        setActiveJobId(null);
        setLoadingReport(false);
        showToast(error instanceof Error ? error.message : 'Could not check report status', 'error');
      }
    }

    poll();
    return () => {
      cancelled = true;
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [activeJobId, loadingReport, router, showToast, useAsyncReports]);

  async function generate() {
    if (!business) return;
    if (periodStart > periodEnd) {
      showToast('Choose an end date on or after the start date', 'error');
      return;
    }
    setLoadingReport(true);
    let queuedAsync = false;
    try {
      if (useAsyncReports) {
        const idempotencyKey = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`;
        const queued = await queueBusinessPerformanceReport({
          businessId: business._id,
          periodStart,
          periodEnd,
          includeAiRecommendations,
          idempotencyKey
        });
        setActiveJobId(queued.job_id);
        setJobStatus(queued.status);
        setProgress(0);
        window.sessionStorage.setItem(activeReportJobStorageKey, queued.job_id);
        queuedAsync = true;
        showToast('Report queued');
        return;
      }
      const response = await generateReport(business._id);
      setCurrentReport(response.data);
      showToast('Report generated');
      router.refresh();
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Report failed', 'error');
    } finally {
      if (!useAsyncReports || !queuedAsync) setLoadingReport(false);
    }
  }

  return (
    <div className="page-stack">
      <div className="row-between">
        <h2>Reports</h2>
        <Button onClick={generate} disabled={!business || loadingReport}><FileText size={18} /> {loadingReport ? statusLabel(jobStatus) : 'Generate business report'}</Button>
      </div>
      {useAsyncReports ? (
        <AppCard>
          <div className="page-stack compact">
            <div className="form-grid">
              <label className="field"><span>Business</span><input value={business?.name || 'No business'} readOnly /></label>
              <label className="field"><span>Period start</span><input type="date" value={periodStart} onChange={(event) => setPeriodStart(event.target.value)} /></label>
              <label className="field"><span>Period end</span><input type="date" value={periodEnd} onChange={(event) => setPeriodEnd(event.target.value)} /></label>
            </div>
            <label className="chip">
              <input type="checkbox" checked={includeAiRecommendations} onChange={(event) => setIncludeAiRecommendations(event.target.checked)} /> Include AI recommendations
            </label>
            {loadingReport ? <span className="chip">{jobStatus || 'queued'} · {progress}%</span> : null}
          </div>
        </AppCard>
      ) : null}
      {currentReport ? <AppCard><ReportDetails report={currentReport} /></AppCard> : <AppCard>No reports generated yet.</AppCard>}
      {history.length ? (
        <AppCard>
          <div className="page-stack compact">
            <strong>Report history</strong>
            {history.map((report) => (
              <button className="button button-secondary" key={report._id} type="button" onClick={() => setCurrentReport(report)}>
                {report.title} · {report.status}
              </button>
            ))}
          </div>
        </AppCard>
      ) : null}
    </div>
  );
}
