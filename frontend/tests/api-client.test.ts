import { describe, expect, it, vi } from 'vitest';
import { apiFetch } from '@/lib/api/client';

describe('apiFetch', () => {
  it('parses backend errors', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ message: 'Invalid email' }), { status: 422 })));
    await expect(apiFetch('/auth/login')).rejects.toThrow('Invalid email');
    vi.unstubAllGlobals();
  });

  it('returns typed json', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Response.json({ success: true, data: { ok: true } })));
    await expect(apiFetch('/business/me')).resolves.toEqual({ success: true, data: { ok: true } });
    vi.unstubAllGlobals();
  });
});
