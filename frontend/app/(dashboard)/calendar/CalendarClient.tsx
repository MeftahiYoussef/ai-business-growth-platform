'use client';

import { CalendarPlus, CheckCircle2, Send } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { AppCard } from '@/components/ui/AppCard';
import { Button } from '@/components/ui/Button';
import { useToast } from '@/components/feedback/ToastProvider';
import { createDraft, workflowAction } from '@/features/planner/api';
import type { Business, ContentDraft } from '@/types/api';

export function CalendarClient({ business, drafts }: { business: Business | null; drafts: ContentDraft[] }) {
  const router = useRouter();
  const { showToast } = useToast();
  const [title, setTitle] = useState('Founder-led market signal post');
  async function create() {
    if (!business) return;
    try {
      await createDraft({ businessId: business._id, title, caption: 'Draft caption ready for review.', platform: 'LinkedIn', contentType: 'Post' });
      showToast('Draft created');
      router.refresh();
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Could not create draft', 'error');
    }
  }
  async function action(id: string, name: string) {
    try {
      await workflowAction(id, name, name === 'schedule' ? { scheduledAt: new Date(Date.now() + 86400000).toISOString() } : {});
      showToast('Workflow updated');
      router.refresh();
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Workflow action failed', 'error');
    }
  }
  return (
    <div className="page-stack">
      <div className="row-between"><h2>Content Calendar</h2><span className="chip">List view · UTC</span></div>
      <AppCard>
        <div className="form-stack">
          <label className="field"><span>Draft title</span><input value={title} onChange={(event) => setTitle(event.target.value)} /></label>
          <Button onClick={create} disabled={!business}><CalendarPlus size={18} /> Create draft</Button>
        </div>
      </AppCard>
      {drafts.length === 0 ? <AppCard>No calendar content yet.</AppCard> : drafts.map((draft) => (
        <AppCard key={draft._id}>
          <div className="row-between">
            <span>
              <strong>{draft.title}</strong>
              <small>{draft.platform} · {draft.contentType || 'Content'} · {draft.status} · {draft.scheduledAt || 'Unscheduled'}</small>
              {draft.objective ? <small>{draft.objective}</small> : null}
            </span>
            <span className="action-row">
              <Link className="button button-secondary" href={`/calendar/${draft._id}`}>Edit</Link>
              <Button variant="secondary" onClick={() => action(draft._id, 'request-review')}><Send size={16} /> Review</Button>
              <Button variant="secondary" onClick={() => action(draft._id, 'approve')}><CheckCircle2 size={16} /> Approve</Button>
              <Button onClick={() => action(draft._id, 'schedule')}>Schedule</Button>
            </span>
          </div>
        </AppCard>
      ))}
    </div>
  );
}
