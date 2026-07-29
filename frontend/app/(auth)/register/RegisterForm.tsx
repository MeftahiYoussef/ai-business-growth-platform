'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowRight, Eye, EyeOff } from 'lucide-react';
import { useState, type ChangeEvent } from 'react';
import { z } from 'zod';
import { TextField } from '@/components/forms/TextField';
import { Button } from '@/components/ui/Button';
import { register } from '@/features/auth/api';

const schema = z.object({
  fullName: z.string().min(1, 'Full name is required.'),
  email: z.email('Enter a valid email.'),
  password: z.string().min(8, 'Password must be at least 8 characters.')
});

export function RegisterForm() {
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [values, setValues] = useState({ fullName: '', email: '', password: '' });

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const parsed = schema.safeParse(values);
    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message || 'Check your details.');
      return;
    }
    setLoading(true);
    try {
      await register(parsed.data);
      router.replace('/onboarding');
    } catch (apiError) {
      setError(apiError instanceof Error ? apiError.message : 'Registration failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className="form-stack" noValidate onSubmit={submit}>
      {error ? <div className="form-error">{error}</div> : null}
      <TextField label="Full name" name="fullName" required value={values.fullName} onChange={(event: ChangeEvent<HTMLInputElement>) => setValues((current) => ({ ...current, fullName: event.target.value }))} />
      <TextField label="Work email" name="email" type="email" required value={values.email} onChange={(event: ChangeEvent<HTMLInputElement>) => setValues((current) => ({ ...current, email: event.target.value }))} />
      <div style={{ display: 'grid', gap: 8 }}>
        <TextField label="Password" name="password" type={showPassword ? 'text' : 'password'} required value={values.password} onChange={(event: ChangeEvent<HTMLInputElement>) => setValues((current) => ({ ...current, password: event.target.value }))} />
        <button className="button button-secondary" type="button" onClick={() => setShowPassword((value) => !value)}>
          {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
          {showPassword ? 'Hide password' : 'Show password'}
        </button>
      </div>
      <Button disabled={loading} type="submit">
        <ArrowRight size={18} />
        {loading ? 'Creating...' : 'Continue to onboarding'}
      </Button>
      <Link className="button button-secondary" href="/login">Already have an account</Link>
    </form>
  );
}
