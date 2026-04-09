# -*- coding: utf-8 -*-
"""Video Processor - Handles video content and transcriptions."""

from typing import Dict, Any, List
import json
import re
from .base import BaseProcessor


class VideoProcessor(BaseProcessor):
    """Processor for video content (YouTube, TikTok with video_analysis)."""
    
    SOURCE_TYPES = ['youtube', 'tiktok']  # tiktok when has video_analysis
    
    def get_prompt(self, content: str, metadata: Dict[str, Any]) -> str:
        source = metadata.get('source_type', 'video')
        title = metadata.get('title', '')
        video_analysis = metadata.get('video_analysis', {})
        
        # Include video analysis if available
        analysis_info = ""
        if video_analysis:
            analysis_info = f"\n\nVIDEO ANALYSIS DATA:\n{json.dumps(video_analysis, indent=2)[:1000]}"
        
        return f"""Analyze this {source} video content.
Title: {title}

TRANSCRIPT/CONTENT:
{content[:4000]}
{analysis_info}

Extract the following in JSON format:
{{
    "executive_summary": "2-3 sentence summary of the video",
    "main_claims": ["key claims made about product/brand"],
    "key_moments": [
        {{"timestamp": "0:00", "description": "what happens"}}
    ],
    "cta_mentioned": "call to action if any",
    "offers_promotions": ["any discounts or offers mentioned"],
    "emotional_hooks": ["emotional triggers used"],
    "target_audience": "who this video targets",
    "production_style": "professional" or "ugc" or "mixed",
    "full_transcript_preserved": true,
    "transcript_snippet": "first 500 chars of transcript"
}}

Return ONLY valid JSON, no other text."""

    def parse_response(self, response: str) -> Dict[str, Any]:
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                parsed = json.loads(json_match.group())
                parsed["full_transcript_preserved"] = True
                return parsed
            return {"raw_response": response, "parse_error": True}
        except json.JSONDecodeError:
            return {"raw_response": response, "parse_error": True}
    
    def _basic_extraction(self, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Basic extraction without LLM."""
        return {
            "executive_summary": metadata.get('title', 'Video content'),
            "transcript_snippet": content[:500],
            "full_transcript": content,  # Preserve full transcript
            "source_type": metadata.get("source_type"),
            "video_analysis": metadata.get("video_analysis"),
            "processed": True,
            "llm_used": False
        }
