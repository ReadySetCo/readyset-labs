"""
Configuration module for Brand Intelligence Scraper.
Loads environment variables and provides settings.
"""

from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path
import os

# Absolute path to backend/ directory so the DB is found regardless of cwd
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_DEFAULT_DB_URL = f"sqlite+aiosqlite:///{_BACKEND_DIR / 'database.db'}"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App settings
    APP_NAME: str = "Brand Intelligence Scraper"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = _DEFAULT_DB_URL
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"  # Will use gpt-5.1 when available in API
    
    # Google Gemini
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"  # Stable, 1M context, 65K output
    GEMINI_CHAT_MODEL: str = "gemini-2.5-flash"  # Model for chat (needs large context)
    
    # Default LLM provider: "openai" or "gemini"
    LLM_PROVIDER: str = "openai"

    # Task-specific LLM routing
    LLM_MODEL_STRATEGY: str = "gpt-5.4"
    LLM_MODEL_CREATIVE: str = "gpt-5.4"
    LLM_MODEL_CHAT: str = "gpt-5.4"
    LLM_MODEL_CLASSIFIER: str = "gemini-2.5-flash"
    LLM_MODEL_VISION: str = "models/gemini-3-flash-preview"
    LLM_MODEL_VISION_FALLBACK: str = "gemini-2.5-flash"

    # Legacy AnythingLLM sync is disabled by default. Chat now uses the direct
    # long-context service over stored research data.
    ENABLE_ANYTHINGLLM_SYNC: bool = False
    
    # Firecrawl
    FIRECRAWL_API_KEY: Optional[str] = None
    FIRECRAWL_BASE_URL: str = "https://api.firecrawl.dev/v1"
    
    # Apify
    APIFY_API_TOKEN: Optional[str] = None
    
    # Instagram credentials (for instaloader - optional)
    INSTAGRAM_USERNAME: Optional[str] = None
    INSTAGRAM_PASSWORD: Optional[str] = None
    
    # Scraping settings
    MAX_POSTS_PER_SOURCE: int = 100  # Increased for more data volume
    MAX_REVIEWS_PER_SOURCE: int = 50  # Reduced to save API costs
    SCRAPE_TIMEOUT: int = 20  # seconds - reduced from 120 to prevent hangs
    
    # Apify cost control - disable expensive actors by default
    # Google Places costs ~$0.05-0.10 per place, which adds up FAST
    APIFY_ENABLE_GOOGLE_PLACES: bool = False  # DISABLED - too expensive ($60 of $100 budget)
    APIFY_ENABLE_AMAZON_REVIEWS: bool = True
    APIFY_ENABLE_SOCIAL_SCRAPERS: bool = True  # Twitter, TikTok, Instagram, Facebook
    APIFY_MAX_GOOGLE_PLACES: int = 3  # If enabled, max 3 places to limit cost
    
    # Ad Library settings - Apify cost is ~$0.20 per 1000 ads (very cheap)
    AD_LIBRARY_MAX_ADS: int = 100  # Brand ads to scrape
    AD_LIBRARY_MAX_BRAND_VIDEOS: int = 30  # Max unique video ads to analyze for brand
    AD_LIBRARY_MAX_BRAND_STATICS: int = 20  # Max unique static/image ads to analyze for brand
    AD_LIBRARY_MAX_COMPETITOR_ADS: int = 60  # TOTAL competitor ads across all competitors
    AD_LIBRARY_MAX_COMP_VIDEOS: int = 10  # Max video ads per competitor
    AD_LIBRARY_MAX_COMP_STATICS: int = 10  # Max static ads per competitor
    AD_LIBRARY_MAX_COMPETITORS: int = 3  # Max competitors to analyze
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings

