# -*- coding: utf-8 -*-
"""Ad Library Processor - Handles Meta Ad Library data and competitor ads."""

from typing import Dict, Any, List
import json
import re
from .base import BaseProcessor


class AdLibraryProcessor(BaseProcessor):
    """Processor for Ad Library data (brand ads and competitor ads)."""
    
    SOURCE_TYPES = ['ad_library', 'competitor_ads']
    
    def get_prompt(self, content: str, metadata: Dict[str, Any]) -> str:
        is_competitor = metadata.get('is_competitor', False)
        competitor_name = metadata.get('competitor_name', 'Unknown')
        
        if is_competitor:
            return self._get_competitor_prompt(content, competitor_name)
        else:
            return self._get_brand_prompt(content)
    
    def _get_brand_prompt(self, content: str) -> str:
        return f"""Analyze this brand ad creative from Meta Ad Library.

AD DATA:
{content[:3000]}

Extract the following in JSON format:
{{
    "ad_type": "brand_ad",
    "headline": "main headline text",
    "body_copy": "main body text",
    "hook_type": "problem" or "curiosity" or "benefit" or "social_proof" or "urgency" or "other",
    "hook_analysis": "why this hook works",
    "cta": "call to action text",
    "offer": "any discount/promotion",
    "format": "video" or "image" or "carousel",
    "video_duration": "duration if video",
    "target_audience_signals": ["audience targeting signals"],
    "emotional_triggers": ["emotions leveraged"],
    "creative_elements": ["notable visual/copy elements"],
    "landing_page_type": "product" or "collection" or "quiz" or "article"
}}

Return ONLY valid JSON, no other text."""
    
    def _get_competitor_prompt(self, content: str, competitor_name: str) -> str:
        return f"""Analyze this COMPETITOR ad from Meta Ad Library.
COMPETITOR: {competitor_name}

AD DATA:
{content[:3000]}

Extract the following in JSON format:
{{
    "ad_type": "competitor_ad",
    "competitor_name": "{competitor_name}",
    "headline": "their headline",
    "body_copy": "their body text",
    "hook_strategy": "what hook they use and why",
    "offer_promotion": "their offer",
    "unique_claims": ["claims they make"],
    "attack_points": ["where they attack our brand or category"],
    "exploitable_weaknesses": ["weaknesses we can exploit"],
    "format": "video" or "image" or "carousel",
    "creative_quality": "low" or "medium" or "high",
    "lessons_to_learn": ["what we can learn from this ad"],
    "counter_strategy": "how we could counter this"
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
        is_competitor = metadata.get('is_competitor', False)
        
        return {
            "ad_type": "competitor_ad" if is_competitor else "brand_ad",
            "competitor_name": metadata.get('competitor_name') if is_competitor else None,
            "content_snippet": str(content)[:500] if content else "",
            "processed": True,
            "llm_used": False
        }
    
    async def process_ad_data(
        self,
        ad_data: Dict[str, Any],
        is_competitor: bool = False,
        competitor_name: str = None
    ) -> Dict[str, Any]:
        """
        Process ad library data specifically.
        
        Args:
            ad_data: Raw ad data from Meta Ad Library
            is_competitor: Whether this is a competitor ad
            competitor_name: Name of competitor if applicable
        """
        content = json.dumps(ad_data, indent=2) if isinstance(ad_data, dict) else str(ad_data)
        
        metadata = {
            'is_competitor': is_competitor,
            'competitor_name': competitor_name,
            'source_type': 'competitor_ads' if is_competitor else 'ad_library'
        }
        
        return await self.process(content, metadata)
