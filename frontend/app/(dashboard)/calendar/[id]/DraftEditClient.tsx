'use client';

import { Save } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { useToast } from '@/components/feedback/ToastProvider';
import { AppCard } from '@/components/ui/AppCard';
import { Button } from '@/components/ui/Button';
import { updateDraft } from '@/features/planner/api';
import type { ContentDraft } from '@/types/api';

export function DraftEditClient({ draft }: { draft: ContentDraft }) {
  const router = useRouter();
  const { showToast } = useToast();
  const [saving, setSaving] = useState(false);
  const [values, setValues] = useState({
    title: draft.title,
    caption: draft.caption,
    cta: draft.cta,
    hashtags: draft.hashtags.join(', '),
    platform: draft.platform,
    contentType: draft.contentType,
    objective: draft.objective
  });

  function updateField(key: keyof typeof values, value: string) {
    setValues((current) => ({ ...current, [key]: value }));
  }

  async function save() {
    if (!values.title.trim()) {
      showToast('Title is required', 'error');
      return;
    }
    if (!values.caption.trim()) {
      showToast('Caption is required', 'error');
      return;
    }
    setSaving(true);
    try {
      await updateDraft(draft._id, {
        title: values.title,
        caption: values.caption,
        cta: values.cta,
        hashtags: split(values.hashtags),
        platform: values.platform,
        contentType: values.contentType,
        objective: values.objective
      });
      showToast('Draft saved');
      router.refresh();
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Could not save draft', 'error');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="page-stack">
      <div className="row-between">
        <h2>Edit Draft</h2>
        <span className="chip">{draft.status} · {draft.scheduledAt || 'Unscheduled'}</span>
      </div>
      <AppCard>
        <div className="form-stack">
          <label className="field"><span>Title / hook</span><input value={values.title} onChange={(event) => updateField('title', event.target.value)} /></label>
          <label className="field"><span>Caption</span><textarea rows={6} value={values.caption} onChange={(event) => updateField('caption', event.target.value)} /></label>
          <label className="field"><span>CTA</span><input value={values.cta} onChange={(event) => updateField('cta', event.target.value)} /></label>
          <label className="field"><span>Hashtags</span><input value={values.hashtags} onChange={(event) => updateField('hashtags', event.target.value)} /></label>
          <div className="form-grid">
            <label className="field"><span>Platform</span><input value={values.platform} onChange={(event) => updateField('platform', event.target.value)} /></label>
            <label className="field"><span>Content type</span><input value={values.contentType} onChange={(event) => updateField('contentType', event.target.value)} /></label>
          </div>
          <label className="field"><span>Objective</span><input value={values.objective} onChange={(event) => updateField('objective', event.target.value)} /></label>
          <Button onClick={save} disabled={saving}><Save size={18} /> {saving ? 'Saving...' : 'Save draft'}</Button>
        </div>
      </AppCard>
    </div>
  );
}

function split(value: string) {
  return value.split(',').map((item) => item.trim()).filter(Boolean);
}
