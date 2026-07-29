import { Sparkles } from 'lucide-react';
import { metricIcons } from '@/lib/constants/routes';
import { AppCard } from './AppCard';

export function MetricCard({
  label,
  value,
  note,
  kind
}: {
  label: string;
  value: string;
  note: string;
  kind: keyof typeof metricIcons;
}) {
  const Icon = metricIcons[kind];
  return (
    <AppCard className="metric-card">
      <Icon color="var(--primary)" size={24} />
      <div>
        <strong>{value}</strong>
        <span>{label}</span>
        <small>{note}</small>
      </div>
    </AppCard>
  );
}

export function AutoGraphIcon() {
  return <Sparkles aria-hidden size={44} />;
}
