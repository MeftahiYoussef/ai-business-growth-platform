import { AppCard } from '@/components/ui/AppCard';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { serverApi } from '@/lib/api/server';
import type { ApiEnvelope, AppNotification } from '@/types/api';
import { NotificationsClient } from './NotificationsClient';

export default async function NotificationsPage() {
  const notifications = await serverApi<ApiEnvelope<AppNotification[]>>('/notifications').catch(() => ({ success: true, data: [] }));
  return (
    <div className="page-stack">
      <SectionTitle title="Alerts" />
      {notifications.data.length === 0 ? <AppCard>No alerts yet. Workflow, report and social events will appear here.</AppCard> : <NotificationsClient notifications={notifications.data} />}
    </div>
  );
}
