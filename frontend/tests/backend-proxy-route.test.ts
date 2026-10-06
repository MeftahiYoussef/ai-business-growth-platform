import { describe, expect, it } from 'vitest';
import { backendProxyPath, isJsonContentType } from '@/app/api/backend/[...path]/route';

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

  it('distinguishes JSON API responses from download responses', () => {
    expect(isJsonContentType('application/json; charset=utf-8')).toBe(true);
    expect(isJsonContentType('text/csv')).toBe(false);
  });
});
