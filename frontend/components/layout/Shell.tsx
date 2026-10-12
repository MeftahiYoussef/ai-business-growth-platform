'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Bolt, LineChart, LogOut } from 'lucide-react';
import { navItems } from '@/lib/constants/routes';
import { ToastProvider } from '@/components/feedback/ToastProvider';
import { logout } from '@/features/auth/api';

export function Shell({ children }: { children: React.ReactNode }) {
  return (
    <ToastProvider>
      <ShellContent>{children}</ShellContent>
    </ToastProvider>
  );
}

function ShellContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  async function signOut() {
    await logout();
    router.replace('/login');
    router.refresh();
  }

  return (
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
          <div className="action-row compact-actions">
            <span className="chip"><LineChart size={16} /> Backend intelligence</span>
            <button className="button button-secondary" type="button" onClick={signOut}>
              <LogOut size={16} /> Logout
            </button>
          </div>
        </header>
        <main className="content">{children}</main>
      </div>
      <nav className="bottom-nav" aria-label="Mobile navigation">
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = pathname.startsWith(item.href);
          return (
            <Link className={`bottom-link ${active ? 'active' : ''}`} href={item.href} key={item.href}>
              <Icon size={20} />
              <span>{item.label}</span>
            </Link>
          );
        })}
        <button className="bottom-link" type="button" onClick={signOut}>
          <LogOut size={20} />
          <span>Logout</span>
        </button>
      </nav>
    </div>
  );
}
