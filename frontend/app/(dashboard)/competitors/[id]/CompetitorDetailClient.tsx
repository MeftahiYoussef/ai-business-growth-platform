'use client';

import { Sparkles } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/Button';
import { AppCard } from '@/components/ui/AppCard';
import { SectionTitle } from '@/components/ui/SectionTitle';
import { useToast } from '@/components/feedback/ToastProvider';
import { generateCompetitorPosts } from '@/features/competitors/api';
import type { Competitor, CompetitorPost } from '@/types/api';

export function CompetitorDetailClient({ competitor, posts }: { competitor: Competitor; posts: CompetitorPost[] }) {
  const router = useRouter();
  const { showToast } = useToast();

  async function generate() {
    try {
      await generateCompetitorPosts(competitor._id);
      showToast('Mock posts generated');
      router.refresh();
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Could not generate posts', 'error');
    }
  }

  return (
    <div className="page-stack">
      <SectionTitle title={competitor.name} action={<Button onClick={generate}><Sparkles size={18} /> Generate posts</Button>} />
      <AppCard>
        <div className="action-row">
          <span className="chip">{competitor.followers} followers</span>
          <span className="chip">{competitor.engagementRate}% engagement</span>
          <span className="chip">{competitor.postingFrequency}</span>
          <span className="chip">{competitor.platform}</span>
        </div>
      </AppCard>
      <SectionTitle title="Mock posts" />
      {posts.length === 0 ? (
        <AppCard>No posts yet. Generate mock posts to seed this competitor.</AppCard>
      ) : (
        <div className="page-stack compact">
          {posts.map((post) => (
            <AppCard key={post._id}>
              <strong>{post.caption}</strong>
              <p style={{ color: 'var(--muted)' }}>{post.hook}</p>
              <div className="action-row">
                <span className="chip">{post.format}</span>
                <span className="chip">{post.engagementScore} engagement</span>
                {post.hashtags.map((tag) => <span className="chip" key={tag}>{tag}</span>)}
              </div>
            </AppCard>
          ))}
        </div>
      )}
      <SectionTitle title="Hashtags and hooks" />
      <AppCard>
        <div className="action-row">
          {posts.flatMap((post) => post.hashtags).slice(0, 8).map((tag, index) => <span className="chip" key={`${tag}-${index}`}>{tag}</span>)}
        </div>
        <div style={{ marginTop: 16 }}>
          {posts.slice(0, 4).map((post) => <p key={post._id}>“{post.hook}”</p>)}
        </div>
      </AppCard>
    </div>
  );
}
