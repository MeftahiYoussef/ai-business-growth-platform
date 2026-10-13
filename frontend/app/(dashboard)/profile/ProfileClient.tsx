'use client';

import { Building2, Contrast, LogOut, Rocket, Timer } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { AppCard } from '@/components/ui/AppCard';
import { useToast } from '@/components/feedback/ToastProvider';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { logout } from '@/features/auth/api';
import { updateBusiness } from '@/features/businesses/api';
import type { Business } from '@/types/api';

export function ProfileClient({ business }: { business: Business | null }) {
  const router = useRouter();
  const { showToast } = useToast();
  const [saving, setSaving] = useState(false);
  const [values, setValues] = useState({
    name: business?.name || '',
    industry: business?.industry || '',
    country: business?.country || '',
    productOrService: business?.productOrService || '',
    targetAudience: business?.targetAudience || '',
    brandVoice: business?.brandVoice || '',
    goals: (business?.goals || []).join(', '),
    preferredPlatforms: (business?.preferredPlatforms || []).join(', '),
    postingFrequency: business?.postingFrequency || '',
    knownCompetitors: (business?.knownCompetitors || []).join(', ')
  });

  async function signOut() {
    await logout();
    router.replace('/login');
    router.refresh();
  }

  function toggleTheme(checked: boolean) {
    document.documentElement.dataset.theme = checked ? 'light' : 'dark';
  }

  function updateField(key: keyof typeof values, value: string) {
    setValues((current) => ({ ...current, [key]: value }));
  }

  async function saveBusiness() {
    if (!business) return;
    setSaving(true);
    try {
      await updateBusiness(business._id, {
        name: values.name,
        industry: values.industry,
        country: values.country,
        productOrService: values.productOrService,
        targetAudience: values.targetAudience,
        brandVoice: values.brandVoice,
        goals: split(values.goals),
        preferredPlatforms: split(values.preferredPlatforms),
        postingFrequency: values.postingFrequency,
        knownCompetitors: split(values.knownCompetitors)
      });
      showToast('Business profile saved');
      router.refresh();
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Could not save business profile', 'error');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="page-stack">
      <SectionTitle title="Profile / Settings" />
      <AppCard>
        <div className="list-row">
          <span className="avatar"><Building2 size={20} /></span>
          <span><strong>{business?.name || 'No business yet'}</strong><small>{business ? `${business.industry} • ${business.country}` : 'Complete onboarding'}</small></span>
        </div>
        <hr />
        <InfoRow label="Product/service" value={business?.productOrService || '-'} />
        <InfoRow label="Target audience" value={business?.targetAudience || '-'} />
        <InfoRow label="Brand voice" value={business?.brandVoice || '-'} />
        <InfoRow label="Goals" value={business?.goals.join(', ') || '-'} />
        <InfoRow label="Preferred platforms" value={business?.preferredPlatforms?.join(', ') || '-'} />
        <InfoRow label="Posting frequency" value={business?.postingFrequency || '-'} />
        <InfoRow label="Known competitors" value={business?.knownCompetitors.join(', ') || '-'} />
      </AppCard>
      <AppCard>
        <div className="form-stack">
          <strong>Edit business profile</strong>
          <div className="form-grid">
            <label className="field"><span>Business name</span><input value={values.name} onChange={(event) => updateField('name', event.target.value)} disabled={!business} /></label>
            <label className="field"><span>Industry</span><input value={values.industry} onChange={(event) => updateField('industry', event.target.value)} disabled={!business} /></label>
            <label className="field"><span>Market / location</span><input value={values.country} onChange={(event) => updateField('country', event.target.value)} disabled={!business} /></label>
            <label className="field"><span>Products / services</span><input value={values.productOrService} onChange={(event) => updateField('productOrService', event.target.value)} disabled={!business} /></label>
          </div>
          <label className="field"><span>Target audience</span><input value={values.targetAudience} onChange={(event) => updateField('targetAudience', event.target.value)} disabled={!business} /></label>
          <label className="field"><span>Brand voice</span><input value={values.brandVoice} onChange={(event) => updateField('brandVoice', event.target.value)} disabled={!business} /></label>
          <label className="field"><span>Objectives</span><textarea value={values.goals} onChange={(event) => updateField('goals', event.target.value)} disabled={!business} rows={2} /></label>
          <div className="form-grid">
            <label className="field"><span>Preferred platforms</span><input value={values.preferredPlatforms} onChange={(event) => updateField('preferredPlatforms', event.target.value)} disabled={!business} /></label>
            <label className="field"><span>Posting frequency</span><input value={values.postingFrequency} onChange={(event) => updateField('postingFrequency', event.target.value)} disabled={!business} /></label>
          </div>
          <label className="field"><span>Known competitors</span><textarea value={values.knownCompetitors} onChange={(event) => updateField('knownCompetitors', event.target.value)} disabled={!business} rows={2} /></label>
          <Button onClick={saveBusiness} disabled={!business || saving}>{saving ? 'Saving...' : 'Save business profile'}</Button>
        </div>
      </AppCard>
      <AppCard>
        <div className="list-row"><Rocket size={22} /><span><strong>Plan</strong><small>Free staging/demo workspace</small></span></div>
        <div className="list-row"><Timer size={22} /><span><strong>Usage</strong><small>Usage limits are enforced server-side for AI generation and reports.</small></span></div>
        <label className="switch-row"><Contrast size={22} /><span>Light mode</span><input type="checkbox" onChange={(event) => toggleTheme(event.target.checked)} /></label>
        <Button onClick={signOut}><LogOut size={18} /> Logout</Button>
      </AppCard>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return <div className="info-row"><strong>{label}</strong><span>{value}</span></div>;
}

function split(value: string) {
  return value.split(',').map((item) => item.trim()).filter(Boolean);
}
