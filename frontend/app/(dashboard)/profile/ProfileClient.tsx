'use client';

import { Building2, Contrast, LogOut, Rocket, Timer } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/Button';
import { AppCard } from '@/components/ui/AppCard';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { logout } from '@/features/auth/api';
import type { Business } from '@/types/api';

export function ProfileClient({ business }: { business: Business | null }) {
  const router = useRouter();

  async function signOut() {
    await logout();
    router.replace('/login');
    router.refresh();
  }

  function toggleTheme(checked: boolean) {
    document.documentElement.dataset.theme = checked ? 'light' : 'dark';
  }

  return (
    <div className="page-stack">
      <SectionTitle title="Profile / Settings" />
      <AppCard>
        <div className="list-row">
          <span className="avatar"><Building2 size={20} /></span>
          <span><strong>{business?.name || 'No business yet'}</strong><small>{business ? `${business.industry} • ${business.country}` : 'Complete onboarding'}</small></span>
        </div>
        <hr />
        <InfoRow label="Product/service" value={business?.productOrService || '-'} />
        <InfoRow label="Target audience" value={business?.targetAudience || '-'} />
        <InfoRow label="Brand voice" value={business?.brandVoice || '-'} />
        <InfoRow label="Goals" value={business?.goals.join(', ') || '-'} />
        <InfoRow label="Known competitors" value={business?.knownCompetitors.join(', ') || '-'} />
      </AppCard>
      <AppCard>
        <div className="list-row"><Rocket size={22} /><span><strong>Subscription</strong><small>Growth Pro placeholder</small></span></div>
        <div className="list-row"><Timer size={22} /><span><strong>Usage</strong><small>42 generated ideas • 3 competitors tracked</small></span></div>
        <label className="switch-row"><Contrast size={22} /><span>Light mode</span><input type="checkbox" onChange={(event) => toggleTheme(event.target.checked)} /></label>
        <Button onClick={signOut}><LogOut size={18} /> Logout</Button>
      </AppCard>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return <div className="info-row"><strong>{label}</strong><span>{value}</span></div>;
}
