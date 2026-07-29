'use client';

import { UserPlus } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { AppCard } from '@/components/ui/AppCard';
import { Button } from '@/components/ui/Button';
import { useToast } from '@/components/feedback/ToastProvider';
import { inviteMember } from '@/features/team/api';
import type { Business, TeamMember } from '@/types/api';

export function TeamClient({ business, members }: { business: Business | null; members: TeamMember[] }) {
  const router = useRouter();
  const { showToast } = useToast();
  const [email, setEmail] = useState('');
  async function invite() {
    if (!business || !email) return;
    try {
      await inviteMember({ businessId: business._id, email, role: 'content_creator' });
      showToast('Invitation created');
      setEmail('');
      router.refresh();
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Invite failed', 'error');
    }
  }
  return (
    <div className="page-stack">
      <div className="row-between"><h2>Team</h2><span className="chip">Business roles</span></div>
      <AppCard>
        <div className="form-actions">
          <label className="field" style={{ flex: 1 }}><span>Email</span><input value={email} onChange={(event) => setEmail(event.target.value)} placeholder="creator@example.com" /></label>
          <Button onClick={invite} disabled={!business || !email}><UserPlus size={18} /> Invite</Button>
        </div>
      </AppCard>
      {members.map((member) => (
        <AppCard key={member._id}>
          <div className="row-between"><span><strong>{member.fullName}</strong><small>{member.email}</small></span><span className="chip">{member.role}</span></div>
        </AppCard>
      ))}
    </div>
  );
}
