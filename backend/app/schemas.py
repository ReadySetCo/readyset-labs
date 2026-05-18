"""
Pydantic schemas for API request/response validation.
"""

from pydantic import BaseModel, Field, HttpUrl, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============ Enums ============

class ResearchStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    # Legacy status values from older sessions
    TIMEOUT = "timeout"
    ERROR = "error"
    RUNNING = "running"


class SourceType(str, Enum):
    WEBSITE = "website"
    REDDIT = "reddit"
    TWITTER = "twitter"
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    AMAZON = "amazon"
    GOOGLE = "google"
    TRUSTPILOT = "trustpilot"
    FORUM = "forum"
    NEWS_BLOG = "news_blog"
    COMPETITOR_COMPARISON = "competitor_comparison"
    G2 = "g2"
    CAPTERRA = "capterra"


class MentionType(str, Enum):
    DIRECT_BRAND = "direct_brand"
    SEGMENT_DISCUSSION = "segment_discussion"
    COMPETITOR_MENTION = "competitor_mention"
    PROBLEM_DISCUSSION = "problem_discussion"


class Track(int, Enum):
    BRAND_MENTIONS = 1
    SEGMENT_RESEARCH = 2


# ============ Brand Schemas ============

class BrandCreate(BaseModel):
    """Schema for creating a new brand."""
    name: str = Field(..., min_length=1, max_length=255, description="Brand name")
    website_url: Optional[str] = Field(None, description="Brand website URL")
    ad_library_url: Optional[str] = Field(
        None,
        description="Direct Ad Library URL (overrides auto-discovery). "
        "Paste the URL the user sees in the browser for this advertiser, "
        "e.g. https://www.facebook.com/ads/library/?view_all_page_id=...",
    )

    @field_validator("website_url", "ad_library_url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v.strip() == "":
            return None
        v = v.strip()
        # Must start with http:// or https://
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class SocialMediaURLs(BaseModel):
    """Social media URLs for a brand."""
    twitter: Optional[str] = None
    instagram: Optional[str] = None
    linkedin: Optional[str] = None
    facebook: Optional[str] = None
    tiktok: Optional[str] = None
    youtube: Optional[str] = None


class ProductDescription(BaseModel):
    """Product with description."""
    name: str
    description: Optional[str] = None


class BrandResponse(BaseModel):
    """Schema for brand response."""
    id: int
    name: str
    website_url: Optional[str]
    ad_library_url: Optional[str] = None
    description: Optional[str]
    sector: Optional[str]
    vertical: Optional[str]
    products: Optional[List[str]]
    target_audience: Optional[str]

    # Brand DNA fields
    brand_colors: Optional[List[str]] = None
    tagline: Optional[str] = None
    brand_values: Optional[List[str]] = None
    brand_aesthetic: Optional[List[str]] = None
    tone_of_voice: Optional[List[str]] = None
    logo_url: Optional[str] = None
    fonts: Optional[List[str]] = None
    brand_images: Optional[List[Any]] = None  # Can be strings or dicts with 'original_url'
    social_media_urls: Optional[Dict[str, str]] = None
    product_descriptions: Optional[List[Dict[str, str]]] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BrandDiscoveryResult(BaseModel):
    """Result of brand discovery phase."""
    brand_id: int
    name: str
    description: str
    sector: str
    vertical: str
    products: List[str]
    target_audience: str
    website_content_summary: str


# ============ Research Session Schemas ============

class ResearchSessionCreate(BaseModel):
    """Schema for starting a new research session."""
    brand_id: int


class ResearchSessionResponse(BaseModel):
    """Schema for research session response."""
    id: int
    brand_id: int
    status: ResearchStatus
    started_at: datetime
    completed_at: Optional[datetime]
    brand_queries: Optional[Dict[str, Any]]
    segment_queries: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


# ============ Query Generation Schemas ============

class GeneratedQueries(BaseModel):
    """Generated search queries for both tracks."""
    
    # Track 1: Brand Mentions
    brand_queries: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Queries for finding brand mentions"
    )
    
    # Track 2: Segment Research
    segment_queries: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Queries for segment/market research"
    )


class QueryGenerationInput(BaseModel):
    """Input for query generation."""
    brand_name: str
    sector: str
    vertical: str
    products: List[str]
    target_audience: str


# ============ Scraped Data Schemas ============

class ScrapedDataCreate(BaseModel):
    """Schema for creating scraped data entry."""
    session_id: int
    source_type: SourceType
    source_url: Optional[str]
    track: Track
    title: Optional[str]
    content: Optional[str]
    author: Optional[str]
    posted_at: Optional[datetime]
    likes: Optional[int]
    comments_count: Optional[int]
    shares: Optional[int]
    rating: Optional[float]
    raw_data: Optional[Dict[str, Any]]


class ScrapedDataResponse(BaseModel):
    """Schema for scraped data response."""
    id: int
    session_id: int
    source_type: str
    source_url: Optional[str]
    track: int
    title: Optional[str]
    content: Optional[str]
    author: Optional[str]
    posted_at: Optional[datetime]
    likes: Optional[int]
    comments_count: Optional[int]
    shares: Optional[int]
    rating: Optional[float]
    # Enhanced categorization
    mention_type: Optional[str]
    sentiment: Optional[str]
    sentiment_score: Optional[float]
    relevance_score: Optional[float]
    detected_topics: Optional[List[str]]
    scraped_at: datetime

    class Config:
        from_attributes = True


# ============ Insight Schemas ============

class ICP(BaseModel):
    """Ideal Customer Profile."""
    name: str
    description: str
    age_range: Optional[str]
    characteristics: List[str]


class MessagingAngle(BaseModel):
    """A messaging angle for ads."""
    name: str
    hook: str
    description: str


class InsightResponse(BaseModel):
    """Schema for insights response."""
    id: int
    session_id: int
    
    # Summary
    brand_summary: Optional[str]
    sentiment_score: Optional[float]
    total_mentions: Optional[int]
    
    # Track 1 insights
    top_positives: Optional[List[str]]
    top_negatives: Optional[List[str]]
    competitors_mentioned: Optional[List[str]]
    
    # Track 2 insights
    market_pain_points: Optional[List[str]]
    customer_language: Optional[List[str]]
    customer_desires: Optional[List[str]]
    trending_topics: Optional[List[str]]
    
    # Creative Dimensions
    icps: Optional[List[Dict[str, Any]]]
    pain_points: Optional[List[str]]
    value_props: Optional[List[str]]
    messaging_angles: Optional[List[Dict[str, Any]]]
    tone_emotions: Optional[List[str]]
    content_insights: Optional[List[str]]
    
    # Enhanced insights
    competitor_analysis: Optional[Dict[str, Any]]
    purchase_triggers: Optional[List[str]]
    objections: Optional[List[Dict[str, Any]]]
    decision_factors: Optional[List[str]]
    verbatim_quotes: Optional[List[Dict[str, Any]]]
    content_opportunities: Optional[List[str]]
    recommended_hooks: Optional[List[Dict[str, Any]]]
    price_sensitivity: Optional[Dict[str, Any]]
    feature_requests: Optional[List[str]]
    
    # Ad Library Insights (NEW)
    ad_library_data: Optional[Dict[str, Any]]
    competitor_ads_data: Optional[List[Dict[str, Any]]]
    ad_creative_patterns: Optional[Dict[str, Any]]
    landing_page_analysis: Optional[List[Dict[str, Any]]]
    
    # Generated Content (NEW)
    generated_scripts: Optional[List[Dict[str, Any]]]
    thumbnail_suggestions: Optional[List[Dict[str, Any]]]
    ab_test_suggestions: Optional[List[Dict[str, Any]]]
    
    # Competitive Intelligence (NEW)
    competitor_profiles: Optional[List[Dict[str, Any]]]
    competitive_matrix: Optional[Dict[str, Any]]
    swot_analysis: Optional[Dict[str, Any]]
    
    # Raw Data Summary (NEW)
    data_summary: Optional[Dict[str, Any]]
    top_quotes: Optional[List[Dict[str, Any]]]
    data_by_topic: Optional[Dict[str, List[Dict[str, Any]]]]
    cross_source_insights: Optional[Dict[str, Any]]
    
    # Platform-specific insights
    tiktok_trends: Optional[Dict[str, Any]] = None
    instagram_brand_presence: Optional[Dict[str, Any]] = None
    hooks_library: Optional[Dict[str, Any]] = None
    
    # Proto-ICPs (Voice of Customer clustering)
    proto_icps: Optional[List[Dict[str, Any]]]
    proto_icp_recommendations: Optional[List[Dict[str, Any]]]
    proto_icp_stats: Optional[Dict[str, Any]]

    # Creative Target Personas (CTP) — added after session 134 showed the
    # frontend tabs were empty because these fields weren't in the response
    # schema, so Pydantic was silently dropping them.
    ctp_data: Optional[List[Dict[str, Any]]] = None
    ctp_hypothesis: Optional[List[Dict[str, Any]]] = None
    ctp_stats: Optional[Dict[str, Any]] = None
    # Target Personas (April 2026) — prospects, not customers. Schwartz
    # Unaware/Problem-Aware/Solution-Aware. Distinct from ctp_data.
    target_personas: Optional[List[Dict[str, Any]]] = None

    # Fase 3 generators
    ugc_briefs: Optional[List[Dict[str, Any]]] = None
    funnel_strategy: Optional[Dict[str, Any]] = None
    post_purchase_survey: Optional[Dict[str, Any]] = None

    # Strategic angles (P0.1 — restored from llm/prompts.py)
    failed_solution_angles: Optional[List[Dict[str, Any]]] = None
    transformation_angles: Optional[List[Dict[str, Any]]] = None
    weak_signals: Optional[List[Dict[str, Any]]] = None
    community_dialect: Optional[List[Any]] = None

    # Full report
    full_report: Optional[str]

    created_at: datetime

    class Config:
        from_attributes = True


# ============ Full Research Result ============

class FullResearchResult(BaseModel):
    """Complete research result with all data."""
    brand: BrandResponse
    session: ResearchSessionResponse
    scraped_data_count: int
    scraped_data_by_source: Dict[str, int]
    insights: Optional[InsightResponse]


# ============ API Response Wrappers ============

class APIResponse(BaseModel):
    """Generic API response wrapper."""
    success: bool
    message: str
    data: Optional[Any] = None


class ResearchProgress(BaseModel):
    """Progress update for research session."""
    session_id: int
    status: ResearchStatus
    current_step: str
    current_phase: str  # brand_dna, discovery, keywords, scraping, ad_library, competitors, insights
    progress_percent: int
    sources_completed: List[str]
    sources_pending: List[str]
    estimated_time_remaining: Optional[int] = None  # seconds


class BrandDNA(BaseModel):
    """Brand DNA extracted from website (Pomelli-style)."""
    brand_colors: List[str] = []
    tagline: Optional[str] = None
    brand_values: List[str] = []
    brand_aesthetic: List[str] = []
    tone_of_voice: List[str] = []
    logo_url: Optional[str] = None
    fonts: List[str] = []
    brand_images: List[Any] = []  # Can be strings or dicts with 'original_url'
    social_media_urls: Dict[str, str] = {}
    product_descriptions: List[Dict[str, str]] = []
    business_overview: Optional[str] = None

