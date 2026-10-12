import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { Shell } from '@/components/layout/Shell';
import * as authApi from '@/features/auth/api';

const replace = vi.fn();
const refresh = vi.fn();

vi.mock('next/navigation', () => ({
  usePathname: () => '/dashboard',
  useRouter: () => ({ replace, refresh })
}));

describe('authenticated shell', () => {
  it('provides a global logout action', async () => {
    vi.spyOn(authApi, 'logout').mockResolvedValue({ success: true });
    render(<Shell><main>Dashboard content</main></Shell>);

    await userEvent.click(screen.getAllByRole('button', { name: /logout/i })[0]);

    await waitFor(() => expect(authApi.logout).toHaveBeenCalled());
    expect(replace).toHaveBeenCalledWith('/login');
    expect(refresh).toHaveBeenCalled();
  });
});
