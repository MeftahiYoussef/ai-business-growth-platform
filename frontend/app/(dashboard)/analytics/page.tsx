import { AppCard } from '@/components/ui/AppCard';
import { MetricCard } from '@/components/ui/MetricCard';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { serverApi } from '@/lib/api/server';
import type { AnalyticsSummary, ApiEnvelope } from '@/types/api';

export default async function AnalyticsPage() {
  const summary = await serverApi<ApiEnvelope<AnalyticsSummary>>('/analytics/summary').catch(() => ({ success: true, data: emptySummary() }));

  return (
    <div className="page-stack">
      <SectionTitle title="Analytics" />
      <div className="grid-responsive">
        <MetricCard label="Followers" value={String(summary.data.totalFollowers)} note="Connected accounts" kind="business" />
        <MetricCard label="Reach" value={String(summary.data.reach)} note="Current period" kind="trend" />
        <MetricCard label="Engagement rate" value={`${summary.data.engagementRate}%`} note={`${summary.data.engagement} interactions`} kind="ideas" />
        <MetricCard label="Published posts" value={String(summary.data.publishedPosts)} note={`${summary.data.scheduledPosts} scheduled`} kind="competitors" />
      </div>
      <AppCard>
        <div className="row-between"><strong>Platform performance</strong><span className="chip">Sandbox-ready</span></div>
        <div className="page-stack compact">
          {summary.data.byPlatform.length === 0 ? <p>No social account data yet. Connect a sandbox account from Integrations.</p> : summary.data.byPlatform.map((item) => (
            <div className="list-row" key={item.platform}>
              <span className="avatar">{item.platform.slice(0, 1).toUpperCase()}</span>
              <span><strong>{item.platform}</strong><small>{item.followers} followers</small></span>
              <span className="chip">{summary.data.engagementRate}% ER</span>
            </div>
          ))}
        </div>
      </AppCard>
    </div>
  );
}

function emptySummary(): AnalyticsSummary {
  return { totalFollowers: 0, reach: 0, impressions: 0, engagement: 0, engagementRate: 0, likes: 0, comments: 0, shares: 0, saves: 0, clicks: 0, videoViews: 0, publishedPosts: 0, scheduledPosts: 0, competitorsTracked: 0, byPlatform: [] };
}
