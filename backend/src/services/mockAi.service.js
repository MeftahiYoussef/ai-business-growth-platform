const { calculateEngagementScore, calculateTrendScore } = require('./scoring.service');

const formats = ['Carousel', 'Short video', 'LinkedIn post', 'Thread', 'Case study'];
const momentumLabels = ['Emerging', 'Peaking', 'Fading'];

const generateCompetitorPosts = (competitor, count = 6) => {
  // TODO: Replace with social media data provider APIs for live competitor post ingestion.
  return Array.from({ length: count }, (_, index) => {
    const likes = 120 + index * 47;
    const comments = 18 + index * 6;
    const shares = 12 + index * 5;
    const views = 2400 + index * 800;

    return {
      competitorId: competitor._id,
      businessId: competitor.businessId,
      platform: competitor.platform,
      postUrl: competitor.profileUrl ? `${competitor.profileUrl}/mock-post-${index + 1}` : '',
      caption: `A practical breakdown of how ${competitor.name} turns market signals into buyer-ready content.`,
      hashtags: ['#aigrowth', '#trendintelligence', '#contentstrategy'],
      hook: index % 2 === 0 ? 'Most brands miss this signal before it peaks.' : 'Here is the content pattern competitors repeat every week.',
      format: formats[index % formats.length],
      likes,
      comments,
      shares,
      views,
      engagementScore: calculateEngagementScore({ likes, comments, shares, views }),
      publishedAt: new Date(Date.now() - index * 86400000)
    };
  });
};

const generateTrends = (business, sourcePosts = []) => {
  // TODO: Connect this to a real AI trend analysis API and social listening data.
  const topics = [
    `AI workflows for ${business.industry}`,
    `${business.targetAudience} pain-point teardowns`,
    `Founder-led proof for ${business.productOrService}`
  ];

  return topics.map((topic, index) => {
    const growthRate = 38 + index * 14;
    const confidence = 0.72 + index * 0.06;

    return {
      businessId: business._id,
      topic,
      hashtags: ['#aitools', '#growthstrategy', '#markettrends'],
      hooks: [
        'This trend is still early enough to own.',
        'Your competitors are already testing this angle.'
      ],
      format: formats[index % formats.length],
      momentumLabel: momentumLabels[index % momentumLabels.length],
      trendScore: calculateTrendScore({
        growthRate,
        confidence,
        sourceCount: sourcePosts.length || 1
      }),
      growthRate,
      confidence,
      explanation: `Mock analysis found repeated demand signals for ${topic}.`,
      sourcePosts: sourcePosts.slice(0, 5).map((post) => post._id)
    };
  });
};

const generateContentIdeas = (business, trends = [], count = 10) => {
  // TODO: Replace with real LLM-powered content ideation.
  return Array.from({ length: count }, (_, index) => {
    const trend = trends[index % Math.max(trends.length, 1)];
    const topic = trend?.topic || `growth signal for ${business.industry}`;

    return {
      businessId: business._id,
      title: `Post idea ${index + 1}: ${topic}`,
      hook: `The ${business.targetAudience} trend your competitors are testing now`,
      caption: `Show the signal, explain why it matters, and connect it to ${business.productOrService} with one practical example.`,
      cta: index % 2 === 0 ? 'Save this before your next planning session.' : 'Comment "growth" for the checklist.',
      hashtags: ['#aibusiness', '#contentops', '#trendstrategy'],
      format: formats[index % formats.length],
      engagementPotentialScore: 78 + (index % 5) * 4,
      trendMatchScore: trend?.trendScore || 82,
      reason: `Generated from mock trend signal: ${topic}.`,
      status: 'draft'
    };
  });
};

const generateStrategy = (business, trends = []) => {
  // TODO: Connect strategy generation to a real AI planning API.
  return {
    businessId: business._id,
    weeklyCalendar: [
      { day: 'Monday', format: 'LinkedIn post', topic: 'Market signal' },
      { day: 'Tuesday', format: 'Carousel', topic: trends[0]?.topic || 'AI workflow teardown' },
      { day: 'Wednesday', format: 'Short video', topic: 'Competitor lesson' },
      { day: 'Thursday', format: 'Thread', topic: 'Objection handling' },
      { day: 'Friday', format: 'Case study', topic: 'Customer proof' }
    ],
    bestPostingTimes: ['Tuesday 09:00', 'Thursday 11:30', 'Sunday 18:00'],
    recommendedHashtags: ['#aigrowth', '#founderbrand', '#contentstrategy'],
    targetAudienceRecommendation: `Prioritize ${business.targetAudience} with practical, proof-driven content.`,
    nextBestActions: [
      {
        title: 'Publish one AI workflow teardown',
        reason: 'Mock trend data shows high save potential.',
        impact: 'High',
        difficulty: 'Medium'
      },
      {
        title: 'Create competitor comparison content',
        reason: 'Competitor posts leave positioning gaps.',
        impact: 'High',
        difficulty: 'Medium'
      },
      {
        title: 'Move two posts to peak time windows',
        reason: 'Mock audience timing suggests better reach.',
        impact: 'Medium',
        difficulty: 'Low'
      }
    ]
  };
};

const generateBusinessAnalysis = (business, trends = []) => {
  // TODO: Replace mock SWOT generation with a real AI analysis workflow.
  return {
    businessId: business._id,
    strengths: ['Focused positioning', 'Clear target audience', 'High-value product category'],
    weaknesses: ['Limited proof assets', 'Inconsistent posting cadence', 'Manual competitor tracking'],
    opportunities: [
      trends[0]?.topic || 'AI workflow content',
      'Founder-led trust building',
      'Comparison and teardown formats'
    ],
    threats: ['Crowded AI tooling market', 'Fast trend decay', 'Competitors with larger audiences'],
    growthRecommendations: [
      {
        title: 'Build a weekly teardown series',
        signal: 'Trend and competitor content overlap',
        impact: 'High'
      },
      {
        title: 'Package a practical lead magnet',
        signal: 'Audience responds to templates and checklists',
        impact: 'Medium'
      }
    ]
  };
};

module.exports = {
  generateCompetitorPosts,
  generateTrends,
  generateContentIdeas,
  generateStrategy,
  generateBusinessAnalysis
};
