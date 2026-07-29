import { AuthCard } from '@/components/layout/AuthCard';
import { RegisterForm } from './RegisterForm';

export default function RegisterPage() {
  return (
    <AuthCard title="Create account" subtitle="Create an owner account for the backend API.">
      <RegisterForm />
    </AuthCard>
  );
}
