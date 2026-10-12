'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { useToast } from '@/components/feedback/ToastProvider';
import { AppCard } from '@/components/ui/AppCard';
import { Button } from '@/components/ui/Button';
import { markRead } from '@/features/notifications/api';
import type { AppNotification } from '@/types/api';

export function NotificationsClient({ notifications }: { notifications: AppNotification[] }) {
  const router = useRouter();
  const { showToast } = useToast();
  const [pendingId, setPendingId] = useState<string | null>(null);

  async function markNotificationRead(id: string) {
    setPendingId(id);
    try {
      await markRead(id);
      showToast('Alert marked read');
      router.refresh();
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Could not update alert', 'error');
    } finally {
      setPendingId(null);
    }
  }

  return (
    <div className="page-stack compact">
      {notifications.map((item) => (
        <AppCard key={item._id}>
          <div className="row-between">
            <span><strong>{item.title}</strong><small>{item.message}</small></span>
            <span className="action-row">
              <span className="chip">{item.readAt ? 'Read' : 'Unread'}</span>
              {!item.readAt ? (
                <Button variant="secondary" onClick={() => markNotificationRead(item._id)} disabled={pendingId === item._id}>
                  {pendingId === item._id ? 'Saving...' : 'Mark read'}
                </Button>
              ) : null}
            </span>
          </div>
        </AppCard>
      ))}
    </div>
  );
}
