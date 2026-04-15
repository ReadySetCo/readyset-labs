/**
 * API Client for Brand Intelligence Scraper
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Types
export interface Brand {
  id: number;
  name: string;
  website_url?: string;
  description?: string;
  sector?: string;
  vertical?: string;
  products?: string[];
  target_audience?: string;
  // Brand DNA fields
  brand_colors?: string[];
  tagline?: string;
  brand_values?: string[];
  brand_aesthetic?: string[];
  tone_of_voice?: string[];
  logo_url?: string;
  fonts?: string[];
  brand_images?: string[];
  social_media_urls?: Record<string, string>;
  product_descriptions?: Array<{ name: string; description?: string }>;
  created_at: string;
  updated_at: string;
}

export interface ResearchSession {
  id: number;
  brand_id: number;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  started_at: string;
  completed_at?: string;
  brand_queries?: Record<string, string[]>;
  segment_queries?: Record<string, string[]>;
}

export interface ResearchProgress {
  session_id: number;
  status: string;
  current_step: string;
  current_phase: string;
  progress_percent: number;
  sources_completed: string[];
  sources_pending: string[];
  estimated_time_remaining?: number;
}

export interface ICP {
  name: string;
  description: string;
  age_range?: string;
  characteristics: string[];
}

export interface MessagingAngle {
  name: string;
  hook: string;
  description: string;
}

export interface CompetitorAnalysis {
  main_competitors?: string[];
  our_advantages?: string[];
  their_advantages?: string[];
  positioning_opportunity?: string;
}

export interface Objection {
  objection: string;
  frequency?: string;
  counter_messaging?: string;
}

export interface VerbatimQuote {
  quote: string;
  context?: string;
  use_case?: string;
}

export interface RecommendedHook {
  hook: string;
  type?: string;
  target_persona?: string;
  reasoning?: string;
}

export interface PriceSensitivity {
  overall_sensitivity?: string;
  price_complaints?: string[];
  value_perception?: string;
}

export interface AdCreativePatterns {
  total_analyzed?: number;
  frameworks?: Record<string, number>;
  hook_types?: Record<string, number>;
  avg_hook_strength?: number;
  avg_effectiveness?: number;
  emotions?: Record<string, number>;
  tones?: Record<string, number>;
  top_transcriptions?: Array<{
    library_id?: string;
    text?: string;
    hook_strength?: number;
    effectiveness?: number;
  }>;
}

export interface GeneratedScript {
  script_name: string;
  framework?: string;
  hook_type?: string;
  target_emotion?: string;
  estimated_length_seconds?: number;
  hook?: string;
  body?: string;
  full_script?: string;
  cta?: string;
  visual_notes?: string;
  why_it_works?: string;
  best_for?: string;
}

export interface ThumbnailSuggestion {
  concept_name: string;
  thumbnail_type?: string;
  visual_description?: string;
  text_overlay?: string;
  color_scheme?: string;
  emotion_evoked?: string;
  why_it_works?: string;
  best_paired_with?: string;
  platform_fit?: string[];
}

export interface ABTestSuggestion {
  test_name: string;
  test_type?: string;
  priority?: string;
  hypothesis?: string;
  control?: { description?: string; example?: string } | string;
  variant?: { description?: string; example?: string } | string;
  expected_impact?: string;
  rationale?: string;
}

export interface CompetitorProfile {
  name: string;
  website?: string;
  positioning?: string;
  estimated_size?: string;
  key_differentiator?: string;
  tagline?: string;
  value_props?: string[];
  products?: string[];
}

export interface SWOTAnalysis {
  strengths?: Array<{ point: string; evidence?: string; leverage_how?: string } | string>;
  weaknesses?: Array<{ point: string; evidence?: string; mitigate_how?: string } | string>;
  opportunities?: Array<{ point: string; evidence?: string; capture_how?: string } | string>;
  threats?: Array<{ point: string; evidence?: string; defend_how?: string } | string>;
  strategic_priorities?: string[];
}

export interface DataSummary {
  total_items?: number;
  by_source?: Record<string, number>;
  by_track?: Record<number, number>;
  by_mention_type?: Record<string, number>;
  by_sentiment?: Record<string, number>;
}

// TikTok Trends Types
export interface TrendingSound {
  name: string;
  author?: string;
  usage_count: number;
  avg_engagement: number;
  trend_score: number;
  sound_id?: string;
}

export interface TrendingHashtag {
  hashtag: string;
  usage_count: number;
  avg_engagement: number;
  velocity_score: number;
  category: string;
}

export interface ContentPatterns {
  duration_stats?: {
    avg_seconds: number;
    median_seconds: number;
    most_common_range: string;
    distribution: Record<string, number>;
  };
  popular_formats?: Array<{ format: string; count: number }>;
  hook_styles?: Array<{ style: string; count: number }>;
}

export interface TikTokTrends {
  status: string;
  videos_analyzed: number;
  trending_sounds: TrendingSound[];
  trending_hashtags: TrendingHashtag[];
  content_patterns: ContentPatterns;
  engagement_benchmarks?: Record<string, any>;
  viral_indicators?: Record<string, any>;
  recommendations?: Array<{
    type: string;
    action: string;
    rationale: string;
  }>;
  // NEW: LLM Segment Analysis
  segment_analysis?: {
    aggregated?: {
      customer_language_patterns?: {
        common_phrases?: string[];
        slang?: string[];
      };
      recommended_hook_types?: string[];
      top_pain_points?: Array<{ pain_point?: string; frequency?: number } | string>;
      trending_formats?: string[];
    };
    individual_videos?: Array<Record<string, any>>;
  };
}

// Hooks Library Types
export interface Hook {
  hook_text: string;
  hook_type: string;
  target_emotion: string;
  target_persona?: string;
  platform_fit: string[];
  pain_point_addressed?: string;
  verbatim_source?: string;
  strength_score: number;
  why_it_works?: string;
}

export interface HooksLibrary {
  brand: string;
  total_hooks: number;
  all_hooks: Hook[];
  by_type: Record<string, Hook[]>;
  by_emotion: Record<string, Hook[]>;
  by_platform: Record<string, Hook[]>;
  by_strength: Record<string, Hook[]>;
  type_distribution: Record<string, number>;
  emotion_distribution: Record<string, number>;
  platform_coverage: Record<string, number>;
  avg_strength: number;
  recommendations?: Array<{
    type: string;
    action: string;
    rationale: string;
  }>;
}

export interface Insight {
  id: number;
  session_id: number;
  brand_summary?: string;
  sentiment_score?: number;
  total_mentions?: number;
  top_positives?: string[];
  top_negatives?: string[];
  competitors_mentioned?: string[];
  market_pain_points?: string[];
  customer_language?: string[];
  customer_desires?: string[];
  trending_topics?: string[];
  icps?: ICP[];
  pain_points?: string[];
  value_props?: string[];
  messaging_angles?: MessagingAngle[];
  tone_emotions?: string[];
  content_insights?: string[];
  // Enhanced insights
  competitor_analysis?: CompetitorAnalysis;
  purchase_triggers?: string[];
  objections?: Objection[];
  decision_factors?: string[];
  verbatim_quotes?: VerbatimQuote[];
  content_opportunities?: string[];
  recommended_hooks?: RecommendedHook[];
  price_sensitivity?: PriceSensitivity;
  feature_requests?: string[];
  // Ad Library Insights
  ad_library_data?: Record<string, any>;
  competitor_ads_data?: Record<string, any>[];
  ad_creative_patterns?: AdCreativePatterns;
  landing_page_analysis?: Record<string, any>[];
  // Generated Content
  generated_scripts?: GeneratedScript[];
  thumbnail_suggestions?: ThumbnailSuggestion[];
  ab_test_suggestions?: ABTestSuggestion[];
  // Competitive Intelligence
  competitor_profiles?: CompetitorProfile[];
  competitive_matrix?: Record<string, any>;
  swot_analysis?: SWOTAnalysis;
  // Raw Data Summary
  data_summary?: DataSummary;
  top_quotes?: Array<{
    text: string;
    source?: string;
    source_url?: string;
    author?: string;
    engagement_score?: number;
    sentiment?: string;
  }>;
  data_by_topic?: Record<string, Record<string, any>[]>;
  // Cross-Source Insights
  cross_source_insights?: {
    validated_pain_points?: Array<{ pain_point: string; source_count: number; confidence: number; sources: string[] }>;
    consistent_praise?: Array<{ theme: string; sources: string[] }>;
    recurring_objections?: Array<{ objection: string; sources: string[] }>;
    messaging_gaps?: Array<{ gap: string; evidence: string }>;
    universal_themes?: Array<{ theme: string; sources: string[]; evidence_count: number }>;
    ai_validated_pain_points?: Array<{ pain_point: string; confidence: number; sources: string[]; evidence: string }>;
    key_opportunities?: string[];
    strategic_recommendations?: string[];
    ad_angle_suggestions?: string[];
    cross_source_sentiment?: Record<string, any>;
  };
  // TikTok Trends & Hooks Library (NEW)
  tiktok_trends?: TikTokTrends;
  hooks_library?: HooksLibrary;
  // Instagram Brand Presence (NEW)
  instagram_brand_presence?: {
    brand_voice?: string | {
      tone?: string;
      primary_tone?: string;
      characteristics?: string[];
    };
    visual_aesthetic?: {
      color_palette?: string[];
      style?: string;
      mood?: string;
    };
    content_pillars?: string[];
    messaging_themes?: string[];
    brand_archetype?: string;
    engagement_style?: string;
    hashtag_strategy?: string[];
    post_formats?: string[];
    caption_style?: string;
  };
  full_report?: string;
  created_at: string;
}

export interface ScrapedData {
  id: number;
  session_id: number;
  source_type: string;
  source_url?: string;
  track: number;
  title?: string;
  content?: string;
  author?: string;
  posted_at?: string;
  likes?: number;
  comments_count?: number;
  shares?: number;
  rating?: number;
  scraped_at: string;
  // Video fields
  video_file?: string;
  video_analysis?: {
    transcription?: string;
    hook?: string;
    key_message?: string;
    cta?: string;
    effectiveness?: number;
  };
  // Categorization
  mention_type?: string;
  sentiment?: string;
  sentiment_score?: number;
}

export interface FullResearchResult {
  brand: Brand;
  session: ResearchSession;
  scraped_data_count: number;
  scraped_data_by_source: Record<string, number>;
  insights?: Insight;
}

// API Functions

// Brands
export const createBrand = async (name: string, website_url?: string): Promise<Brand> => {
  const { data } = await api.post('/brands/', { name, website_url });
  return data;
};

export const listBrands = async (): Promise<Brand[]> => {
  const { data } = await api.get('/brands/');
  return data;
};

export const getBrand = async (id: number): Promise<Brand> => {
  const { data } = await api.get(`/brands/${id}`);
  return data;
};

export const deleteBrand = async (id: number): Promise<void> => {
  await api.delete(`/brands/${id}`);
};

// Research
export const startResearch = async (brand_id: number): Promise<ResearchSession> => {
  const { data } = await api.post('/research/start', { brand_id });
  return data;
};

export const getSession = async (session_id: number): Promise<ResearchSession> => {
  const { data } = await api.get(`/research/session/${session_id}`);
  return data;
};

export const getSessionProgress = async (session_id: number): Promise<ResearchProgress> => {
  const { data } = await api.get(`/research/session/${session_id}/progress`);
  return data;
};

export const getSessionData = async (
  session_id: number,
  source_type?: string,
  track?: number
): Promise<ScrapedData[]> => {
  const params = new URLSearchParams();
  if (source_type) params.append('source_type', source_type);
  if (track) params.append('track', track.toString());

  const { data } = await api.get(`/research/session/${session_id}/data?${params}`);
  return data;
};

export const getSessionInsights = async (session_id: number): Promise<Insight> => {
  const { data } = await api.get(`/research/session/${session_id}/insights`);
  return data;
};

export const getFullResearchResult = async (session_id: number): Promise<FullResearchResult> => {
  const { data } = await api.get(`/research/session/${session_id}/full`);
  return data;
};

export interface SentimentAnalysis {
  session_id: number;
  total: number;
  overall: Record<string, number>;
  overall_pct: Record<string, number>;
  by_source: Record<string, { positive: number; negative: number; neutral: number; total: number; avg_score: number }>;
  top_positive: Array<{ content: string; source: string; score: number; author?: string; title?: string }>;
  top_negative: Array<{ content: string; source: string; score: number; author?: string; title?: string }>;
  model: string;
}

export const getSentimentAnalysis = async (session_id: number): Promise<SentimentAnalysis> => {
  const { data } = await api.get(`/research/session/${session_id}/sentiment`);
  return data;
};

export const getBrandSessions = async (brand_id: number): Promise<ResearchSession[]> => {
  const { data } = await api.get(`/research/brand/${brand_id}/sessions`);
  return data;
};

// Enhanced Ad Analysis Types
export interface SceneBreakdown {
  scene_number: number;
  timestamp_start?: string;
  timestamp_end?: string;
  duration_seconds?: number;
  visual_description?: string;
  audio_transcript?: string;
  on_screen_text?: string;
  scene_type?: string;
}

export interface HookAnalysis {
  hook_type?: string;
  hook_strength?: number;
  hook_text?: string;
  hook_technique?: string;
  attention_device?: string;
}

export interface CreativeDimensions {
  framework?: string;
  pacing?: string;
  proof_type?: string;
  emotions?: string[];
  cta_type?: string;
  cta_text?: string;
  tone?: string;
  style?: string;
  production_quality?: string;
}

export interface AdCreativeAnalysis {
  transcription?: string;
  hook?: string;
  hook_type?: string;
  hook_strength?: number;
  framework?: string;
  target_emotion?: string;
  cta?: string;
  effectiveness?: number;
  key_messages?: string[];
  visual_elements?: string[];
  // Enhanced analysis fields
  scene_breakdown?: SceneBreakdown[];
  hook_analysis?: HookAnalysis;
  creative_dimensions?: CreativeDimensions;
  disclaimers?: string[];
  full_copy?: string;
  audio_transcript?: string;
  // Data provenance for generated content
  based_on_verbatims?: string[];
  pain_points_addressed?: string[];
  source_insights?: string[];
}

export interface LogEntry {
  timestamp: string;
  level: 'info' | 'success' | 'warning' | 'error';
  message: string;
  source?: string;
  details?: Record<string, any>;
}

export interface SessionLogs {
  session_id: number;
  logs: LogEntry[];
  total_count: number;
}

// Logs API
export const getSessionLogs = async (session_id: number, since?: string): Promise<SessionLogs> => {
  const params = new URLSearchParams();
  if (since) params.append('since', since);

  const { data } = await api.get(`/research/session/${session_id}/logs?${params}`);
  return data;
};


// Chat API Types
export interface ChatMessage {
  message: string;
  session_id?: number;
  brand_id?: number;
}

export interface ChatResponse {
  response: string;
  sources: Array<Record<string, any>>;
  timestamp: string;
  error?: string;
  message_ids?: { user?: number; assistant?: number };
}

export interface Verbatim {
  quote: string;
  source: string;
  sentiment?: string;
  author?: string;
  url?: string;
}

// Chat API Functions
export const sendChatMessage = async (message: ChatMessage): Promise<ChatResponse> => {
  const { data } = await api.post('/chat', message);
  return data;
};

export const generateScript = async (
  session_id: number,
  prompt: string = '',
  style: string = 'ugc'
): Promise<{ script: string; style: string; session_id: number }> => {
  const { data } = await api.post('/chat/generate-script', {
    session_id,
    prompt,
    style
  });
  return data;
};

export const findVerbatims = async (
  session_id: number,
  topic: string = '',
  sentiment: string = 'any',
  limit: number = 10
): Promise<{ verbatims: Verbatim[]; count: number }> => {
  const { data } = await api.post('/chat/find-verbatims', {
    session_id,
    topic,
    sentiment,
    limit
  });
  return data;
};

export const getChatSuggestions = async (session_id?: number): Promise<{ suggestions: string[] }> => {
  const params = session_id ? `?session_id=${session_id}` : '';
  const { data } = await api.get(`/chat/suggestions${params}`);
  return data;
};

export const clearChatHistory = async (session_id?: number, brand_id?: number): Promise<{ success: boolean }> => {
  const { data } = await api.post('/chat/clear', { session_id, brand_id });
  return data;
};

export interface ChatHistoryMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface ChatHistoryResponse {
  session_id: number;
  messages: ChatHistoryMessage[];
  count: number;
}

export const getChatHistory = async (session_id: number): Promise<ChatHistoryResponse> => {
  const { data } = await api.get(`/chat/history?session_id=${session_id}`);
  return data;
};

export interface SaveInsightRequest {
  session_id: number;
  brand_id: number;
  question: string;
  answer: string;
  label: string;
}

export interface SaveInsightResponse {
  success: boolean;
  message: string;
  knowledge_id: number;
  label: string;
}

export const saveInsight = async (payload: SaveInsightRequest): Promise<SaveInsightResponse> => {
  const { data } = await api.post('/chat/save-insight', payload);
  return data;
};

export interface BrandKnowledge {
  id: number;
  question: string;
  answer: string;
  label: string;
  source_session_id?: number;
  saved_at: string;
}

export interface BrandKnowledgeResponse {
  brand_id: number;
  knowledge: BrandKnowledge[];
  count: number;
}

export const getBrandKnowledge = async (brand_id: number): Promise<BrandKnowledgeResponse> => {
  const { data } = await api.get(`/brand/${brand_id}/knowledge`);
  return data;
};

// AnythingLLM RAG Chat
export interface RAGChatMessage {
  message: string;
  workspace?: string;  // Optional - workspace slug in AnythingLLM
  session_id?: number;  // Optional - session ID to auto-detect workspace
}

export interface RAGChatResponse {
  response: string;
  sources: Array<Record<string, any>>;
  success: boolean;
  error?: string;
  workspace?: string;
  brand_name?: string;
}

export const sendRAGMessage = async (message: RAGChatMessage): Promise<RAGChatResponse> => {
  const { data } = await api.post('/chat/rag', message);
  return data;
};

export const getRAGWorkspaces = async (): Promise<{ workspaces: Array<{ name: string; slug: string }> }> => {
  const { data } = await api.get('/chat/rag/workspaces');
  return data;
};


// ==========================================
// Idea Bank API
// ==========================================

export interface SavedIdea {
  id: number;
  brand_id?: number;
  session_id?: number;
  idea_type: string;
  title?: string;
  content: string;
  hook_type?: string;
  target_emotion?: string;
  target_persona?: string;
  platform_fit?: string[];
  strength_score?: number;
  source?: string;
  source_detail?: string;
  tags?: string[];
  notes?: string;
  is_favorite: boolean;
  created_at: string;
  updated_at: string;
}

export interface IdeaCreate {
  brand_id?: number;
  session_id?: number;
  idea_type: string;
  title?: string;
  content: string;
  hook_type?: string;
  target_emotion?: string;
  target_persona?: string;
  platform_fit?: string[];
  strength_score?: number;
  source?: string;
  source_detail?: string;
  tags?: string[];
  notes?: string;
}

export interface IdeaUpdate {
  title?: string;
  content?: string;
  hook_type?: string;
  target_emotion?: string;
  target_persona?: string;
  platform_fit?: string[];
  strength_score?: number;
  tags?: string[];
  notes?: string;
  is_favorite?: boolean;
}

export interface IdeaBankStats {
  total_ideas: number;
  favorites: number;
  by_type: Record<string, number>;
  by_brand: Record<string, number>;
}

// Idea Bank API functions

export const createIdea = async (idea: IdeaCreate): Promise<SavedIdea> => {
  const { data } = await api.post('/ideas/', idea);
  return data;
};

export const listIdeas = async (params?: {
  idea_type?: string;
  brand_id?: number;
  is_favorite?: boolean;
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<SavedIdea[]> => {
  const queryParams = new URLSearchParams();
  if (params?.idea_type) queryParams.append('idea_type', params.idea_type);
  if (params?.brand_id) queryParams.append('brand_id', params.brand_id.toString());
  if (params?.is_favorite !== undefined) queryParams.append('is_favorite', params.is_favorite.toString());
  if (params?.search) queryParams.append('search', params.search);
  if (params?.limit) queryParams.append('limit', params.limit.toString());
  if (params?.offset) queryParams.append('offset', params.offset.toString());

  const { data } = await api.get(`/ideas/?${queryParams}`);
  return data;
};

export const getIdea = async (id: number): Promise<SavedIdea> => {
  const { data } = await api.get(`/ideas/${id}`);
  return data;
};

export const updateIdea = async (id: number, update: IdeaUpdate): Promise<SavedIdea> => {
  const { data } = await api.put(`/ideas/${id}`, update);
  return data;
};

export const deleteIdea = async (id: number): Promise<void> => {
  await api.delete(`/ideas/${id}`);
};

export const toggleIdeaFavorite = async (id: number): Promise<SavedIdea> => {
  const { data } = await api.post(`/ideas/${id}/favorite`);
  return data;
};

export const getIdeasByBrand = async (brandId: number, ideaType?: string): Promise<SavedIdea[]> => {
  const params = ideaType ? `?idea_type=${ideaType}` : '';
  const { data } = await api.get(`/ideas/by-brand/${brandId}${params}`);
  return data;
};

export const getIdeasByType = async (ideaType: string, limit?: number): Promise<SavedIdea[]> => {
  const params = limit ? `?limit=${limit}` : '';
  const { data } = await api.get(`/ideas/by-type/${ideaType}${params}`);
  return data;
};

export const getIdeaBankStats = async (): Promise<IdeaBankStats> => {
  const { data } = await api.get('/ideas/stats/summary');
  return data;
};
