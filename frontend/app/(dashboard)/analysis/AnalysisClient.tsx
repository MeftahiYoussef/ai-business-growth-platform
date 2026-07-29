'use client';

import { Sparkles, ThumbsUp } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/Button';
import { AppCard } from '@/components/ui/AppCard';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { useToast } from '@/components/feedback/ToastProvider';
import { generateAnalysis } from '@/features/analyses/api';
import type { Business, BusinessAnalysis } from '@/types/api';

export function AnalysisClient({ analysis, business }: { analysis: BusinessAnalysis | null; business: Business | null }) {
  const router = useRouter();
  const { showToast } = useToast();
  async function generate() {
    if (!business) return;
    try {
      await generateAnalysis(business._id);
      showToast('Business analysis generated');
      router.refresh();
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Could not generate analysis', 'error');
    }
  }

  return (
    <div className="page-stack">
      <SectionTitle title="Business Analysis" action={<Button onClick={generate} disabled={!business}><Sparkles size={18} /> Generate</Button>} />
      <div className="grid-responsive">
        <SwotCard title="Strengths" items={analysis?.strengths || ['Clear niche', 'Fast content production', 'Useful AI positioning']} />
        <SwotCard title="Weaknesses" items={analysis?.weaknesses || ['Low posting consistency', 'Limited proof assets', 'Few comparison posts']} />
        <SwotCard title="Opportunities" items={analysis?.opportunities || ['AI workflow trends', 'Founder-led demand', 'Competitor content gaps']} />
        <SwotCard title="Threats" items={analysis?.threats || ['Crowded tool market', 'Short trend cycles', 'Rising ad costs']} />
      </div>
      <SectionTitle title="Growth recommendations" />
      {(analysis?.growthRecommendations?.length ? analysis.growthRecommendations : [
        { title: 'Create weekly teardown series', signal: 'Signal: AI workflow teardowns are peaking with high saves.' },
        { title: 'Add competitor comparison content', signal: 'Signal: buyer objections appear in competitor comments.' },
        { title: 'Package one lead magnet', signal: 'Signal: audience responds to templates and checklists.' }
      ]).map((item) => (
        <AppCard key={item.title}>
          <div className="list-row">
            <ThumbsUp size={22} />
            <span><strong>{item.title}</strong><small>{item.signal}</small></span>
          </div>
        </AppCard>
      ))}
    </div>
  );
}

function SwotCard({ title, items }: { title: string; items: string[] }) {
  return <AppCard><h3>{title}</h3>{items.map((item) => <p key={item}>• {item}</p>)}</AppCard>;
}
