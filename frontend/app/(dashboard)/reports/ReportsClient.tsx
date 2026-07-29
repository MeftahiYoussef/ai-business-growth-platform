'use client';

import { FileText } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { AppCard } from '@/components/ui/AppCard';
import { Button } from '@/components/ui/Button';
import { useToast } from '@/components/feedback/ToastProvider';
import { generateReport } from '@/features/reports/api';
import type { Business, Report } from '@/types/api';

export function ReportsClient({ business, reports }: { business: Business | null; reports: Report[] }) {
  const router = useRouter();
  const { showToast } = useToast();
  async function generate() {
    if (!business) return;
    try {
      await generateReport(business._id);
      showToast('Report generated');
      router.refresh();
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Report failed', 'error');
    }
  }
  return (
    <div className="page-stack">
      <div className="row-between"><h2>Reports</h2><Button onClick={generate} disabled={!business}><FileText size={18} /> Generate report</Button></div>
      {reports.length === 0 ? <AppCard>No reports generated yet.</AppCard> : reports.map((report) => (
        <AppCard key={report._id}>
          <div className="row-between"><span><strong>{report.title}</strong><small>{report.reportType} · {report.status}</small></span><span className="chip">{report.summary.reach || 0} reach</span></div>
        </AppCard>
      ))}
    </div>
  );
}
