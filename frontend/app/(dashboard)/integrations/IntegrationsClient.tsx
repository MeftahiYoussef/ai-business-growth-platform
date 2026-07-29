'use client';

import { Plug, RefreshCw } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/Button';
import { AppCard } from '@/components/ui/AppCard';
import { useToast } from '@/components/feedback/ToastProvider';
import { connectSandbox, syncConnection } from '@/features/integrations/api';
import type { Business, SocialConnection } from '@/types/api';

export function IntegrationsClient({ business, connections }: { business: Business | null; connections: SocialConnection[] }) {
  const router = useRouter();
  const { showToast } = useToast();
  async function connect() {
    if (!business) return;
    try {
      await connectSandbox(business._id);
      showToast('Sandbox social account connected');
      router.refresh();
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Connection failed', 'error');
    }
  }
  async function sync(id: string) {
    try {
      await syncConnection(id);
      showToast('Synchronization completed');
      router.refresh();
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Sync failed', 'error');
    }
  }
  return (
    <div className="page-stack">
      <div className="row-between">
        <h2>Social Integrations</h2>
        <Button onClick={connect} disabled={!business}><Plug size={18} /> Connect sandbox</Button>
      </div>
      {connections.length === 0 ? <AppCard>No social accounts connected yet.</AppCard> : connections.map((item) => (
        <AppCard key={item._id}>
          <div className="row-between">
            <span><strong>{item.displayName}</strong><small>{item.provider} · {item.status}</small></span>
            <Button variant="secondary" onClick={() => sync(item._id)}><RefreshCw size={18} /> Sync</Button>
          </div>
        </AppCard>
      ))}
    </div>
  );
}
