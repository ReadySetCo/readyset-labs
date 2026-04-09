# -*- coding: utf-8 -*-
"""Brand Processor - Handles brand website content."""

from typing import Dict, Any, List
import json
import re
from .base import BaseProcessor


class BrandProcessor(BaseProcessor):
    """Processor for brand website content."""
    
    SOURCE_TYPES = ['brand_website']
    
    def get_prompt(self, content: str, metadata: Dict[str, Any]) -> str:
        url = metadata.get('source_url', '')
        
        return f"""Analyze this brand website content.
URL: {url}

CONTENT:
{content[:4000]}

Extract the following in JSON format:
{{
    "value_propositions": ["main value props stated"],
    "product_features": ["features highlighted"],
    "pricing_info": {{"model": "subscription/one-time", "prices": ["prices mentioned"]}},
    "target_audience_signals": ["who they're targeting"],
    "brand_voice": "professional" or "casual" or "playful" or "authoritative",
    "unique_selling_points": ["what makes them different"],
    "social_proof": ["testimonials, numbers, awards mentioned"],
    "ctas_used": ["call to action phrases"],
    "guarantees_offers": ["money back, free trial, etc"],
    "brand_story": "brief brand narrative if present"
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
        # Look for pricing patterns
        prices = re.findall(r'\$[\d,]+(?:\.\d{2})?', content)
        
        return {
            "prices_found": prices[:10],
            "content_snippet": content[:500],
            "source_url": metadata.get('source_url', ''),
            "source_type": metadata.get("source_type"),
            "processed": True,
            "llm_used": False
        }
