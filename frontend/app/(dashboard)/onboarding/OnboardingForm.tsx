'use client';

import { useRouter } from 'next/navigation';
import { useState, type ChangeEvent } from 'react';
import { TextField } from '@/components/forms/TextField';
import { Button } from '@/components/ui/Button';
import { createBusiness } from '@/features/businesses/api';

const steps = [
  { label: 'Business name', key: 'name' },
  { label: 'Industry', key: 'industry' },
  { label: 'Country', key: 'country' },
  { label: 'Product/service', key: 'productOrService' },
  { label: 'Target audience', key: 'targetAudience' },
  { label: 'Brand voice', key: 'brandVoice' },
  { label: 'Goals', key: 'goals', textarea: true },
  { label: 'Preferred platforms', key: 'preferredPlatforms', textarea: true },
  { label: 'Posting frequency', key: 'postingFrequency' },
  { label: 'Known competitors', key: 'knownCompetitors', textarea: true }
] as const;

type Values = Record<(typeof steps)[number]['key'], string>;

const defaults: Values = {
  name: 'Nova Studio',
  industry: 'Digital products',
  country: 'United States',
  productOrService: 'AI templates and launch kits',
  targetAudience: 'Founders, creators, and solo marketers',
  brandVoice: 'Clear, confident, and helpful',
  goals: 'Increase qualified leads and improve content consistency',
  preferredPlatforms: 'Instagram, LinkedIn',
  postingFrequency: '4 posts per week',
  knownCompetitors: 'LaunchKit, GrowthPilot, Trendly'
};

export function OnboardingForm() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [values, setValues] = useState<Values>(defaults);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const current = steps[step];

  async function next() {
    setError(null);
    if (!values[current.key].trim()) {
      setError(`${current.label} is required.`);
      return;
    }
    if (step < steps.length - 1) {
      setStep((value) => value + 1);
      return;
    }

    setSaving(true);
    try {
      await createBusiness({
        name: values.name,
        industry: values.industry,
        country: values.country,
        productOrService: values.productOrService,
        targetAudience: values.targetAudience,
        goals: split(values.goals),
        knownCompetitors: split(values.knownCompetitors),
        brandVoice: values.brandVoice,
        preferredPlatforms: split(values.preferredPlatforms),
        postingFrequency: values.postingFrequency
      });
      router.replace('/dashboard');
      router.refresh();
    } catch (apiError) {
      setError(apiError instanceof Error ? apiError.message : 'Could not save business.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="app-card onboarding-card">
      <h1>Business onboarding</h1>
      <p>Step {step + 1} of {steps.length}</p>
      <div className="progress" aria-label="Onboarding progress">
        <span style={{ width: `${((step + 1) / steps.length) * 100}%` }} />
      </div>
      <div style={{ minHeight: 170 }}>
        <TextField
          label={current.label}
          name={current.key}
          required
          textarea={'textarea' in current ? current.textarea : false}
          value={values[current.key]}
          onChange={(event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setValues((old) => ({ ...old, [current.key]: event.target.value }))}
        />
        {error ? <p className="error-text">{error}</p> : null}
      </div>
      <div className="onboarding-actions">
        {step > 0 ? <Button variant="secondary" onClick={() => setStep((value) => value - 1)}>Back</Button> : <span />}
        <Button onClick={next} disabled={saving}>{saving ? 'Saving...' : step === steps.length - 1 ? 'Finish' : 'Next'}</Button>
      </div>
    </div>
  );
}

function split(value: string) {
  return value.split(',').map((item) => item.trim()).filter(Boolean);
}
