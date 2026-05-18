# -*- coding: utf-8 -*-
"""
Thumbnail Suggester - Lightweight, reliable thumbnail suggestions.
"""

import asyncio
from typing import Dict, Any, List
from ..llm.client import get_llm_client


class ThumbnailSuggester:
    """Generates thumbnail suggestions with short, focused prompts."""
    
    def __init__(self):
        self.llm = get_llm_client(task_type="creative")
    
    async def suggest_thumbnails(
        self,
        brand_info: Dict[str, Any],
        ad_patterns: Dict[str, Any],
        insights: Dict[str, Any],
        num_suggestions: int = 3
    ) -> List[Dict[str, Any]]:
        """Generate thumbnail suggestions using real Ad Library data."""
        
        brand_name = brand_info.get('name', 'Brand')[:50]
        sector = str(brand_info.get('sector', ''))[:30]
        
        # Get key data from insights
        pain_points = insights.get('pain_points', [])[:5]
        pain_text = '\n'.join([f"• {str(p.get('pain_point', p) if isinstance(p, dict) else p)[:80]}" for p in pain_points]) or "common problems"
        
        # Get Ad Library data (what's working)
        ad_examples = ad_patterns.get('ad_examples', {})
        visual_types = list(ad_patterns.get('visual_types', {}).keys())[:5]
        first_frames = []
        best_hooks = []
        
        for ad in ad_examples.get('brand_ads', [])[:10]:
            if ad.get('visual_type'):
                if ad['visual_type'] not in visual_types:
                    visual_types.append(ad['visual_type'])
            if ad.get('hook'):
                best_hooks.append(f"• \"{ad['hook'][:100]}\" (Strength: {ad.get('hook_strength', 0)}/5)")
        
        for ad in ad_examples.get('competitor_ads', [])[:5]:
            if ad.get('hook'):
                best_hooks.append(f"• [{ad.get('competitor', 'Competitor')}] \"{ad['hook'][:100]}\"")
        
        visual_types_text = ', '.join(visual_types[:6]) if visual_types else "talking head, product demo, lifestyle"
        hooks_text = '\n'.join(best_hooks[:8]) if best_hooks else "No hooks analyzed"
        
        print(f"       -> Generating {num_suggestions} thumbnail ideas (using {len(best_hooks)} hooks, {len(visual_types)} visual types)...")
        
        prompt = f"""Suggest {num_suggestions} thumbnail/first-frame ideas for {brand_name} ({sector}) video ads.

=== TARGET AUDIENCE PAIN POINTS ===
{pain_text}

=== VISUAL STYLES THAT WORK (from analyzed ads) ===
{visual_types_text}

=== TOP HOOKS FROM SUCCESSFUL ADS ===
These hooks stopped the scroll - use similar strategies:
{hooks_text}

=== TASK ===
Create {num_suggestions} thumbnail concepts that:
1. Match the visual styles that work for this brand
2. Use hooks/text that create curiosity or address pain points
3. Would stop someone from scrolling in their feed

Return JSON array:
[
    {{
        "concept_name": "Short memorable name",
        "thumbnail_type": "UGC/Studio/Lifestyle/Product-focused/Text-led/etc",
        "visual_description": "What the thumbnail shows - be specific about visuals",
        "visual_elements": ["element1", "element2", "element3"],
        "text_overlay": "Bold text shown on thumbnail (use hook inspiration)",
        "visual_style": "UGC/Studio/Lifestyle/Product-focused/etc",
        "first_frame_element": "Face/Product/Text/Scene/Offer",
        "emotion_evoked": "Emotion to evoke",
        "why_it_works": "Why this will stop the scroll - reference the data above",
        "platform_fit": ["TikTok", "Instagram", "Meta"]
    }}
]"""

        try:
            result = await asyncio.wait_for(
                self.llm.complete_json(prompt=prompt, temperature=0.7),
                timeout=60.0  # 60s margin for gpt-5.4 (creative calls observed 22-25s in session 139)
            )
            
            if result and isinstance(result, list):
                print(f"       -> Generated {len(result)} thumbnail ideas")
                return [self._normalize_thumbnail(item) for item in result[:num_suggestions]]
            elif result and isinstance(result, dict):
                # Handle wrapped response
                for key in ["thumbnails", "suggestions", "concepts"]:
                    if key in result and isinstance(result[key], list):
                        return [self._normalize_thumbnail(item) for item in result[key][:num_suggestions]]
        
        except asyncio.TimeoutError:
            print(f"       [!] Thumbnail generation timeout")
        except Exception as e:
            import traceback
            print(f"       [!] Thumbnail generation failed: {type(e).__name__}: {e}")
            print(f"       [!] Traceback:\n{traceback.format_exc()}")
        
        # Fallback thumbnails
        print(f"       -> Using fallback thumbnails")
        return self._generate_fallbacks(brand_name, num_suggestions)

    def _normalize_thumbnail(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Keep new sessions canonical even if the LLM returns legacy field names."""
        if not isinstance(item, dict):
            return {}
        visual_elements = item.get("visual_elements") or []
        if not isinstance(visual_elements, list):
            visual_elements = [str(visual_elements)]
        return {
            **item,
            "thumbnail_type": item.get("thumbnail_type") or item.get("visual_style") or item.get("first_frame_element"),
            "visual_description": item.get("visual_description") or item.get("description") or ", ".join(map(str, visual_elements)),
            "emotion_evoked": item.get("emotion_evoked") or item.get("emotion_target") or item.get("target_emotion"),
            "why_it_works": item.get("why_it_works") or item.get("why_effective"),
            "platform_fit": item.get("platform_fit") or item.get("platforms") or [],
        }
    
    def _generate_fallbacks(self, brand_name: str, num: int) -> List[Dict[str, Any]]:
        """Generate fallback thumbnail suggestions."""
        fallbacks = [
            {
                "concept_name": "Problem Face",
                "thumbnail_type": "UGC",
                "visual_description": f"Close-up of person with frustrated expression, relatable problem",
                "visual_elements": ["face", "emotion", "problem context"],
                "text_overlay": "Sound familiar?",
                "emotion_evoked": "Recognition",
                "why_it_works": "Creates immediate emotional connection",
                "platform_fit": ["TikTok", "Instagram", "Meta"]
            },
            {
                "concept_name": "Before/After Split",
                "thumbnail_type": "Transformation",
                "visual_description": f"Split screen showing transformation with {brand_name}",
                "visual_elements": ["split screen", "contrast", "product"],
                "text_overlay": "The difference is real",
                "emotion_evoked": "Aspiration",
                "why_it_works": "Shows tangible results",
                "platform_fit": ["TikTok", "Instagram", "Meta"]
            },
            {
                "concept_name": "Curiosity Question",
                "thumbnail_type": "Text-led",
                "visual_description": f"Bold text question with intriguing background",
                "visual_elements": ["text", "minimal design", "curiosity gap"],
                "text_overlay": "Wait... this actually works?",
                "emotion_evoked": "Curiosity",
                "why_it_works": "Creates information gap that demands resolution",
                "platform_fit": ["TikTok", "Instagram", "Meta"]
            }
        ]
        return fallbacks[:num]
    
    async def analyze_thumbnail_effectiveness(
        self,
        thumbnail_descriptions: List[str]
    ) -> List[Dict[str, Any]]:
        """Quick effectiveness analysis."""
        return [{"description": d, "score": 3, "suggestion": "Test variations"} for d in thumbnail_descriptions]
    
    async def generate_ab_thumbnail_pairs(
        self,
        base_concept: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate A/B variations of a thumbnail."""
        name = base_concept.get('concept_name', 'Concept')
        return [
            {**base_concept, "variant": "A", "concept_name": f"{name} - Text Focus"},
            {**base_concept, "variant": "B", "concept_name": f"{name} - Visual Focus"}
        ]
