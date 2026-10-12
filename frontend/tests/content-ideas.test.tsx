import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ToastProvider } from '@/components/feedback/ToastProvider';
import { ContentIdeasClient } from '@/app/(dashboard)/generate/ContentIdeasClient';
import * as contentIdeasApi from '@/features/content-ideas/api';
import type { Business, ContentIdea } from '@/types/api';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ refresh: vi.fn() })
}));

const business: Business = {
  _id: 'business-1',
  ownerId: 'user-1',
  name: 'Nova Studio',
  industry: 'B2B AI software',
  country: 'US',
  productOrService: 'AI launch kits',
  targetAudience: 'Founders',
  goals: ['lead generation'],
  knownCompetitors: [],
  brandVoice: 'Sharp',
  preferredPlatforms: ['LinkedIn'],
  postingFrequency: '4 posts per week'
};

function idea(overrides: Partial<ContentIdea> = {}): ContentIdea {
  return {
    _id: 'idea-1',
    businessId: 'business-1',
    title: 'AI launch checklist',
    hook: 'A useful hook for founders.',
    caption: 'Use the launch checklist to pick the next campaign.',
    cta: 'Save this.',
    hashtags: ['#AI', '#Launch'],
    format: 'Carousel',
    engagementPotentialScore: 82,
    trendMatchScore: 74,
    reason: 'Rule-based estimate from business profile.',
    status: 'draft',
    ...overrides
  };
}

function renderIdeas(ideas: ContentIdea[]) {
  return render(
    <ToastProvider>
      <ContentIdeasClient business={business} ideas={ideas} />
    </ToastProvider>
  );
}

describe('content ideas client', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('labels scores as estimates instead of factual analytics', () => {
    renderIdeas([idea()]);
    expect(screen.getByText(/estimated engagement 82/i)).toBeInTheDocument();
    expect(screen.getByText(/profile fit estimate 74/i)).toBeInTheDocument();
    expect(screen.queryByText(/^Engagement 82$/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/^Trend match 74$/i)).not.toBeInTheDocument();
  });

  it('copies the exact visible idea content and shows feedback', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    renderIdeas([idea()]);

    await userEvent.click(screen.getByRole('button', { name: /copy idea/i }));

    expect(writeText).toHaveBeenCalledWith('A useful hook for founders.\n\nUse the launch checklist to pick the next campaign.\n\nCTA: Save this.\n\n#AI #Launch');
    expect(await screen.findByText(/idea copied/i)).toBeInTheDocument();
  });

  it('saves ideas with feedback and disables already-saved cards', async () => {
    vi.spyOn(contentIdeasApi, 'saveContentIdea').mockResolvedValue({ success: true, data: idea({ status: 'saved' }) });
    renderIdeas([idea()]);

    await userEvent.click(screen.getByRole('button', { name: /save idea/i }));

    await waitFor(() => expect(contentIdeasApi.saveContentIdea).toHaveBeenCalledWith('idea-1'));
    expect(await screen.findByText(/idea saved/i)).toBeInTheDocument();
  });

  it('does not delete unless the user confirms', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
    vi.spyOn(contentIdeasApi, 'deleteContentIdea').mockResolvedValue({ success: true, data: { id: 'idea-1' } });
    renderIdeas([idea()]);

    await userEvent.click(screen.getByRole('button', { name: /delete idea/i }));

    expect(confirm).toHaveBeenCalled();
    expect(contentIdeasApi.deleteContentIdea).not.toHaveBeenCalled();
  });

  it('deletes the selected idea after confirmation', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    vi.spyOn(contentIdeasApi, 'deleteContentIdea').mockResolvedValue({ success: true, data: { id: 'idea-1' } });
    renderIdeas([idea()]);

    await userEvent.click(screen.getByRole('button', { name: /delete idea/i }));

    await waitFor(() => expect(contentIdeasApi.deleteContentIdea).toHaveBeenCalledWith('idea-1'));
    expect(await screen.findByText(/idea removed/i)).toBeInTheDocument();
  });
});
