import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ToastProvider } from '@/components/feedback/ToastProvider';
import { NotificationsClient } from '@/app/(dashboard)/notifications/NotificationsClient';
import * as notificationsApi from '@/features/notifications/api';
import type { AppNotification } from '@/types/api';

const refresh = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ refresh })
}));

function notification(overrides: Partial<AppNotification> = {}): AppNotification {
  return {
    _id: 'notification-1',
    businessId: 'business-1',
    notificationType: 'report_ready',
    title: 'Report ready',
    message: 'Your business report is ready.',
    readAt: null,
    createdAt: '2026-10-12T00:00:00Z',
    ...overrides
  };
}

function renderNotifications(notifications: AppNotification[]) {
  return render(
    <ToastProvider>
      <NotificationsClient notifications={notifications} />
    </ToastProvider>
  );
}

describe('notifications client', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('marks an unread notification as read', async () => {
    vi.spyOn(notificationsApi, 'markRead').mockResolvedValue({
      success: true,
      data: notification({ readAt: '2026-10-12T12:00:00Z' })
    });
    renderNotifications([notification()]);

    await userEvent.click(screen.getByRole('button', { name: /mark read/i }));

    await waitFor(() => expect(notificationsApi.markRead).toHaveBeenCalledWith('notification-1'));
    expect(await screen.findByText(/alert marked read/i)).toBeInTheDocument();
    expect(refresh).toHaveBeenCalled();
  });

  it('does not show a read action for already-read notifications', () => {
    renderNotifications([notification({ readAt: '2026-10-12T12:00:00Z' })]);

    expect(screen.getByText('Read')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /mark read/i })).not.toBeInTheDocument();
  });
});
