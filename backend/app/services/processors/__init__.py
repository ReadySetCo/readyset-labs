# -*- coding: utf-8 -*-
"""Processors package for Knowledge Synthesizer."""

from .base import BaseProcessor
from .review_processor import ReviewProcessor
from .social_processor import SocialProcessor
from .discussion_processor import DiscussionProcessor
from .video_processor import VideoProcessor
from .article_processor import ArticleProcessor
from .competitive_processor import CompetitiveProcessor
from .brand_processor import BrandProcessor
from .adlibrary_processor import AdLibraryProcessor

__all__ = [
    'BaseProcessor',
    'ReviewProcessor',
    'SocialProcessor', 
    'DiscussionProcessor',
    'VideoProcessor',
    'ArticleProcessor',
    'CompetitiveProcessor',
    'BrandProcessor',
    'AdLibraryProcessor',
]

# Mapping of source_type to processor class
PROCESSOR_MAP = {
    # Reviews
    'google_reviews': ReviewProcessor,
    'trustpilot': ReviewProcessor,
    'app_store': ReviewProcessor,
    'play_store': ReviewProcessor,
    'g2': ReviewProcessor,
    'capterra': ReviewProcessor,
    'product_hunt': ReviewProcessor,
    'yelp': ReviewProcessor,
    'amazon': ReviewProcessor,
    'other_review': ReviewProcessor,
    
    # Social
    'twitter': SocialProcessor,
    'instagram': SocialProcessor,
    'linkedin': SocialProcessor,
    'tiktok': SocialProcessor,
    'instagram_profile': SocialProcessor,
    
    # Discussions
    'reddit': DiscussionProcessor,
    'forum': DiscussionProcessor,
    'quora': DiscussionProcessor,
    'youtube_comment': DiscussionProcessor,
    'segment_discussion': DiscussionProcessor,
    
    # Video
    'youtube': VideoProcessor,
    # Note: tiktok with video_analysis also uses VideoProcessor
    
    # Articles
    'news_blog': ArticleProcessor,
    'medium': ArticleProcessor,
    
    # Competitive
    'competitor_comparison': CompetitiveProcessor,
    
    # Brand
    'brand_website': BrandProcessor,
}


def get_processor_for_source(source_type: str, llm_client=None) -> BaseProcessor:
    """Get the appropriate processor for a source type."""
    processor_class = PROCESSOR_MAP.get(source_type, ReviewProcessor)
    return processor_class(llm_client=llm_client)
