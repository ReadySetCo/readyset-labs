# -*- coding: utf-8 -*-
"""Social Processor - Handles social media posts."""

from typing import Dict, Any, List
import json
import re
from .base import BaseProcessor


class SocialProcessor(BaseProcessor):
    """Processor for social media content (Twitter, Instagram, LinkedIn, TikTok)."""
    
    SOURCE_TYPES = ['twitter', 'instagram', 'linkedin', 'tiktok', 'instagram_profile']
    
    def get_prompt(self, content: str, metadata: Dict[str, Any]) -> str:
        source = metadata.get('source_type', 'social')
        author = metadata.get('author', 'unknown')
        likes = metadata.get('likes', 0)
        
        return f"""Analyze this {source} post by @{author} ({likes} likes).

POST:
{content[:2000]}

Extract the following in JSON format:
{{
    "mention_type": "organic" or "paid" or "influencer" or "ugc" or "brand",
    "sentiment": "positive" or "negative" or "neutral",
    "sentiment_score": 0.0 to 1.0,
    "brand_claims": ["specific claims about the brand/product"],
    "implied_audience": "description of who this targets",
    "engagement_potential": "low" or "medium" or "high",
    "hashtags": ["relevant hashtags"],
    "mentions": ["@mentions"],
    "call_to_action": "any CTA present or null",
    "key_message": "main point in 1 sentence"
}}

Return ONLY valid JSON, no other text."""

    def parse_response(self, response: str) -> Dict[str, Any]:
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
            return {"raw_response": response, "parse_error": True}
        except json.JSONDecodeError:
            return {"raw_response": response, "parse_error": True}
    
    def _basic_extraction(self, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Basic extraction without LLM."""
        # Extract hashtags
        hashtags = re.findall(r'#(\w+)', content)
        # Extract mentions
        mentions = re.findall(r'@(\w+)', content)
        
        return {
            "mention_type": "organic",
            "sentiment": "neutral",
            "hashtags": hashtags[:10],
            "mentions": mentions[:10],
            "content_snippet": content[:300],
            "source_type": metadata.get("source_type"),
            "processed": True,
            "llm_used": False
        }
