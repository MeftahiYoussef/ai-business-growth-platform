'use client';

import { Sparkles } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/Button';
import { AppCard } from '@/components/ui/AppCard';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { EmptyState } from '@/components/ui/EmptyState';
import { useToast } from '@/components/feedback/ToastProvider';
import { analyzeTrends } from '@/features/trends/api';
import type { Business, Trend } from '@/types/api';

export function TrendsClient({ trends, business }: { trends: Trend[]; business: Business | null }) {
  const router = useRouter();
  const { showToast } = useToast();

  async function analyze() {
    if (!business) return;
    try {
      await analyzeTrends(business._id);
      showToast('Trends analyzed');
      router.refresh();
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Could not analyze trends', 'error');
    }
  }

  return (
    <div className="page-stack">
      <SectionTitle title="Trends" action={<Button onClick={analyze} disabled={!business}><Sparkles size={18} /> Analyze</Button>} />
      {trends.length === 0 ? (
        <EmptyState title="No trends yet" description="Analyze your competitor signals to generate trend intelligence." />
      ) : trends.map((trend) => (
        <AppCard key={trend._id}>
          <div className="row-between">
            <h2 style={{ margin: 0 }}>{trend.topic}</h2>
            <div className="action-row">
              <span className="chip">{trend.momentumLabel}</span>
              <span className="chip">{trend.trendScore}</span>
            </div>
          </div>
          <div className="action-row" style={{ marginTop: 14 }}>
            {trend.hashtags.map((tag) => <span className="chip" key={tag}>{tag}</span>)}
          </div>
          <h3>Viral hooks</h3>
          {trend.hooks.map((hook) => <p key={hook}>• {hook}</p>)}
          <p>Formats: {trend.format}</p>
        </AppCard>
      ))}
    </div>
  );
}
