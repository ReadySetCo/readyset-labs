# -*- coding: utf-8 -*-
"""
Instagram Brand Analyzer - LLM-powered analysis of brand's Instagram presence.

Analyzes the brand's last 40 posts to extract:
- Brand voice & tone
- Visual aesthetic
- Content pillars
- Messaging patterns

The data flows to: script generator, hooks library, RAG chat, dashboard.
"""

import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

import google.generativeai as genai

from ..config import settings


class InstagramBrandAnalyzer:
    """
    Analyzes a brand's Instagram presence using Gemini LLM.
    
    Extracts brand voice, visual aesthetic, and content strategy for scriptwriting.
    """
    
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if self.api_key:
            genai.configure(api_key=self.api_key)
        self.model_id = getattr(settings, 'GEMINI_MODEL', None) or "models/gemini-2.0-flash"
        self.max_posts = 40  # Analyze last 40 posts
    
    def _build_brand_presence_prompt(self, posts: List[Dict[str, Any]], brand_name: str) -> str:
        """
        Build prompt for analyzing brand's Instagram presence.
        Synthesizes patterns across posts for brand identity insights.
        """
        # Create summary of posts
        posts_summary = []
        for i, post in enumerate(posts[:self.max_posts], 1):
            content = post.get("content", "") or post.get("raw_data", {}).get("caption", "")
            likes = post.get("likes", 0)
            comments = post.get("comments_count", 0)
            
            summary = f"""
Post {i}:
- Caption: "{content[:300] if content else 'No caption'}..."
- Engagement: {likes} likes, {comments} comments
"""
            posts_summary.append(summary)
        
        posts_text = "\n".join(posts_summary)
        
        return f"""You are a brand strategist analyzing {brand_name}'s Instagram presence.
I've collected their last {len(posts)} posts. Analyze them to extract brand identity and content strategy.

POSTS DATA:
{posts_text}

Return a JSON object with:

## BRAND VOICE & TONE
- "brand_voice": Overall voice description (10-20 words)
- "primary_tone": "Professional" | "Casual" | "Playful" | "Inspirational" | "Educational" | "Luxury" | "Authentic" | "Edgy"
- "secondary_tones": [List of secondary tones]
- "communication_style": How they talk to their audience (formal/informal, 1st/2nd/3rd person, etc.)
- "vocabulary_patterns": [Key words and phrases they use repeatedly]
- "emoji_usage": "Heavy" | "Moderate" | "Minimal" | "None"
- "hashtag_strategy": How they use hashtags (branded, generic, mix, etc.)

## VISUAL AESTHETIC (Based on Captions Context)
- "visual_mood": Overall visual feeling they convey
- "color_palette_description": Description of likely color themes
- "content_style": "Polished" | "UGC-style" | "Minimalist" | "Vibrant" | "Dark" | "Lifestyle" | "Product-focused"
- "aesthetic_keywords": [3-5 words describing their look and feel]

## CONTENT PILLARS
- "content_pillars": [List of 3-5 main content themes/categories they post about]
- "content_mix": {{"pillar_name": "percentage_estimate"}} - roughly how much of each
- "post_types": [Types of posts: product, lifestyle, educational, behind-scenes, user-generated, etc.]
- "storytelling_approach": How they tell their brand story

## MESSAGING STRATEGY
- "core_message": Their main brand message in one sentence
- "value_proposition": What value they promise
- "differentiation": How they position vs competitors (if visible)
- "cta_patterns": [Common calls-to-action they use]
- "engagement_tactics": [How they encourage engagement: questions, polls, etc.]

## AUDIENCE RELATIONSHIP
- "audience_persona": Who they're talking to (15-20 words)
- "community_building": How they build community (respond to comments, feature users, etc.)
- "exclusivity_signals": Any VIP, insider, or exclusive messaging

## CAMPAIGN & SEASONAL PATTERNS
- "recurring_themes": [Themes that appear repeatedly]
- "promotional_approach": How they handle promotions/sales
- "content_frequency_vibe": "Daily engagement" | "Regular updates" | "Quality over quantity" | "Sporadic"

## BRAND PERSONALITY SUMMARY
- "brand_personality": 50-word summary of the brand's personality based on their Instagram
- "brand_archetype": One of: "Hero" | "Outlaw" | "Magician" | "Innocent" | "Explorer" | "Sage" | "Lover" | "Jester" | "Everyman" | "Caregiver" | "Ruler" | "Creator"
- "key_brand_attributes": [5 adjectives that define this brand]

## RECOMMENDATIONS FOR AD CREATION
- "voice_dos": [5 things to DO when writing for this brand]
- "voice_donts": [5 things to AVOID when writing for this brand]
- "script_tone_guide": Brief guide for matching their tone in ads
- "visual_direction": Brief guide for visual style in ads

Return ONLY valid JSON. Be specific and base insights on actual patterns observed in the posts."""
    
    async def analyze_brand_presence(
        self,
        posts: List[Dict[str, Any]],
        brand_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze a brand's Instagram presence from their posts.
        
        Args:
            posts: List of Instagram post dicts (last 40 posts ideally)
            brand_name: Brand name for context
            
        Returns:
            Dict with brand presence insights or None if analysis fails
        """
        if not self.api_key:
            print("       [Instagram Brand] No API key configured")
            return None
        
        if not posts:
            print("       [Instagram Brand] No posts to analyze")
            return None
        
        # Limit to max_posts
        posts_to_analyze = posts[:self.max_posts]
        
        print(f"       [Instagram Brand] Analyzing {len(posts_to_analyze)} posts for brand presence...")
        
        try:
            prompt = self._build_brand_presence_prompt(posts_to_analyze, brand_name)
            model = genai.GenerativeModel(self.model_id)
            
            response = await asyncio.wait_for(
                asyncio.to_thread(model.generate_content, prompt),
                timeout=60.0
            )
            
            result = self._extract_json(response.text)
            if result:
                result["analyzed_at"] = datetime.now().isoformat()
                result["posts_analyzed"] = len(posts_to_analyze)
                result["brand_name"] = brand_name
                result["source"] = "instagram_brand_presence"
            
            print(f"       [+] Instagram Brand: Analysis complete")
            return result
            
        except asyncio.TimeoutError:
            print(f"       [Instagram Brand] Timeout during analysis")
            return None
        except Exception as e:
            print(f"       [Instagram Brand] Error: {e}")
            return None
    
    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from LLM response."""
        if not text:
            return None
        try:
            import re
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                return json.loads(match.group(0))
        except (json.JSONDecodeError, ValueError) as e:
            print(f"       [Instagram Brand] JSON regex extraction failed: {e}")
        try:
            clean = text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"       [Instagram Brand] JSON clean extraction failed: {e}")
        print(f"       [Instagram Brand] Could not parse LLM response ({len(text)} chars)")
        return None


# Singleton instance
_brand_analyzer = None


def get_instagram_brand_analyzer() -> InstagramBrandAnalyzer:
    """Get Instagram brand analyzer instance."""
    global _brand_analyzer
    if _brand_analyzer is None:
        _brand_analyzer = InstagramBrandAnalyzer()
    return _brand_analyzer
