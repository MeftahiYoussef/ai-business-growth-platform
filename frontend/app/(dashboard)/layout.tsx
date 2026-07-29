import { redirect } from 'next/navigation';
import { Shell } from '@/components/layout/Shell';
import { serverApi } from '@/lib/api/server';
import type { ApiEnvelope, User } from '@/types/api';

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  try {
    await serverApi<ApiEnvelope<User>>('/auth/me');
  } catch {
    redirect('/login');
  }

  return <Shell>{children}</Shell>;
}
