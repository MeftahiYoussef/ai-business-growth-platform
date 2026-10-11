'use client';

import { BookmarkPlus, Copy, RefreshCw, Trash2 } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/Button';
import { AppCard } from '@/components/ui/AppCard';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { EmptyState } from '@/components/ui/EmptyState';
import { useToast } from '@/components/feedback/ToastProvider';
import { deleteContentIdea, generateContentIdeas, saveContentIdea } from '@/features/content-ideas/api';
import type { Business, ContentIdea } from '@/types/api';

export function ContentIdeasClient({ ideas, business }: { ideas: ContentIdea[]; business: Business | null }) {
  const router = useRouter();
  const { showToast } = useToast();

  async function generate() {
    if (!business) return;
    try {
      await generateContentIdeas(business._id);
      showToast('Content ideas generated');
      router.refresh();
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Could not generate ideas', 'error');
    }
  }

  async function save(id: string) {
    try {
      await saveContentIdea(id);
      showToast('Idea saved');
      router.refresh();
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Could not save idea', 'error');
    }
  }

  async function remove(id: string) {
    if (!window.confirm('Delete this content idea?')) return;
    try {
      await deleteContentIdea(id);
      showToast('Idea removed');
      router.refresh();
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Could not delete idea', 'error');
    }
  }

  async function copyIdea(idea: ContentIdea) {
    const value = [
      idea.hook,
      '',
      idea.caption,
      '',
      `CTA: ${idea.cta}`,
      '',
      idea.hashtags.join(' ')
    ].join('\n');
    try {
      await navigator.clipboard.writeText(value);
      showToast('Idea copied');
    } catch {
      showToast('Could not copy idea', 'error');
    }
  }

  return (
    <div className="page-stack">
      <SectionTitle title="Content Generator" action={<Button onClick={generate} disabled={!business}><RefreshCw size={18} /> Generate Ideas</Button>} />
      {ideas.length === 0 ? (
        <EmptyState title="No content ideas yet" description="Generate ideas from your business and trend signals." />
      ) : ideas.map((idea) => (
        <AppCard key={idea._id}>
          <h2>{idea.hook}</h2>
          <p>{idea.caption}</p>
          <p><strong>CTA:</strong> {idea.cta}</p>
          <div className="action-row">
            {idea.hashtags.map((tag) => <span className="chip" key={tag}>{tag}</span>)}
          </div>
          <div className="row-between" style={{ marginTop: 12 }}>
            <div className="action-row">
              <span className="chip">Estimated engagement {idea.engagementPotentialScore}</span>
              <span className="chip">Context fit {idea.trendMatchScore}</span>
              <span className="chip">{idea.status}</span>
            </div>
            <div className="action-row">
              <button aria-label="Copy idea" onClick={() => copyIdea(idea)}><Copy size={18} /></button>
              <button aria-label="Save idea" disabled={idea.status === 'saved'} onClick={() => save(idea._id)}><BookmarkPlus size={18} /></button>
              <button aria-label="Delete idea" onClick={() => remove(idea._id)}><Trash2 size={18} /></button>
            </div>
          </div>
        </AppCard>
      ))}
    </div>
  );
}
