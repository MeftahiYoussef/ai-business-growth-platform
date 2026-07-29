'use client';

import { CalendarDays, FilePlus2, Sparkles } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { AppCard } from '@/components/ui/AppCard';
import { useToast } from '@/components/feedback/ToastProvider';
import { createDraftsFromPlan, generateStudioContent, generateWeeklyContentPlan } from '@/features/ai-studio/api';
import type { AIGeneration, Business, ContentPlanGenerationResponse, ContentPlanItem } from '@/types/api';

const platformOptions = ['instagram', 'facebook', 'linkedin', 'tiktok', 'youtube', 'x', 'pinterest'];

export function StudioClient({ business, generations }: { business: Business | null; generations: AIGeneration[] }) {
  const router = useRouter();
  const { showToast } = useToast();
  const [objective, setObjective] = useState('Generate a LinkedIn post for lead generation');
  const [platforms, setPlatforms] = useState<string[]>(['instagram', 'linkedin']);
  const [startDate, setStartDate] = useState(new Date(Date.now() + 86400000).toISOString().slice(0, 10));
  const [planGoal, setPlanGoal] = useState('increase engagement');
  const [instructions, setInstructions] = useState('Focus on educational content and competitor gaps.');
  const [planResult, setPlanResult] = useState<ContentPlanGenerationResponse | null>(null);
  const [selectedDays, setSelectedDays] = useState<number[]>([]);
  const [editedItems, setEditedItems] = useState<Record<string, Partial<ContentPlanItem>>>({});
  const [loadingPlan, setLoadingPlan] = useState(false);
  const [creatingDrafts, setCreatingDrafts] = useState(false);

  async function generate() {
    if (!business) return;
    try {
      await generateStudioContent({ businessId: business._id, objective, platform: 'LinkedIn', contentFormat: 'LinkedIn post' });
      showToast('AI content generated');
      router.refresh();
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Generation failed', 'error');
    }
  }

  function togglePlatform(platform: string) {
    setPlatforms((current) => current.includes(platform) ? current.filter((item) => item !== platform) : [...current, platform]);
  }

  function toggleDay(day: number) {
    setSelectedDays((current) => current.includes(day) ? current.filter((item) => item !== day) : [...current, day]);
  }

  function editItem(day: number, field: keyof ContentPlanItem, value: string) {
    setEditedItems((current) => ({ ...current, [day]: { ...(current[String(day)] || {}), [field]: value } }));
  }

  async function generatePlan() {
    if (!business) return;
    if (platforms.length === 0) {
      showToast('Select at least one platform', 'error');
      return;
    }
    setLoadingPlan(true);
    try {
      const result = await generateWeeklyContentPlan({
        businessId: business._id,
        platforms,
        startDate,
        goal: planGoal,
        additionalInstructions: instructions
      });
      setPlanResult(result);
      setSelectedDays(result.plan.items.map((item) => item.day_number));
      setEditedItems({});
      showToast('Seven-day content plan generated');
      router.refresh();
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Content plan generation failed', 'error');
    } finally {
      setLoadingPlan(false);
    }
  }

  async function createSelectedDrafts() {
    if (!planResult || selectedDays.length === 0) return;
    setCreatingDrafts(true);
    try {
      const response = await createDraftsFromPlan(planResult.id, selectedDays, editedItems);
      showToast(response.data.length ? `${response.data.length} draft(s) created` : 'Selected items already have drafts');
      router.push('/calendar');
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Could not create drafts', 'error');
    } finally {
      setCreatingDrafts(false);
    }
  }

  return (
    <div className="page-stack">
      <div className="row-between"><h2>AI Content Studio</h2><span className="chip">Backend AI provider</span></div>
      <AppCard>
        <div className="page-stack compact">
          <div className="row-between">
            <h3>Seven-day content plan</h3>
            <span className="chip"><CalendarDays size={14} /> Human review required</span>
          </div>
          <div className="form-grid">
            <label className="field"><span>Start date</span><input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} /></label>
            <label className="field"><span>Campaign goal</span><input value={planGoal} onChange={(event) => setPlanGoal(event.target.value)} maxLength={500} /></label>
          </div>
          <div className="action-row" aria-label="Platforms">
            {platformOptions.map((platform) => (
              <Button key={platform} type="button" variant={platforms.includes(platform) ? 'primary' : 'secondary'} onClick={() => togglePlatform(platform)}>
                {platform}
              </Button>
            ))}
          </div>
          <label className="field"><span>Additional instructions</span><textarea value={instructions} onChange={(event) => setInstructions(event.target.value)} rows={3} maxLength={1200} /></label>
          <Button onClick={generatePlan} disabled={!business || loadingPlan}><Sparkles size={18} /> {loadingPlan ? 'Generating...' : 'Generate seven-day plan'}</Button>
        </div>
      </AppCard>
      {planResult ? (
        <AppCard>
          <div className="page-stack compact">
            <div className="row-between">
              <span><strong>{planResult.plan.summary}</strong><small>{planResult.provider} · {planResult.model} · {planResult.prompt_version}</small></span>
              <span className="chip">{planResult.usage.input_tokens} in · {planResult.usage.output_tokens} out</span>
            </div>
            {planResult.plan.items.map((item) => {
              const edited = editedItems[String(item.day_number)] || {};
              return (
                <details key={item.day_number} className="app-card">
                  <summary className="row-between">
                    <span><strong>Day {item.day_number}: {edited.title || item.title}</strong><small>{item.platform} · {item.content_type} · {item.recommended_time}</small></span>
                    <label className="chip" onClick={(event) => event.stopPropagation()}>
                      <input type="checkbox" checked={selectedDays.includes(item.day_number)} onChange={() => toggleDay(item.day_number)} /> Select
                    </label>
                  </summary>
                  <div className="form-stack">
                    <label className="field"><span>Title</span><input value={edited.title || item.title} onChange={(event) => editItem(item.day_number, 'title', event.target.value)} /></label>
                    <label className="field"><span>Caption</span><textarea value={edited.caption || item.caption} onChange={(event) => editItem(item.day_number, 'caption', event.target.value)} rows={4} /></label>
                    <label className="field"><span>Call to action</span><input value={edited.call_to_action || item.call_to_action} onChange={(event) => editItem(item.day_number, 'call_to_action', event.target.value)} /></label>
                    <p>{item.hook}</p>
                    <small>{item.source_context.join(', ') || 'No source context'} · Review required: {String(item.requires_human_review)}</small>
                  </div>
                </details>
              );
            })}
            <Button onClick={createSelectedDrafts} disabled={creatingDrafts || selectedDays.length === 0}><FilePlus2 size={18} /> {creatingDrafts ? 'Creating drafts...' : 'Create selected drafts'}</Button>
          </div>
        </AppCard>
      ) : null}
      <AppCard>
        <div className="form-stack">
          <label className="field"><span>Objective</span><textarea value={objective} onChange={(event) => setObjective(event.target.value)} rows={3} /></label>
          <Button onClick={generate} disabled={!business}><Sparkles size={18} /> Generate content</Button>
        </div>
      </AppCard>
      {generations.length === 0 ? <AppCard>No generations yet.</AppCard> : generations.map((item) => (
        <AppCard key={item._id}>
          <div className="page-stack compact">
            <strong>{item.generatedContent.hook || item.objective}</strong>
            <p>{item.generatedContent.caption || item.featureName}</p>
            <span className="chip">{item.provider} · {item.model}</span>
          </div>
        </AppCard>
      ))}
    </div>
  );
}
