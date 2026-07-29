'use client';

import { Sparkles } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/Button';
import { AppCard } from '@/components/ui/AppCard';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { useToast } from '@/components/feedback/ToastProvider';
import { generateStrategy } from '@/features/strategies/api';
import type { Business, Strategy } from '@/types/api';

const fallbackActions = [
  { title: 'Publish one AI workflow teardown', reason: 'Competitors with teardown posts are averaging higher saves.', impact: 'High', difficulty: 'Medium' },
  { title: 'Shift two posts to Tuesday morning', reason: 'Audience activity and competitor gaps overlap at 9 AM.', impact: 'Medium', difficulty: 'Low' },
  { title: 'Turn objections into a comparison carousel', reason: 'Pricing and trust objections appear across top competitor comments.', impact: 'High', difficulty: 'Medium' }
];

export function StrategyClient({ strategy, business }: { strategy: Strategy | null; business: Business | null }) {
  const router = useRouter();
  const { showToast } = useToast();
  const actions = strategy?.nextBestActions?.length ? strategy.nextBestActions : fallbackActions;
  const calendar = strategy?.weeklyCalendar?.length ? strategy.weeklyCalendar : [
    { day: 'Mon', topic: 'Market insight' },
    { day: 'Tue', topic: 'AI workflow teardown' },
    { day: 'Wed', topic: 'Competitor lesson' },
    { day: 'Thu', topic: 'Carousel' },
    { day: 'Fri', topic: 'Founder story' }
  ];

  async function generate() {
    if (!business) return;
    try {
      await generateStrategy(business._id);
      showToast('Strategy generated');
      router.refresh();
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Could not generate strategy', 'error');
    }
  }

  return (
    <div className="page-stack">
      <SectionTitle title="Strategy & Recommendations" action={<Button onClick={generate} disabled={!business}><Sparkles size={18} /> Generate</Button>} />
      <div className="grid-responsive">
        <AppCard><h3>Best posting times</h3>{(strategy?.bestPostingTimes?.length ? strategy.bestPostingTimes : ['Tue 9:00 AM', 'Thu 11:30 AM', 'Sun 6:00 PM']).map((item) => <p key={item}>{item}</p>)}</AppCard>
        <AppCard><h3>Target audience</h3><p>{strategy?.targetAudienceRecommendation || 'Solo founders, B2B creators, Marketing operators'}</p></AppCard>
        <AppCard><h3>Recommended hashtags</h3><div className="action-row">{(strategy?.recommendedHashtags?.length ? strategy.recommendedHashtags : ['#aigrowth', '#founderbrand', '#contentops']).map((tag) => <span className="chip" key={tag}>{tag}</span>)}</div></AppCard>
      </div>
      <SectionTitle title="Weekly posting calendar" />
      <AppCard><div className="action-row">{calendar.map((item, index) => <span className="day-plan" key={`${item.day}-${index}`}><strong>{item.day}</strong><small>{item.topic}</small></span>)}</div></AppCard>
      <SectionTitle title="Ranked next-best actions" />
      {actions.map((item, index) => (
        <AppCard key={item.title}>
          <div className="list-row">
            <span className="avatar">{index + 1}</span>
            <span><strong>{item.title}</strong><small>{item.reason}</small></span>
            <span className="action-row"><span className="chip">{item.impact}</span><span className="chip">{item.difficulty}</span></span>
          </div>
        </AppCard>
      ))}
    </div>
  );
}
