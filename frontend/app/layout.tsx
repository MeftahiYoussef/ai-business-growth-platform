import type { Metadata } from 'next';
import './globals.css';
import '@/components/layout/shell.css';
import './(dashboard)/dashboard.css';
import './(dashboard)/dashboard-tables.css';

export const metadata: Metadata = {
  title: 'AI Business Growth & Trend Intelligence',
  description: 'Premium SaaS web dashboard for business growth and trend intelligence.'
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
