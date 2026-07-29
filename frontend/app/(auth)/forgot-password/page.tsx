import Link from 'next/link';
import { AuthCard } from '@/components/layout/AuthCard';

export default function ForgotPasswordPage() {
  return (
    <AuthCard title="Password reset" subtitle="Password reset is not implemented yet. Contact support.">
      <Link className="button button-primary" href="/login">Back to login</Link>
    </AuthCard>
  );
}
