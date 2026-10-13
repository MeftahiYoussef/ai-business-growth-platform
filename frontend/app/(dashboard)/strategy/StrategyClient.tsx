'use client';

import { AppCard } from '@/components/ui/AppCard';
import { SectionTitle } from '@/components/ui/SectionTitle';
import type { Business, Strategy } from '@/types/api';

export function StrategyClient({ strategy, business }: { strategy: Strategy | null; business: Business | null }) {
  const actions = strategy?.nextBestActions || [];
  const calendar = strategy?.weeklyCalendar || [];

  return (
    <div className="page-stack">
      <SectionTitle title="Strategy & Recommendations" />
      <AppCard>
        <strong>Post-MVP preview</strong>
        <p style={{ color: 'var(--muted)' }}>
          Strategy generation is not part of the current v1 single-business MVP. This hidden route only shows previously stored strategy records when they exist.
        </p>
        {!business ? <p style={{ color: 'var(--muted)' }}>Complete business setup before using future strategy workflows.</p> : null}
      </AppCard>
      <div className="grid-responsive">
        <AppCard><h3>Best posting times</h3>{strategy?.bestPostingTimes?.length ? strategy.bestPostingTimes.map((item) => <p key={item}>{item}</p>) : <p style={{ color: 'var(--muted)' }}>No validated strategy data yet.</p>}</AppCard>
        <AppCard><h3>Target audience</h3><p>{strategy?.targetAudienceRecommendation || 'No validated strategy data yet.'}</p></AppCard>
        <AppCard><h3>Recommended hashtags</h3><div className="action-row">{strategy?.recommendedHashtags?.length ? strategy.recommendedHashtags.map((tag) => <span className="chip" key={tag}>{tag}</span>) : <span style={{ color: 'var(--muted)' }}>No validated strategy data yet.</span>}</div></AppCard>
      </div>
      <SectionTitle title="Weekly posting calendar" />
      <AppCard>{calendar.length ? <div className="action-row">{calendar.map((item, index) => <span className="day-plan" key={`${item.day}-${index}`}><strong>{item.day}</strong><small>{item.topic}</small></span>)}</div> : <p style={{ color: 'var(--muted)' }}>No validated strategy calendar yet.</p>}</AppCard>
      <SectionTitle title="Ranked next-best actions" />
      {actions.length ? actions.map((item, index) => (
        <AppCard key={item.title}>
          <div className="list-row">
            <span className="avatar">{index + 1}</span>
            <span><strong>{item.title}</strong><small>{item.reason}</small></span>
            <span className="action-row"><span className="chip">{item.impact}</span><span className="chip">{item.difficulty}</span></span>
          </div>
        </AppCard>
      )) : <AppCard>No validated next-best actions yet.</AppCard>}
    </div>
  );
}
