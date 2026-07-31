import { describe, expect, it } from 'vitest';
import { backendProxyPath } from '@/app/api/backend/[...path]/route';

describe('backendProxyPath', () => {
  it('preserves trailing slash for Django POST endpoints', () => {
    expect(
      backendProxyPath(['ai', 'content-plans', 'queue'])
    ).toBe('/ai/content-plans/queue/');
  });

  it('adds the Django trailing slash when Vercel normalizes the browser path', () => {
    expect(
      backendProxyPath(['ai', 'studio', 'history'])
    ).toBe('/ai/studio/history/');
  });
});
