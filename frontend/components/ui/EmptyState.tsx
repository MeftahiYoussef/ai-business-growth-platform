import { Inbox } from 'lucide-react';
import { AppCard } from './AppCard';

export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <AppCard>
      <div style={{ alignItems: 'center', display: 'flex', gap: 12 }}>
        <Inbox aria-hidden size={24} />
        <div>
          <strong>{title}</strong>
          <p style={{ color: 'var(--muted)', margin: '4px 0 0' }}>{description}</p>
        </div>
      </div>
    </AppCard>
  );
}
