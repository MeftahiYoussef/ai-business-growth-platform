'use client';

import Link from 'next/link';
import { Plus, RefreshCw, Search, Trash2 } from 'lucide-react';
import { useMemo, useState } from 'react';
import type { ChangeEvent } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Button } from '@/components/ui/Button';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { AppCard } from '@/components/ui/AppCard';
import { TextField } from '@/components/forms/TextField';
import { EmptyState } from '@/components/ui/EmptyState';
import { useToast } from '@/components/feedback/ToastProvider';
import { createCompetitor, deleteCompetitor } from '@/features/competitors/api';
import type { Business, Competitor, PaginatedResponse } from '@/types/api';

export function CompetitorsClient({
  initial,
  business
}: {
  initial: PaginatedResponse<Competitor>;
  business: Business | null;
}) {
  const router = useRouter();
  const params = useSearchParams();
  const { showToast } = useToast();
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ name: '', platform: 'LinkedIn', profileUrl: '' });
  const search = params.get('search') || '';
  const items = initial.items;
  const query = useMemo(() => new URLSearchParams(params), [params]);

  function updateSearch(value: string) {
    const next = new URLSearchParams(query);
    if (value) next.set('search', value);
    else next.delete('search');
    router.push(`/competitors?${next.toString()}`);
  }

  async function create() {
    if (!business) return;
    setSaving(true);
    try {
      await createCompetitor({ businessId: business._id, ...form });
      showToast('Competitor created');
      setOpen(false);
      setForm({ name: '', platform: 'LinkedIn', profileUrl: '' });
      router.refresh();
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Could not create competitor', 'error');
    } finally {
      setSaving(false);
    }
  }

  async function remove(id: string) {
    if (!window.confirm('Delete this competitor and its posts?')) return;
    await deleteCompetitor(id);
    showToast('Competitor deleted');
    router.refresh();
  }

  return (
    <div className="page-stack">
      <SectionTitle
        title="Competitors"
        action={
          <div className="action-row">
            <Button variant="secondary" onClick={() => router.refresh()}><RefreshCw size={18} /> Refresh</Button>
            <Button onClick={() => setOpen(true)} disabled={!business}><Plus size={18} /> Add</Button>
          </div>
        }
      />
      <AppCard>
        <div className="toolbar">
          <Search size={18} />
          <input aria-label="Search competitors" defaultValue={search} placeholder="Search competitors" onChange={(event) => updateSearch(event.target.value)} />
        </div>
      </AppCard>
      {items.length === 0 ? (
        <EmptyState title="No competitors yet" description="Add a competitor to start tracking posts and trend signals." />
      ) : (
        <>
          <div className="desktop-table app-card">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Platform</th>
                  <th>Followers</th>
                  <th>Engagement</th>
                  <th>Frequency</th>
                  <th aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item._id}>
                    <td><Link href={`/competitors/${item._id}`}>{item.name}</Link></td>
                    <td>{item.platform}</td>
                    <td>{Intl.NumberFormat('en', { notation: 'compact' }).format(item.followers)}</td>
                    <td>{item.engagementRate}%</td>
                    <td>{item.postingFrequency}</td>
                    <td><button aria-label={`Delete ${item.name}`} onClick={() => remove(item._id)}><Trash2 size={18} /></button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mobile-cards">
            {items.map((item) => (
              <Link className="app-card competitor-card" href={`/competitors/${item._id}`} key={item._id}>
                <strong>{item.name}</strong>
                <span>{item.platform} • {Intl.NumberFormat('en', { notation: 'compact' }).format(item.followers)} followers</span>
                <span>{item.engagementRate}% engagement • {item.postingFrequency}</span>
              </Link>
            ))}
          </div>
        </>
      )}
      {open ? (
        <div className="dialog-backdrop" role="dialog" aria-modal="true" aria-labelledby="add-competitor-title">
          <div className="app-card dialog">
            <h2 id="add-competitor-title">Add competitor</h2>
            <TextField label="Name" required value={form.name} onChange={(event: ChangeEvent<HTMLInputElement>) => setForm((value) => ({ ...value, name: event.target.value }))} />
            <TextField label="Platform" required value={form.platform} onChange={(event: ChangeEvent<HTMLInputElement>) => setForm((value) => ({ ...value, platform: event.target.value }))} />
            <TextField label="Profile URL" value={form.profileUrl} onChange={(event: ChangeEvent<HTMLInputElement>) => setForm((value) => ({ ...value, profileUrl: event.target.value }))} />
            <div className="form-actions">
              <Button variant="secondary" onClick={() => setOpen(false)}>Cancel</Button>
              <Button onClick={create} disabled={saving || !form.name || !form.platform}>{saving ? 'Creating...' : 'Create'}</Button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
