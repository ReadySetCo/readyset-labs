# -*- coding: utf-8 -*-
"""Review Processor - Handles customer reviews from multiple sources."""

from typing import Dict, Any, List
import json
import re
from .base import BaseProcessor


class ReviewProcessor(BaseProcessor):
    """Processor for customer reviews (Trustpilot, Google, App Store, etc.)"""
    
    SOURCE_TYPES = [
        'google_reviews', 'trustpilot', 'app_store', 'play_store',
        'g2', 'capterra', 'product_hunt', 'yelp', 'amazon', 'other_review'
    ]
    
    def get_prompt(self, content: str, metadata: Dict[str, Any]) -> str:
        source = metadata.get('source_type', 'review')
        rating = metadata.get('rating', '')
        rating_info = f"\nRating: {rating}/5" if rating else ""
        
        return f"""Analyze this customer review from {source}.{rating_info}

REVIEW:
{content[:2000]}

Extract the following in JSON format:
{{
    "verbatim_quote": "The most impactful quote from this review (exact words)",
    "sentiment": "positive" or "negative" or "neutral",
    "sentiment_score": 0.0 to 1.0,
    "key_themes": ["theme1", "theme2"],
    "pain_points": ["any problems or frustrations mentioned"],
    "purchase_triggers": ["what made them buy or consider buying"],
    "product_features_mentioned": ["specific features discussed"],
    "would_recommend": true or false or null,
    "summary": "1-2 sentence summary of the review"
}}

Return ONLY valid JSON, no other text."""

    def parse_response(self, response: str) -> Dict[str, Any]:
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
            return {"raw_response": response, "parse_error": True}
        except json.JSONDecodeError:
            return {"raw_response": response, "parse_error": True}
    
    def _basic_extraction(self, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Basic extraction without LLM."""
        # Simple sentiment detection
        positive_words = ['great', 'excellent', 'amazing', 'love', 'best', 'fantastic', 'wonderful']
        negative_words = ['bad', 'terrible', 'worst', 'hate', 'awful', 'horrible', 'disappointing']
        
        content_lower = content.lower()
        pos_count = sum(1 for w in positive_words if w in content_lower)
        neg_count = sum(1 for w in negative_words if w in content_lower)
        
        if pos_count > neg_count:
            sentiment = "positive"
            score = min(0.5 + (pos_count * 0.1), 1.0)
        elif neg_count > pos_count:
            sentiment = "negative"
            score = max(0.5 - (neg_count * 0.1), 0.0)
        else:
            sentiment = "neutral"
            score = 0.5
        
        return {
            "verbatim_quote": content[:200] if len(content) > 50 else content,
            "sentiment": sentiment,
            "sentiment_score": score,
            "key_themes": [],
            "pain_points": [],
            "purchase_triggers": [],
            "source_type": metadata.get("source_type"),
            "processed": True,
            "llm_used": False
        }
