export type Role = 'owner' | 'admin';
export type MomentumLabel = 'Emerging' | 'Peaking' | 'Fading';
export type ContentStatus = 'draft' | 'saved' | 'rejected';

export interface ApiEnvelope<T> {
  success: boolean;
  data: T;
  token?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  success: boolean;
  items: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    pages: number;
  };
}

export interface User {
  id: string;
  _id?: string;
  fullName: string;
  email: string;
  role: Role;
  createdAt?: string;
  updatedAt?: string;
}

export interface Business {
  _id: string;
  ownerId: string;
  name: string;
  industry: string;
  country: string;
  productOrService: string;
  targetAudience: string;
  goals: string[];
  knownCompetitors: string[];
  brandVoice: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface Competitor {
  _id: string;
  businessId: string;
  name: string;
  platform: string;
  profileUrl?: string;
  followers: number;
  engagementRate: number;
  postingFrequency: string;
  status: 'active' | 'paused' | 'archived';
  createdAt?: string;
  updatedAt?: string;
}

export interface CompetitorPost {
  _id: string;
  competitorId: string;
  businessId: string;
  platform: string;
  postUrl?: string;
  caption: string;
  hashtags: string[];
  hook: string;
  format: string;
  likes: number;
  comments: number;
  shares: number;
  views: number;
  engagementScore: number;
  publishedAt?: string;
  createdAt?: string;
}

export interface Trend {
  _id: string;
  businessId: string;
  topic: string;
  hashtags: string[];
  hooks: string[];
  format: string;
  momentumLabel: MomentumLabel;
  trendScore: number;
  growthRate: number;
  confidence: number;
  explanation: string;
  sourcePosts: string[];
  createdAt?: string;
}

export interface ContentIdea {
  _id: string;
  businessId: string;
  title: string;
  hook: string;
  caption: string;
  cta: string;
  hashtags: string[];
  format: string;
  engagementPotentialScore: number;
  trendMatchScore: number;
  reason: string;
  status: ContentStatus;
  createdAt?: string;
}

export interface NextBestAction {
  title: string;
  reason: string;
  impact: string;
  difficulty: string;
}

export interface Strategy {
  _id: string;
  businessId: string;
  weeklyCalendar: Array<{ day?: string; format?: string; topic?: string }>;
  bestPostingTimes: string[];
  recommendedHashtags: string[];
  targetAudienceRecommendation: string;
  nextBestActions: NextBestAction[];
  createdAt?: string;
}

export interface BusinessAnalysis {
  _id: string;
  businessId: string;
  strengths: string[];
  weaknesses: string[];
  opportunities: string[];
  threats: string[];
  growthRecommendations: Array<{ title?: string; signal?: string; impact?: string }>;
  createdAt?: string;
}

export interface AnalyticsSummary {
  totalFollowers: number;
  reach: number;
  impressions: number;
  engagement: number;
  engagementRate: number;
  likes: number;
  comments: number;
  shares: number;
  saves: number;
  clicks: number;
  videoViews: number;
  publishedPosts: number;
  scheduledPosts: number;
  competitorsTracked: number;
  byPlatform: Array<{ platform: string; followers: number }>;
}

export interface SocialConnection {
  _id: string;
  businessId: string;
  provider: string;
  status: string;
  displayName: string;
  requiredPermissions: string[];
  lastSuccessfulSyncAt?: string | null;
  lastError?: string;
  createdAt?: string;
}

export interface ContentDraft {
  _id: string;
  businessId: string;
  title: string;
  caption: string;
  platform: string;
  contentType: string;
  hashtags: string[];
  cta: string;
  status: string;
  scheduledAt?: string | null;
  timezone: string;
  approvalStatus: string;
  sourceAiGenerationId?: string | null;
  sourcePlanDay?: number | null;
  retryCount: number;
  maxRetries: number;
  createdAt?: string;
  updatedAt?: string;
}

export interface ContentPlanItem {
  day_number: number;
  title: string;
  platform: string;
  content_type: string;
  objective: string;
  topic: string;
  hook: string;
  caption: string;
  call_to_action: string;
  hashtags: string[];
  visual_brief: string;
  recommended_time: string;
  source_context: string[];
  risk_flags: string[];
  requires_human_review: boolean;
}

export interface ContentPlan {
  summary: string;
  primary_goal: string;
  target_audience: string;
  items: ContentPlanItem[];
}

export interface ContentPlanGenerationResponse {
  success: boolean;
  id: string;
  status: string;
  provider: string;
  model: string;
  prompt_version: string;
  plan: ContentPlan;
  usage: {
    input_tokens: number;
    output_tokens: number;
  };
  created_at: string;
  data: AIGeneration;
}

export interface ContentPlanQueueResponse {
  success: boolean;
  generation_id: string;
  task_id: string;
  status: 'queued' | 'running' | 'retrying' | 'completed' | 'failed' | 'cancelled' | string;
  status_url: string;
  data: AIGeneration;
}

export interface ContentPlanStatusResponse {
  success: boolean;
  generation_id: string;
  status: 'queued' | 'running' | 'retrying' | 'completed' | 'failed' | 'cancelled' | string;
  attempt_count: number;
  created_at: string;
  queued_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  failed_at?: string | null;
  error?: { code: string; message: string } | null;
  result_available: boolean;
  provider?: string;
  model?: string;
  prompt_version?: string;
  plan?: ContentPlan;
  usage?: {
    input_tokens: number;
    output_tokens: number;
  };
  data?: AIGeneration;
}

export interface AIGeneration {
  _id: string;
  businessId: string;
  objective: string;
  platform: string;
  audience: string;
  tone: string;
  language: string;
  contentFormat: string;
  featureName?: string;
  promptVersion?: string;
  generatedContent: {
    hook?: string;
    caption?: string;
    cta?: string;
    hashtags?: string[];
    alternatives?: Array<{ hook?: string; angle?: string }>;
    imagePrompt?: string;
  };
  structuredOutput?: ContentPlan | Record<string, unknown>;
  provider: string;
  model: string;
  usage: Record<string, unknown>;
  status?: string;
  draftLinks?: Record<string, string>;
  createdAt?: string;
}

export interface TeamMember {
  _id: string;
  businessId: string;
  userId: string;
  fullName: string;
  email: string;
  role: string;
  createdAt?: string;
}

export interface Report {
  _id: string;
  businessId: string;
  jobId?: string | null;
  title: string;
  reportType: string;
  dateRangeStart?: string | null;
  dateRangeEnd?: string | null;
  filters?: Record<string, unknown>;
  status: string;
  summary: Partial<AnalyticsSummary> & Record<string, number | string | undefined>;
  structuredContent?: BusinessPerformanceReport;
  provider?: string;
  model?: string;
  usage?: Record<string, unknown>;
  generatedAt?: string | null;
  createdAt?: string;
  updatedAt?: string;
}

export interface BusinessPerformanceReport {
  report_type: 'business_performance';
  period: { start: string; end: string };
  business_overview: {
    name: string;
    industry: string;
    country: string;
    product_or_service: string;
    target_audience: string;
    goals: string[];
  };
  metrics: Record<string, number>;
  platform_breakdown: Array<{ name: string; count: number; source?: string }>;
  content_type_breakdown: Array<{ name: string; count: number }>;
  objective_breakdown: Array<{ name: string; count: number }>;
  recent_trends: Array<Record<string, unknown>>;
  competitor_observations: Array<Record<string, unknown>>;
  highlights: string[];
  risks: string[];
  recommendations: Array<{ text: string; requires_human_review: boolean | string }>;
  data_limitations: string[];
}

export interface ReportQueueResponse {
  success: boolean;
  job_id: string;
  status: 'queued' | 'running' | 'retrying' | 'completed' | 'failed' | 'cancelled' | string;
  status_url: string;
}

export interface ReportJobStatusResponse {
  success: boolean;
  job_id: string;
  status: 'queued' | 'running' | 'retrying' | 'completed' | 'failed' | 'cancelled' | string;
  progress: number;
  progress_label: string;
  attempt_count: number;
  report_id?: string | null;
  error?: { code: string; message: string } | null;
  result_available: boolean;
  report?: Report;
  created_at: string;
  queued_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  failed_at?: string | null;
}

export interface AppNotification {
  _id: string;
  businessId: string;
  notificationType: string;
  title: string;
  message: string;
  readAt?: string | null;
  createdAt?: string;
}
