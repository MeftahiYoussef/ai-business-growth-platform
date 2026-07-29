import { serverApi } from '@/lib/api/server';
import type { ApiEnvelope, Business, TeamMember } from '@/types/api';
import { TeamClient } from './TeamClient';

export default async function TeamPage() {
  const [business, members] = await Promise.all([
    serverApi<ApiEnvelope<Business | null>>('/business/me').catch(() => ({ success: true, data: null })),
    serverApi<ApiEnvelope<TeamMember[]>>('/team').catch(() => ({ success: true, data: [] }))
  ]);
  return <TeamClient business={business.data} members={members.data} />;
}
