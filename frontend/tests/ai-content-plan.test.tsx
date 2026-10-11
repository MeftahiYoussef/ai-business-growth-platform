import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ToastProvider } from '@/components/feedback/ToastProvider';
import { StudioClient } from '@/app/(dashboard)/studio/StudioClient';
import * as aiApi from '@/features/ai-studio/api';
import type { Business, ContentPlanGenerationResponse } from '@/types/api';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() })
}));

const business: Business = {
  _id: 'business-1',
  ownerId: 'user-1',
  name: 'Nova Studio',
  industry: 'SaaS',
  country: 'US',
  productOrService: 'AI launch kits',
  targetAudience: 'Founders',
  goals: ['engagement'],
  knownCompetitors: ['GrowthPilot'],
  brandVoice: 'Sharp'
};

function planResponse(): ContentPlanGenerationResponse {
  return {
    success: true,
    id: 'generation-1',
    status: 'completed',
    provider: 'mock',
    model: 'mock-social-content-v1',
    prompt_version: 'content-plan-v1',
    usage: { input_tokens: 10, output_tokens: 20 },
    created_at: '2026-08-03T00:00:00Z',
    data: {} as ContentPlanGenerationResponse['data'],
    plan: {
      summary: 'Weekly strategy summary',
      primary_goal: 'engagement',
      target_audience: 'Founders',
      items: Array.from({ length: 7 }, (_, index) => ({
        day_number: index + 1,
        title: `Plan item ${index + 1}`,
        platform: 'linkedin',
        content_type: 'linkedin_post',
        objective: 'engagement',
        topic: `Topic ${index + 1}`,
        hook: `Hook ${index + 1}`,
        caption: `Caption ${index + 1}`,
        call_to_action: 'Save this',
        hashtags: ['#growth'],
        visual_brief: 'Simple visual',
        recommended_time: '18:00',
        source_context: ['mock'],
        risk_flags: [],
        requires_human_review: true
      }))
    }
  };
}

function renderStudio() {
  return render(
    <ToastProvider>
      <StudioClient business={business} generations={[]} />
    </ToastProvider>
  );
}

describe('weekly content plan studio', () => {
  afterEach(() => {
    delete process.env.NEXT_PUBLIC_AI_ASYNC_CONTENT_PLAN;
    vi.restoreAllMocks();
    window.sessionStorage.clear();
  });

  it('renders seven generated items and creates selected drafts', async () => {
    vi.spyOn(aiApi, 'generateWeeklyContentPlan').mockResolvedValue(planResponse());
    vi.spyOn(aiApi, 'createDraftsFromPlan').mockResolvedValue({ success: true, data: [] });
    vi.spyOn(aiApi, 'generateStudioContent').mockResolvedValue({ success: true, data: {} as never });
    renderStudio();
    await userEvent.click(screen.getByRole('button', { name: /generate seven-day plan/i }));
    await waitFor(() => expect(screen.getByText(/weekly strategy summary/i)).toBeInTheDocument());
    expect(screen.getAllByText(/Plan item/i).length).toBe(7);
    await userEvent.click(screen.getByRole('button', { name: /create selected drafts/i }));
    expect(aiApi.createDraftsFromPlan).toHaveBeenCalledWith('generation-1', [1, 2, 3, 4, 5, 6, 7], {});
  });

  it('polls an asynchronous content plan job until completion', async () => {
    process.env.NEXT_PUBLIC_AI_ASYNC_CONTENT_PLAN = 'true';
    vi.spyOn(aiApi, 'queueWeeklyContentPlan').mockResolvedValue({
      success: true,
      generation_id: 'generation-async-1',
      task_id: 'task-1',
      status: 'queued',
      status_url: '/api/ai/content-plans/generation-async-1/status/',
      data: {} as never
    });
    vi.spyOn(aiApi, 'getContentPlanStatus').mockResolvedValue({
      ...planResponse(),
      generation_id: 'generation-async-1',
      attempt_count: 1,
      queued_at: '2026-08-03T00:00:00Z',
      started_at: '2026-08-03T00:00:01Z',
      completed_at: '2026-08-03T00:00:02Z',
      failed_at: null,
      error: null,
      result_available: true
    });
    vi.spyOn(aiApi, 'createDraftsFromPlan').mockResolvedValue({ success: true, data: [] });
    vi.spyOn(aiApi, 'generateStudioContent').mockResolvedValue({ success: true, data: {} as never });
    renderStudio();
    await userEvent.click(screen.getByRole('button', { name: /generate seven-day plan/i }));
    await waitFor(() => expect(aiApi.queueWeeklyContentPlan).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByText(/weekly strategy summary/i)).toBeInTheDocument());
    expect(aiApi.getContentPlanStatus).toHaveBeenCalledWith('generation-async-1');
    expect(screen.getAllByText(/Plan item/i).length).toBe(7);
  });

  it('does not show a recoverable queued state before asynchronous queue submission returns', async () => {
    process.env.NEXT_PUBLIC_AI_ASYNC_CONTENT_PLAN = 'true';
    let resolveQueue: (value: Awaited<ReturnType<typeof aiApi.queueWeeklyContentPlan>>) => void = () => {};
    vi.spyOn(aiApi, 'queueWeeklyContentPlan').mockReturnValue(
      new Promise((resolve) => {
        resolveQueue = resolve;
      })
    );
    vi.spyOn(aiApi, 'getContentPlanStatus').mockResolvedValue({
      ...planResponse(),
      generation_id: 'generation-async-1',
      attempt_count: 1,
      queued_at: '2026-08-03T00:00:00Z',
      started_at: '2026-08-03T00:00:01Z',
      completed_at: '2026-08-03T00:00:02Z',
      failed_at: null,
      error: null,
      result_available: true
    });
    vi.spyOn(aiApi, 'generateStudioContent').mockResolvedValue({ success: true, data: {} as never });

    renderStudio();
    await userEvent.click(screen.getByRole('button', { name: /generate seven-day plan/i }));

    expect(await screen.findByRole('button', { name: /submitting/i })).toBeDisabled();
    expect(window.sessionStorage.getItem('activeContentPlanGenerationId')).toBeNull();
    expect(screen.queryByRole('button', { name: /queued/i })).not.toBeInTheDocument();

    resolveQueue({
      success: true,
      generation_id: 'generation-async-1',
      task_id: 'task-1',
      status: 'queued',
      status_url: '/api/ai/content-plans/generation-async-1/status/',
      data: {} as never
    });

    await waitFor(() => expect(window.sessionStorage.getItem('activeContentPlanGenerationId')).toBe('generation-async-1'));
    await waitFor(() => expect(screen.getByText(/weekly strategy summary/i)).toBeInTheDocument());
  });

  it('clears the loading state when asynchronous queue submission fails', async () => {
    process.env.NEXT_PUBLIC_AI_ASYNC_CONTENT_PLAN = 'true';
    vi.spyOn(aiApi, 'queueWeeklyContentPlan').mockRejectedValue(new Error('Queue unavailable'));
    vi.spyOn(aiApi, 'generateStudioContent').mockResolvedValue({ success: true, data: {} as never });
    renderStudio();
    await userEvent.click(screen.getByRole('button', { name: /generate seven-day plan/i }));
    await waitFor(() => expect(screen.getByText(/queue unavailable/i)).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /generate seven-day plan/i })).not.toBeDisabled();
  });

  it('shows validation and API errors', async () => {
    vi.spyOn(aiApi, 'generateWeeklyContentPlan').mockRejectedValue(new Error('Provider unavailable'));
    renderStudio();
    for (const button of screen.getAllByRole('button', { name: /instagram|linkedin/i })) {
      await userEvent.click(button);
    }
    await userEvent.click(screen.getByRole('button', { name: /generate seven-day plan/i }));
    expect(await screen.findByText(/select at least one platform/i)).toBeInTheDocument();
  });

  it('does not reference provider API keys in client files', () => {
    const studio = readFileSync(join(process.cwd(), 'app/(dashboard)/studio/StudioClient.tsx'), 'utf8');
    const api = readFileSync(join(process.cwd(), 'features/ai-studio/api.ts'), 'utf8');
    expect(`${studio}\n${api}`).not.toMatch(/GROQ_API_KEY|NEXT_PUBLIC_GROQ/);
  });
});
