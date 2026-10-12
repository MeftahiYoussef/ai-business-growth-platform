import Link from 'next/link';
import { AutoGraphIcon, MetricCard } from '@/components/ui/MetricCard';
import { AppCard } from '@/components/ui/AppCard';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { serverApi } from '@/lib/api/server';
import type { ApiEnvelope, Business, Competitor, ContentIdea, PaginatedResponse, Trend } from '@/types/api';

export default async function DashboardPage() {
  const [business, competitors, trends, ideas] = await Promise.all([
    serverApi<ApiEnvelope<Business | null>>('/business/me').catch(() => ({ success: true, data: null })),
    serverApi<PaginatedResponse<Competitor>>('/competitors?limit=5').catch(() => empty<Competitor>()),
    serverApi<PaginatedResponse<Trend>>('/trends?limit=3').catch(() => empty<Trend>()),
    serverApi<PaginatedResponse<ContentIdea>>('/content-ideas?limit=1').catch(() => empty<ContentIdea>())
  ]);

  return (
    <div className="page-stack">
      <AppCard gradient>
        <div className="hero-card">
          <div>
            <h1>Good morning, {business.data?.name || 'Nova Studio'}</h1>
            <p>Today: create a reviewed content plan, turn it into drafts, and keep reports current.</p>
          </div>
          <AutoGraphIcon />
        </div>
      </AppCard>
      <div className="grid-responsive">
        <MetricCard label="Profile completeness" value={`${profileCompleteness(business.data)}%`} note="Business context fields" kind="business" />
        <MetricCard label="Trend records" value={String(trends.pagination.total)} note="Stored signals" kind="trend" />
        <MetricCard label="Competitors tracked" value={String(competitors.pagination.total)} note="Stored records" kind="competitors" />
        <MetricCard label="Generated ideas" value={String(ideas.pagination.total)} note="Saved in API" kind="ideas" />
      </div>
      <section>
        <SectionTitle title="Weekly trends" />
        <div className="page-stack compact">
          {trends.items.length === 0 ? <AppCard>No trends yet. Analyze trends from the Trends page.</AppCard> : trends.items.map((trend) => (
            <AppCard key={trend._id}>
              <div className="row-between">
                <strong>{trend.topic}</strong>
                <span className="chip">{trend.trendScore} score</span>
              </div>
            </AppCard>
          ))}
        </div>
      </section>
      <section>
        <SectionTitle title="Competitor records" />
        <div className="page-stack compact">
          {competitors.items.length === 0 ? <AppCard>No competitor records yet. Competitor intelligence is post-MVP.</AppCard> : competitors.items.map((competitor) => (
            <Link className="list-row" href={`/competitors/${competitor._id}`} key={competitor._id}>
              <span className="avatar">📣</span>
              <span><strong>{competitor.name}</strong><small>{competitor.platform}</small></span>
              <span>{competitor.engagementRate}%</span>
            </Link>
          ))}
        </div>
      </section>
      <section>
        <SectionTitle title="Quick actions" />
        <div className="action-row">
          <Link className="button button-primary" href="/studio">Open AI Studio</Link>
          <Link className="button button-secondary" href="/calendar">Review drafts</Link>
          <Link className="button button-secondary" href="/reports">Generate report</Link>
        </div>
      </section>
    </div>
  );
}

function empty<T>(): PaginatedResponse<T> {
  return { success: true, items: [], pagination: { page: 1, limit: 10, total: 0, pages: 0 } };
}

function profileCompleteness(business: Business | null) {
  if (!business) return 0;
  const fields = [
    business.name,
    business.industry,
    business.country,
    business.productOrService,
    business.targetAudience,
    business.brandVoice,
    business.postingFrequency || '',
    business.goals.length ? business.goals.join(',') : '',
    business.preferredPlatforms?.length ? business.preferredPlatforms.join(',') : ''
  ];
  return Math.round((fields.filter((field) => field.trim().length > 0).length / fields.length) * 100);
}
