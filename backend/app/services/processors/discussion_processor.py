# -*- coding: utf-8 -*-
"""Discussion Processor - Handles Reddit, forums, Quora, comments."""

from typing import Dict, Any, List
import json
import re
from .base import BaseProcessor


class DiscussionProcessor(BaseProcessor):
    """Processor for discussions (Reddit, forums, Quora, YouTube comments)."""
    
    SOURCE_TYPES = ['reddit', 'forum', 'quora', 'youtube_comment', 'segment_discussion']
    
    def get_prompt(self, content: str, metadata: Dict[str, Any]) -> str:
        source = metadata.get('source_type', 'discussion')
        title = metadata.get('title', '')
        title_info = f"\nThread title: {title}" if title else ""
        
        return f"""Analyze this {source} discussion/comment.{title_info}

CONTENT:
{content[:3000]}

Extract the following in JSON format:
{{
    "main_topic": "what this discussion is about",
    "brand_sentiment": "positive" or "negative" or "neutral" or "mixed",
    "opinions_expressed": [
        {{"stance": "pro" or "con" or "neutral", "summary": "brief opinion"}}
    ],
    "questions_asked": ["questions users are asking"],
    "objections_raised": ["doubts or objections mentioned"],
    "recommendations_given": ["any recommendations made"],
    "verbatim_quotes": ["most valuable direct quotes (max 3)"],
    "competitor_mentions": ["competitors mentioned"],
    "engagement_signals": {{"upvotes": 0, "comments": 0}},
    "key_insight": "the most valuable insight from this discussion"
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
        # Look for question marks
        questions = [s.strip() for s in content.split('?') if len(s.strip()) > 10][:3]
        
        return {
            "main_topic": metadata.get('title', 'Unknown'),
            "brand_sentiment": "neutral",
            "questions_asked": [q + '?' for q in questions] if questions else [],
            "content_snippet": content[:500],
            "source_type": metadata.get("source_type"),
            "processed": True,
            "llm_used": False
        }
