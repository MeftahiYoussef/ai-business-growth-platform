import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderToString } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { LoginForm } from '@/app/(auth)/login/LoginForm';
import { RegisterForm } from '@/app/(auth)/register/RegisterForm';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: vi.fn(), refresh: vi.fn() })
}));

describe('auth forms', () => {
  it('does not allow pre-hydration credential submission through GET forms', () => {
    const loginMarkup = renderToString(<LoginForm />);
    const registerMarkup = renderToString(<RegisterForm />);

    expect(loginMarkup).toContain('method="post"');
    expect(registerMarkup).toContain('method="post"');
    expect(loginMarkup).toContain('disabled=""');
    expect(registerMarkup).toContain('disabled=""');
  });

  it('shows login validation errors', async () => {
    render(<LoginForm />);
    await userEvent.click(screen.getByRole('button', { name: /login/i }));
    expect(screen.getByText(/enter a valid email/i)).toBeInTheDocument();
  });

  it('shows registration password validation', async () => {
    render(<RegisterForm />);
    await userEvent.type(screen.getByLabelText(/full name/i), 'Demo User');
    await userEvent.type(screen.getByLabelText(/work email/i), 'demo@example.com');
    await userEvent.type(screen.getByLabelText(/^password/i), 'short');
    await userEvent.click(screen.getByRole('button', { name: /continue to onboarding/i }));
    expect(screen.getByText(/at least 8 characters/i)).toBeInTheDocument();
  });
});
