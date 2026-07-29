import type { ReactNode } from 'react';

export function AppCard({
  children,
  gradient = false,
  className = ''
}: {
  children: ReactNode;
  gradient?: boolean;
  className?: string;
}) {
  return <div className={`${gradient ? 'app-card gradient-card' : 'app-card'} ${className}`}>{children}</div>;
}
