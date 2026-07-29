import { AppCard } from '@/components/ui/AppCard';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { serverApi } from '@/lib/api/server';
import type { ApiEnvelope, AppNotification } from '@/types/api';

export default async function NotificationsPage() {
  const notifications = await serverApi<ApiEnvelope<AppNotification[]>>('/notifications').catch(() => ({ success: true, data: [] }));
  return (
    <div className="page-stack">
      <SectionTitle title="Alerts" />
      {notifications.data.length === 0 ? <AppCard>No alerts yet. Workflow, report and social events will appear here.</AppCard> : notifications.data.map((item) => (
        <AppCard key={item._id}>
          <div className="row-between">
            <span><strong>{item.title}</strong><small>{item.message}</small></span>
            <span className="chip">{item.readAt ? 'Read' : 'Unread'}</span>
          </div>
        </AppCard>
      ))}
    </div>
  );
}
