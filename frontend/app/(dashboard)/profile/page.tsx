import { serverApi } from '@/lib/api/server';
import type { ApiEnvelope, Business } from '@/types/api';
import { ProfileClient } from './ProfileClient';

export default async function ProfilePage() {
  const business = await serverApi<ApiEnvelope<Business | null>>('/business/me').catch(() => ({ success: true, data: null }));
  return <ProfileClient business={business.data} />;
}
