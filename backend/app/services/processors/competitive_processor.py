# -*- coding: utf-8 -*-
"""Competitive Processor - Handles competitor comparisons."""

from typing import Dict, Any, List
import json
import re
from .base import BaseProcessor


class CompetitiveProcessor(BaseProcessor):
    """Processor for competitor comparison content."""
    
    SOURCE_TYPES = ['competitor_comparison']
    
    def get_prompt(self, content: str, metadata: Dict[str, Any]) -> str:
        return f"""Analyze this competitive comparison content.

CONTENT:
{content[:4000]}

Extract the following in JSON format:
{{
    "competitors_mentioned": ["list of competitor names"],
    "brand_advantages": ["where brand wins vs competitors"],
    "brand_disadvantages": ["where competitors win"],
    "price_comparison": {{"brand": "price", "competitors": {{"name": "price"}}}},
    "feature_comparison": [
        {{"feature": "name", "brand_has": true, "competitor_has": true}}
    ],
    "recommendation": "which is recommended and why",
    "key_differentiators": ["what makes brand unique"],
    "switching_triggers": ["reasons someone would switch to brand"],
    "competitive_quote": "most impactful quote about competition"
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
        # Look for common competitor patterns
        vs_matches = re.findall(r'(\w+)\s+vs\s+(\w+)', content, re.IGNORECASE)
        competitors = list(set([m[0] for m in vs_matches] + [m[1] for m in vs_matches]))
        
        return {
            "competitors_mentioned": competitors[:10],
            "content_snippet": content[:500],
            "source_type": metadata.get("source_type"),
            "processed": True,
            "llm_used": False
        }
