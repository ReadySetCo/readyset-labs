"""
SQLAlchemy models for Brand Intelligence Scraper.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

Base = declarative_base()


class Brand(Base):
    """Brand being researched."""
    __tablename__ = "brands"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    website_url = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    sector = Column(String(255), nullable=True)
    vertical = Column(String(255), nullable=True)
    products = Column(JSON, nullable=True)  # List of products
    target_audience = Column(Text, nullable=True)
    
    # Brand DNA fields (Pomelli-style)
    brand_colors = Column(JSON, nullable=True)  # ["#002432", "#0070c9", ...]
    tagline = Column(String(500), nullable=True)  # Brand slogan/tagline
    brand_values = Column(JSON, nullable=True)  # ["Transparency", "Innovation", ...]
    brand_aesthetic = Column(JSON, nullable=True)  # ["modern", "clean", "digital", ...]
    tone_of_voice = Column(JSON, nullable=True)  # ["Empathetic", "Informative", ...]
    logo_url = Column(String(1000), nullable=True)  # URL to brand logo
    fonts = Column(JSON, nullable=True)  # ["Inter", "Helvetica", ...]
    brand_images = Column(JSON, nullable=True)  # URLs of representative brand images
    social_media_urls = Column(JSON, nullable=True)  # {"twitter": "...", "instagram": "...", ...}
    ad_library_page_id = Column(String(50), nullable=True)  # Facebook Ad Library page ID (e.g., "645468212198661")
    product_descriptions = Column(JSON, nullable=True)  # [{"name": "Product A", "description": "..."}]
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    research_sessions = relationship("ResearchSession", back_populates="brand")


class ResearchSession(Base):
    """A research session for a brand."""
    __tablename__ = "research_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    status = Column(String(50), default="pending")  # pending, in_progress, completed, failed
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
    
    # Generated queries for scraping
    brand_queries = Column(JSON, nullable=True)  # Track 1 queries
    segment_queries = Column(JSON, nullable=True)  # Track 2 queries
    
    # Relationships
    brand = relationship("Brand", back_populates="research_sessions")
    scraped_data = relationship("ScrapedData", back_populates="session")
    insights = relationship("Insight", back_populates="session")


class ScrapedData(Base):
    """Raw scraped data from various sources."""
    __tablename__ = "scraped_data"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("research_sessions.id"), nullable=False)
    
    # Source information
    source_type = Column(String(50), nullable=False)  # reddit, twitter, tiktok, instagram, amazon, google, trustpilot, forum, website, news_blog, competitor_comparison
    source_url = Column(String(1000), nullable=True)
    track = Column(Integer, nullable=False)  # 1 = brand mentions, 2 = segment research
    
    # Content
    title = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    author = Column(String(255), nullable=True)
    posted_at = Column(DateTime, nullable=True)
    
    # Metrics
    likes = Column(Integer, nullable=True)
    comments_count = Column(Integer, nullable=True)
    shares = Column(Integer, nullable=True)
    rating = Column(Float, nullable=True)  # For reviews
    
    # NEW: Enhanced categorization
    mention_type = Column(String(50), nullable=True)  # direct_brand, segment_discussion, competitor_mention, problem_discussion
    sentiment = Column(String(20), nullable=True)  # positive, negative, neutral
    sentiment_score = Column(Float, nullable=True)  # -1.0 to 1.0
    relevance_score = Column(Float, nullable=True)  # 0.0 to 1.0
    detected_topics = Column(JSON, nullable=True)  # List of topics: pain_points, features, pricing, support, etc.
    
    # Video analysis (for TikTok/Instagram)
    video_analysis = Column(JSON, nullable=True)  # Gemini analysis: transcription, hook, key_message, etc.
    video_file = Column(String(500), nullable=True)  # Path to downloaded video file
    
    # === INTAKE ENGINE: Snippet Tagging (per brief) ===
    # Primary Trigger - "Why they start searching now"
    primary_trigger = Column(String(255), nullable=True)
    
    # Blocker Type - Friction ("can't") vs Objection ("won't")
    blocker_type = Column(String(50), nullable=True)  # friction, objection, none
    
    # Desired Outcome Level - Functional / Emotional / Identity
    desired_outcome_level = Column(String(50), nullable=True)  # functional, emotional, identity
    
    # Proof Type Trusted - What evidence they trust
    proof_type_trusted = Column(String(100), nullable=True)  # vet_science, reviews_ugc, transparency, price_math, certifications, before_after
    
    # Language detection
    language = Column(String(10), nullable=True)  # en, es, etc.
    
    # Validation Level per brief (1-5)
    # 1=Scraped, 2=Client Provided, 3=Client Validated, 4=Creative Hypothesis, 5=Performance Validated
    validation_level = Column(Integer, default=1)
    
    # Classification confidence score (0.0 - 1.0)
    classification_confidence = Column(Float, nullable=True)
    
    # Language cues (repeated phrases, slang, emotional words)
    language_cues = Column(JSON, nullable=True)

    # General Stance (CTP classification)
    general_stance = Column(String(100), nullable=True)  # fatalist, skeptic, bio_hacker, etc.
    stance_confidence = Column(Float, nullable=True)  # 0.0 - 1.0

    # Raw data
    raw_data = Column(JSON, nullable=True)
    
    scraped_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    session = relationship("ResearchSession", back_populates="scraped_data")


class Insight(Base):
    """Generated insights and Creative Dimensions."""
    __tablename__ = "insights"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("research_sessions.id"), nullable=False)
    
    # Brand summary
    brand_summary = Column(Text, nullable=True)
    sentiment_score = Column(Float, nullable=True)
    total_mentions = Column(Integer, nullable=True)
    
    # Track 1 insights (Brand Mentions)
    top_positives = Column(JSON, nullable=True)
    top_negatives = Column(JSON, nullable=True)
    competitors_mentioned = Column(JSON, nullable=True)
    
    # Track 2 insights (Segment Research)
    market_pain_points = Column(JSON, nullable=True)
    customer_language = Column(JSON, nullable=True)
    customer_desires = Column(JSON, nullable=True)
    trending_topics = Column(JSON, nullable=True)
    
    # Creative Dimensions
    icps = Column(JSON, nullable=True)  # Ideal Customer Profiles
    pain_points = Column(JSON, nullable=True)
    value_props = Column(JSON, nullable=True)
    messaging_angles = Column(JSON, nullable=True)
    tone_emotions = Column(JSON, nullable=True)
    content_insights = Column(JSON, nullable=True)  # From TikTok/IG
    
    # Enhanced insights
    competitor_analysis = Column(JSON, nullable=True)  # Detailed competitor comparison
    purchase_triggers = Column(JSON, nullable=True)  # What makes people buy
    objections = Column(JSON, nullable=True)  # Common objections to address
    decision_factors = Column(JSON, nullable=True)  # Key decision factors
    verbatim_quotes = Column(JSON, nullable=True)  # Real quotes for ads
    content_opportunities = Column(JSON, nullable=True)  # Content gaps to fill
    recommended_hooks = Column(JSON, nullable=True)  # Suggested ad hooks
    price_sensitivity = Column(JSON, nullable=True)  # Price-related insights
    feature_requests = Column(JSON, nullable=True)  # What users want
    
    # Ad Library Insights (NEW)
    ad_library_data = Column(JSON, nullable=True)  # Brand's ads data
    competitor_ads_data = Column(JSON, nullable=True)  # Competitor ads data
    ad_creative_patterns = Column(JSON, nullable=True)  # Aggregated creative patterns
    landing_page_analysis = Column(JSON, nullable=True)  # LP analysis
    
    # Generated Content (NEW)
    generated_scripts = Column(JSON, nullable=True)  # AI-generated ad scripts
    thumbnail_suggestions = Column(JSON, nullable=True)  # First frame ideas
    ab_test_suggestions = Column(JSON, nullable=True)  # Test recommendations
    
    # Competitive Intelligence (NEW)
    competitor_profiles = Column(JSON, nullable=True)  # Detailed competitor info
    competitive_matrix = Column(JSON, nullable=True)  # Comparison matrix
    swot_analysis = Column(JSON, nullable=True)  # SWOT analysis
    
    # Raw Data Summary (NEW)
    data_summary = Column(JSON, nullable=True)  # Stats by source
    top_quotes = Column(JSON, nullable=True)  # Best quotes for ads
    data_by_topic = Column(JSON, nullable=True)  # Data categorized by topic
    cross_source_insights = Column(JSON, nullable=True)  # Patterns across multiple sources
    
    # TikTok Trends (NEW)
    tiktok_trends = Column(JSON, nullable=True)  # Trending sounds, hashtags, content patterns
    
    # Instagram Brand Presence (NEW)
    instagram_brand_presence = Column(JSON, nullable=True)  # Brand voice, visual aesthetic, content pillars
    
    # Hooks Library (NEW)
    hooks_library = Column(JSON, nullable=True)  # Structured hooks library for creative briefs
    
    # Proto-ICPs (Voice of Customer clustering)
    proto_icps = Column(JSON, nullable=True)  # Clustered ICP candidates
    proto_icp_recommendations = Column(JSON, nullable=True)  # Top 3 recommended
    proto_icp_stats = Column(JSON, nullable=True)  # Summary stats

    # Creative Target Personas (CTP) - grouped by General Stance
    ctp_data = Column(JSON, nullable=True)  # Full CTP structures list
    ctp_hypothesis = Column(JSON, nullable=True)  # Hypothesis layer per CTP
    ctp_stats = Column(JSON, nullable=True)  # Summary stats

    # Full report
    full_report = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    session = relationship("ResearchSession", back_populates="insights")


class SavedIdea(Base):
    """
    Idea Bank - Save hooks, scripts, and other creative ideas for later use.
    
    This allows users to build a library of their favorite creative ideas
    across multiple research sessions.
    """
    __tablename__ = "saved_ideas"
    
    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True)  # Optional brand association
    session_id = Column(Integer, ForeignKey("research_sessions.id"), nullable=True)  # Source session
    
    # Idea type and content
    idea_type = Column(String(50), nullable=False)  # hook, script, thumbnail, angle, quote
    title = Column(String(255), nullable=True)  # Optional title/name
    content = Column(Text, nullable=False)  # The actual idea content
    
    # Metadata
    hook_type = Column(String(50), nullable=True)  # question, statement, story, etc.
    target_emotion = Column(String(50), nullable=True)  # curiosity, fear, hope, etc.
    target_persona = Column(String(255), nullable=True)  # Which ICP this targets
    platform_fit = Column(JSON, nullable=True)  # ["TikTok", "Instagram"]
    strength_score = Column(Integer, nullable=True)  # 1-5 rating
    
    # Source tracking
    source = Column(String(100), nullable=True)  # generated, scraped, manual
    source_detail = Column(Text, nullable=True)  # Additional source info (verbatim quote, etc.)
    
    # Organization
    tags = Column(JSON, nullable=True)  # User-defined tags
    notes = Column(Text, nullable=True)  # User notes
    is_favorite = Column(Boolean, default=False)  # Star/favorite marker
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    brand = relationship("Brand", backref="saved_ideas")
    session = relationship("ResearchSession", backref="saved_ideas")


class ChatMessage(Base):
    """Persistent chat message history."""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("research_sessions.id"), nullable=False)
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    session = relationship("ResearchSession", backref="chat_messages")


class BrandKnowledge(Base):
    """Brand-level accumulated knowledge from chat insights."""
    __tablename__ = "brand_knowledge"

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("research_sessions.id"), nullable=True)  # Source session for traceability

    # The original question and answer
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)

    # User-provided label for this insight
    label = Column(String(255), nullable=False)

    # Timestamps
    saved_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    brand = relationship("Brand", backref="brand_knowledge")
    session = relationship("ResearchSession", backref="brand_knowledge")

