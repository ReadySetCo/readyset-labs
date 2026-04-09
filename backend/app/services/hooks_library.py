# -*- coding: utf-8 -*-
"""
Hooks Library Service - Generate structured, actionable hooks for ad creative.

Creates a library of hooks organized by:
- Type (question, statement, curiosity, story, etc.)
- Target persona (which ICP it speaks to)
- Platform fit (TikTok, Instagram, Facebook, etc.)
- Emotion triggered (curiosity, fear, hope, etc.)
- Source (derived from data or inspired by patterns)
"""

from typing import Dict, Any, List, Optional
from collections import defaultdict
import asyncio

from .llm.client import get_llm_client


class HooksLibraryService:
    """Generate structured hooks library for creative strategy."""
    
    # Hook type definitions
    HOOK_TYPES = {
        "question": {
            "description": "Opens with a question to engage viewer",
            "examples": ["Did you know...?", "Why does everyone...?", "What if I told you...?"],
            "best_for": ["TikTok", "Instagram Reels"],
            "emotion": "curiosity"
        },
        "statement": {
            "description": "Bold claim or declaration",
            "examples": ["This changes everything.", "Forget what you know about..."],
            "best_for": ["Facebook", "YouTube"],
            "emotion": "surprise"
        },
        "story": {
            "description": "Personal narrative opening",
            "examples": ["6 months ago I was...", "When my doctor told me..."],
            "best_for": ["TikTok", "Instagram Reels", "Facebook"],
            "emotion": "relatability"
        },
        "pattern_interrupt": {
            "description": "Unexpected opening that stops scroll",
            "examples": ["POV:", "Wait...", "I can't believe I'm showing this..."],
            "best_for": ["TikTok", "Instagram Reels"],
            "emotion": "shock"
        },
        "curiosity_gap": {
            "description": "Creates tension that must be resolved",
            "examples": ["The thing nobody tells you about...", "Nobody is talking about this..."],
            "best_for": ["TikTok", "YouTube"],
            "emotion": "intrigue"
        },
        "testimonial": {
            "description": "Social proof opening",
            "examples": ["I've been using this for 3 months...", "My [expert] recommended..."],
            "best_for": ["Facebook", "Instagram"],
            "emotion": "trust"
        },
        "problem_call_out": {
            "description": "Directly addresses pain point",
            "examples": ["Tired of...?", "Still struggling with...?", "If you deal with..."],
            "best_for": ["Facebook", "YouTube"],
            "emotion": "recognition"
        },
        "transformation": {
            "description": "Before/after focus",
            "examples": ["Watch my [X] transform in real-time", "3 months later..."],
            "best_for": ["Instagram", "TikTok"],
            "emotion": "aspiration"
        }
    }
    
    # Emotions mapping
    EMOTIONS = {
        "curiosity": "Makes viewer want to learn more",
        "fear": "Highlights risk of not taking action",
        "hope": "Promises a better outcome",
        "trust": "Builds credibility and social proof",
        "urgency": "Creates time pressure",
        "recognition": "Makes viewer feel seen/understood",
        "aspiration": "Shows desirable end state",
        "surprise": "Challenges assumptions",
        "relatability": "Connects through shared experience"
    }
    
    def __init__(self):
        self.llm = get_llm_client(provider="gemini")
    
    async def generate_hooks_library(
        self,
        brand_info: Dict[str, Any],
        insights: Dict[str, Any],
        num_hooks: int = 30
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive hooks library.
        
        Args:
            brand_info: Brand information dict
            insights: Generated insights dict
            num_hooks: Target number of hooks to generate
            
        Returns:
            Structured hooks library with categorization
        """
        print(f"       [Hooks Library] Generating {num_hooks} hooks...")
        
        # Build context from insights
        context = self._build_hooks_context(brand_info, insights)
        
        # Generate hooks via LLM
        raw_hooks = await self._generate_hooks_batch(context, num_hooks)
        
        # Organize into library
        library = self._organize_hooks(raw_hooks, brand_info)
        
        # Add recommendations
        library["recommendations"] = self._generate_recommendations(library)
        
        print(f"       [Hooks Library] Generated {len(library.get('all_hooks', []))} hooks in {len(library.get('by_type', {}))} categories")
        return library
    
    def _build_hooks_context(
        self,
        brand_info: Dict[str, Any],
        insights: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build context for hook generation."""
        return {
            "brand_name": brand_info.get("name", "Brand"),
            "sector": brand_info.get("sector", ""),
            "products": brand_info.get("products", []),
            "pain_points": insights.get("pain_points", [])[:10],
            "customer_language": insights.get("customer_language", [])[:15],
            "verbatim_quotes": [q.get("quote", q) if isinstance(q, dict) else q 
                              for q in insights.get("verbatim_quotes", [])[:10]],
            "icps": insights.get("icps", [])[:5],
            "objections": insights.get("objections", [])[:5],
            "recommended_hooks": insights.get("recommended_hooks", [])[:10],
            "purchase_triggers": insights.get("purchase_triggers", [])[:5],
            "tiktok_trends": insights.get("tiktok_trends", {})
        }
    
    async def _generate_hooks_batch(
        self,
        context: Dict[str, Any],
        num_hooks: int
    ) -> List[Dict[str, Any]]:
        """Generate hooks using LLM."""
        
        prompt = f"""Generate {num_hooks} unique, ready-to-use ad hooks for {context['brand_name']}.

=== BRAND CONTEXT ===
Sector: {context['sector']}
Products: {', '.join(str(p) for p in context['products'][:5]) if context['products'] else 'Various products'}

=== CUSTOMER PAIN POINTS ===
{chr(10).join(f'• {p}' for p in context['pain_points'][:8]) if context['pain_points'] else '• General industry pain points'}

=== CUSTOMER LANGUAGE (use these exact phrases!) ===
{chr(10).join(f'• "{p}"' for p in context['customer_language'][:10]) if context['customer_language'] else '• Natural conversational language'}

=== REAL CUSTOMER QUOTES (incorporate these) ===
{chr(10).join(f'• "{q[:150]}"' for q in context['verbatim_quotes'][:8]) if context['verbatim_quotes'] else '• Use relatable testimonial style'}

=== OBJECTIONS TO ADDRESS ===
{chr(10).join(f'• {o.get("objection", o) if isinstance(o, dict) else o}' for o in context['objections'][:5]) if context['objections'] else '• Common purchase hesitations'}

=== HOOK TYPES TO INCLUDE ===
Generate a MIX of these types:
1. question - Opens with engaging question
2. statement - Bold claim or declaration
3. story - Personal narrative opening
4. pattern_interrupt - POV, Wait, unexpected opening
5. curiosity_gap - Creates tension to be resolved
6. testimonial - Social proof opening
7. problem_call_out - Directly addresses pain point
8. transformation - Before/after focus

=== OUTPUT FORMAT ===
Return a JSON dictionary containing a single key "hooks". The value must be an array of {num_hooks} hook objects. Each hook object must have:
{{
    "hook_text": "The exact hook text, ready to use (10-50 words)",
    "hook_type": "question/statement/story/pattern_interrupt/curiosity_gap/testimonial/problem_call_out/transformation",
    "target_emotion": "curiosity/fear/hope/trust/urgency/recognition/aspiration/surprise/relatability",
    "target_persona": "Brief description of who this speaks to",
    "platform_fit": ["TikTok", "Instagram", "Facebook"],  // Best platforms for this hook
    "pain_point_addressed": "Which pain point this targets (if any)",
    "verbatim_source": "Which customer quote inspired this (if any)",
    "strength_score": 1-5,  // Estimated hook strength
    "why_it_works": "One sentence on why this hook is effective"
}}

Generate EXACTLY {num_hooks} unique hooks. Make them specific to {context['brand_name']}, not generic.
Use the EXACT customer language provided whenever possible.
Prioritize hooks that address real objections and pain points from the data."""

        system = """You are an elite creative strategist specializing in direct-response advertising hooks.
You write hooks that:
- Stop the scroll in the first 1-3 seconds
- Use the customer's exact words (not marketing speak)
- Create an irresistible urge to keep watching
- Feel native to each platform
Return ONLY valid JSON. No explanation, no markdown."""

        for attempt in range(2):
            try:
                result = await asyncio.wait_for(
                    self.llm.complete_json(prompt=prompt, system_prompt=system, temperature=0.8),
                    timeout=180.0
                )

                if result and isinstance(result, list):
                    print(f"       [Hooks] LLM returned list with {len(result)} items (attempt {attempt+1})")
                    return result
                elif result and isinstance(result, dict):
                    if "hooks" in result:
                        print(f"       [Hooks] LLM returned dict with {len(result['hooks'])} hooks (attempt {attempt+1})")
                        return result["hooks"]
                    # Sometimes LLM puts it in another key
                    for key, value in result.items():
                        if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict) and "hook_text" in value[0]:
                            print(f"       [Hooks] Found hooks under key '{key}' ({len(value)} hooks)")
                            return value
                    print(f"       [!] Hooks LLM dict missing hooks array. Keys: {list(result.keys())}")
                else:
                    print(f"       [!] Hooks LLM returned {type(result).__name__} (attempt {attempt+1})")

                # Retry with simplified prompt on first failure
                if attempt == 0:
                    print(f"       [Hooks] Retrying with simplified prompt...")
                    prompt = f"""Generate {num_hooks} ad hooks for {context['brand_name']}.
Pain points: {', '.join(str(p)[:60] for p in context['pain_points'][:5])}

Return JSON: {{"hooks": [
  {{"hook_text": "...", "hook_type": "question", "target_emotion": "curiosity", "strength_score": 4, "why_it_works": "..."}}
]}}
Generate {num_hooks} hooks. Be specific to {context['brand_name']}."""

            except asyncio.TimeoutError:
                print(f"       [!] Hooks generation timeout (attempt {attempt+1})")
            except Exception as e:
                print(f"       [!] Hooks generation error (attempt {attempt+1}): {str(e)[:80]}")

        return []
    
    def _organize_hooks(
        self,
        raw_hooks: List[Dict[str, Any]],
        brand_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Organize hooks into structured library."""
        
        library = {
            "brand": brand_info.get("name", "Brand"),
            "total_hooks": len(raw_hooks),
            "generated_at": None,  # Will be set when saving
            
            "all_hooks": raw_hooks,
            
            # Categorized views
            "by_type": defaultdict(list),
            "by_emotion": defaultdict(list),
            "by_platform": defaultdict(list),
            "by_strength": defaultdict(list),
            
            # Stats
            "type_distribution": {},
            "emotion_distribution": {},
            "platform_coverage": {},
            "avg_strength": 0
        }
        
        total_strength = 0
        
        for hook in raw_hooks:
            # By type
            hook_type = hook.get("hook_type", "other")
            library["by_type"][hook_type].append(hook)
            
            # By emotion
            emotion = hook.get("target_emotion", "other")
            library["by_emotion"][emotion].append(hook)
            
            # By platform
            platforms = hook.get("platform_fit", ["general"])
            if isinstance(platforms, str):
                platforms = [platforms]
            for platform in platforms:
                library["by_platform"][platform.lower()].append(hook)
            
            # By strength
            strength = hook.get("strength_score", 3)
            strength_bucket = "weak" if strength <= 2 else "medium" if strength <= 3 else "strong"
            library["by_strength"][strength_bucket].append(hook)
            total_strength += strength
        
        # Calculate distributions
        library["type_distribution"] = {k: len(v) for k, v in library["by_type"].items()}
        library["emotion_distribution"] = {k: len(v) for k, v in library["by_emotion"].items()}
        library["platform_coverage"] = {k: len(v) for k, v in library["by_platform"].items()}
        library["avg_strength"] = round(total_strength / len(raw_hooks), 2) if raw_hooks else 0
        
        # Convert defaultdicts to regular dicts
        library["by_type"] = dict(library["by_type"])
        library["by_emotion"] = dict(library["by_emotion"])
        library["by_platform"] = dict(library["by_platform"])
        library["by_strength"] = dict(library["by_strength"])
        
        return library
    
    def _generate_recommendations(self, library: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate recommendations based on library analysis."""
        recommendations = []
        
        # Top performing hooks
        strong_hooks = library.get("by_strength", {}).get("strong", [])
        if strong_hooks:
            top_hook = strong_hooks[0]
            recommendations.append({
                "type": "top_hook",
                "action": f"Start testing with: \"{top_hook.get('hook_text', '')[:80]}...\"",
                "rationale": f"Highest strength score ({top_hook.get('strength_score', 5)}/5) - {top_hook.get('why_it_works', '')}"
            })
        
        # Platform-specific recommendation
        platform_counts = library.get("platform_coverage", {})
        if platform_counts:
            top_platform = max(platform_counts, key=platform_counts.get)
            recommendations.append({
                "type": "platform",
                "action": f"Focus on {top_platform} first",
                "rationale": f"Highest hook coverage ({platform_counts[top_platform]} hooks optimized for this platform)"
            })
        
        # Hook type recommendation
        type_counts = library.get("type_distribution", {})
        if type_counts:
            for hook_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:2]:
                type_info = self.HOOK_TYPES.get(hook_type, {})
                recommendations.append({
                    "type": "hook_type",
                    "action": f"Prioritize '{hook_type}' hooks ({count} available)",
                    "rationale": type_info.get("description", "Effective hook style for this brand")
                })
        
        # Emotion diversity
        emotion_counts = library.get("emotion_distribution", {})
        if emotion_counts:
            dominant_emotion = max(emotion_counts, key=emotion_counts.get)
            emotion_desc = self.EMOTIONS.get(dominant_emotion, "")
            recommendations.append({
                "type": "emotion",
                "action": f"Lead with '{dominant_emotion}' emotion",
                "rationale": f"{emotion_desc} - Most prevalent in generated hooks"
            })
        
        return recommendations
    
    def get_hooks_for_brief(
        self,
        library: Dict[str, Any],
        platform: str = None,
        hook_type: str = None,
        emotion: str = None,
        min_strength: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Filter hooks for a specific creative brief.
        
        Args:
            library: Generated hooks library
            platform: Filter by platform (tiktok, instagram, facebook, youtube)
            hook_type: Filter by hook type
            emotion: Filter by target emotion
            min_strength: Minimum strength score
            
        Returns:
            Filtered list of hooks matching criteria
        """
        hooks = library.get("all_hooks", [])
        
        filtered = []
        for hook in hooks:
            # Strength filter
            if hook.get("strength_score", 0) < min_strength:
                continue
            
            # Platform filter
            if platform:
                platforms = hook.get("platform_fit", [])
                if isinstance(platforms, str):
                    platforms = [platforms]
                if not any(platform.lower() in p.lower() for p in platforms):
                    continue
            
            # Hook type filter
            if hook_type and hook.get("hook_type", "").lower() != hook_type.lower():
                continue
            
            # Emotion filter
            if emotion and hook.get("target_emotion", "").lower() != emotion.lower():
                continue
            
            filtered.append(hook)
        
        # Sort by strength
        filtered.sort(key=lambda x: x.get("strength_score", 0), reverse=True)
        
        return filtered


# Singleton instance
_hooks_service: Optional[HooksLibraryService] = None

def get_hooks_library_service() -> HooksLibraryService:
    """Get hooks library service instance."""
    global _hooks_service
    if _hooks_service is None:
        _hooks_service = HooksLibraryService()
    return _hooks_service
