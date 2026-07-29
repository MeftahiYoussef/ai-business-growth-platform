import { AuthCard } from '@/components/layout/AuthCard';
import { LoginForm } from './LoginForm';

export default function LoginPage() {
  return (
    <AuthCard title="Welcome back" subtitle="Sign in to your growth intelligence workspace.">
      <LoginForm />
    </AuthCard>
  );
}
