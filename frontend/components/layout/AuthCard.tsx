import { Bolt } from 'lucide-react';
import type { ReactNode } from 'react';
import { AppCard } from '@/components/ui/AppCard';

export function AuthCard({
  title,
  subtitle,
  children
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <main className="auth-page">
      <AppCard className="auth-card">
        <div className="auth-heading">
          <span className="brand-mark"><Bolt size={22} /></span>
          <div>
            <h1>{title}</h1>
            <p>{subtitle}</p>
          </div>
        </div>
        {children}
      </AppCard>
    </main>
  );
}
