import { redirect } from 'next/navigation';
import { serverApi } from '@/lib/api/server';
import type { ApiEnvelope, Business } from '@/types/api';
import { OnboardingForm } from './OnboardingForm';

export default async function OnboardingPage() {
  const business = await serverApi<ApiEnvelope<Business | null>>('/business/me').catch(() => ({ success: true, data: null }));
  if (business.data) redirect('/dashboard');

  return (
    <div className="onboarding-page">
      <OnboardingForm />
    </div>
  );
}
