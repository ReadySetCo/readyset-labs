# -*- coding: utf-8 -*-
"""Article Processor - Handles news, blogs, Medium articles."""

from typing import Dict, Any, List
import json
import re
from .base import BaseProcessor


class ArticleProcessor(BaseProcessor):
    """Processor for articles (news, blogs, Medium)."""
    
    SOURCE_TYPES = ['news_blog', 'medium']
    
    def get_prompt(self, content: str, metadata: Dict[str, Any]) -> str:
        source = metadata.get('source_type', 'article')
        title = metadata.get('title', '')
        url = metadata.get('source_url', '')
        
        return f"""Analyze this {source} article.
Title: {title}
URL: {url}

CONTENT:
{content[:4000]}

Extract the following in JSON format:
{{
    "article_type": "review" or "news" or "opinion" or "listicle" or "comparison",
    "brand_mentions": [
        {{"context": "how brand is mentioned", "sentiment": "positive/negative/neutral"}}
    ],
    "key_claims": ["factual claims made"],
    "competitor_comparisons": [
        {{"competitor": "name", "comparison": "how compared", "winner": "brand/competitor/tie"}}
    ],
    "quotes_about_brand": ["direct quotes relevant to brand"],
    "author_stance": "supportive" or "critical" or "neutral",
    "target_reader": "who this article is for",
    "seo_keywords": ["keywords this ranks for"],
    "main_takeaway": "1-2 sentence summary"
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
        return {
            "article_type": "unknown",
            "title": metadata.get('title', ''),
            "content_snippet": content[:500],
            "source_url": metadata.get('source_url', ''),
            "source_type": metadata.get("source_type"),
            "processed": True,
            "llm_used": False
        }
