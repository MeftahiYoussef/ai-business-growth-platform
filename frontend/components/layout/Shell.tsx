'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Bolt, LineChart } from 'lucide-react';
import { navItems } from '@/lib/constants/routes';
import { ToastProvider } from '@/components/feedback/ToastProvider';

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <ToastProvider>
      <div className="shell">
        <aside className="sidebar" aria-label="Main navigation">
          <Link className="brand" href="/dashboard">
            <span className="brand-mark"><Bolt size={23} /></span>
            <strong>TrendIntel</strong>
          </Link>
          <nav className="side-nav">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = pathname.startsWith(item.href);
              return (
                <Link className={`nav-link ${active ? 'active' : ''}`} href={item.href} key={item.href}>
                  <Icon size={20} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </aside>
        <div className="workspace">
          <header className="topbar">
            <h1>AI Business Growth & Trend Intelligence Platform</h1>
            <span className="chip"><LineChart size={16} /> Backend intelligence</span>
          </header>
          <main className="content">{children}</main>
        </div>
        <nav className="bottom-nav" aria-label="Mobile navigation">
          {navItems.slice(0, 5).map((item) => {
            const Icon = item.icon;
            const active = pathname.startsWith(item.href);
            return (
              <Link className={`bottom-link ${active ? 'active' : ''}`} href={item.href} key={item.href}>
                <Icon size={20} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </ToastProvider>
  );
}
