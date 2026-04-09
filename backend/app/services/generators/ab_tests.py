# -*- coding: utf-8 -*-
"""
A/B Test Suggester - Lightweight, reliable test suggestions.
"""

import asyncio
from typing import Dict, Any, List
from ..llm.client import get_llm_client


class ABTestSuggester:
    """Generates A/B test suggestions with simple, reliable prompts."""
    
    def __init__(self):
        self.llm = get_llm_client()
    
    async def suggest_tests(
        self,
        brand_info: Dict[str, Any],
        ad_patterns: Dict[str, Any],
        insights: Dict[str, Any],
        competitor_data: Dict[str, Any] = None,
        num_tests: int = 3
    ) -> List[Dict[str, Any]]:
        """Generate A/B test suggestions using real Ad Library data."""
        
        brand_name = brand_info.get('name', 'Brand')[:50]
        
        # Get pain points
        pain_points = insights.get('pain_points', [])[:5]
        pain_text = '\n'.join([f"• {str(p.get('pain_point', p) if isinstance(p, dict) else p)[:80]}" for p in pain_points]) or "general improvements"
        
        # Get objections with counters
        objections = insights.get('objections', [])[:5]
        objection_text = '\n'.join([
            f"• OBJECTION: \"{o.get('objection', str(o))[:60]}\" → COUNTER: {o.get('counter_message', o.get('counter', 'N/A'))[:80]}"
            for o in objections if isinstance(o, dict)
        ]) or "No objections analyzed"
        
        # Get Ad Library data
        ad_examples = ad_patterns.get('ad_examples', {})
        
        # Frameworks that work
        frameworks = list(ad_patterns.get('frameworks', {}).keys())[:5]
        frameworks_text = ', '.join(frameworks) if frameworks else "Problem-Solution, Testimonial"
        
        # Hook types that work
        hook_types = list(ad_patterns.get('hook_types', {}).keys())[:5]
        hooks_text = ', '.join(hook_types) if hook_types else "Question, Statement"
        
        # Emotions that work
        emotions = list(ad_patterns.get('emotions', {}).keys())[:5]
        emotions_text = ', '.join(emotions) if emotions else "Curiosity, Relief"
        
        # Best hooks from analyzed ads
        best_hooks = []
        for h in ad_examples.get('best_hooks', [])[:5]:
            best_hooks.append(f"• \"{h.get('hook', '')[:100]}\" (Strength: {h.get('strength', 0)}/5, {h.get('framework', '')})")
        hooks_examples = '\n'.join(best_hooks) if best_hooks else "No hooks analyzed"
        
        # CTAs from ads
        ctas = []
        for ad in ad_examples.get('brand_ads', [])[:10]:
            if ad.get('cta'):
                ctas.append(ad['cta'][:50])
        ctas_text = ', '.join(list(set(ctas))[:5]) if ctas else "Shop Now, Learn More"
        
        print(f"       -> Generating {num_tests} A/B test ideas (using {len(frameworks)} frameworks, {len(best_hooks)} hooks)...")
        
        prompt = f"""Suggest {num_tests} data-driven A/B tests for {brand_name} video ads.

=== WHAT'S WORKING (from analyzed ads) ===
Winning Frameworks: {frameworks_text}
Hook Types: {hooks_text}
Emotions: {emotions_text}
CTAs used: {ctas_text}

=== TOP HOOKS FROM SUCCESSFUL ADS ===
{hooks_examples}

=== CUSTOMER PAIN POINTS ===
{pain_text}

=== OBJECTIONS TO ADDRESS ===
{objection_text}

=== TASK ===
Create {num_tests} A/B tests that:
1. Test variables identified from the actual ad data (frameworks, hooks, emotions)
2. Address specific pain points or objections
3. Are practical to implement and measure

Return JSON array:
[
    {{
        "test_name": "Short descriptive name",
        "hypothesis": "If we [change X] then [metric] will improve because [reason based on data above]",
        "variant_a": "Control version - describe specifically",
        "variant_b": "Test version - describe specifically", 
        "element_being_tested": "Hook/Framework/CTA/Emotion/Objection/etc",
        "metric_to_track": "Hook Rate/CTR/CVR/Watch Time/etc",
        "expected_impact": "High/Medium/Low",
        "implementation_effort": "Low/Medium/High",
        "data_supporting_test": "What from the analysis above supports this test"
    }}
]"""

        try:
            result = await asyncio.wait_for(
                self.llm.complete_json(prompt=prompt, temperature=0.7),
                timeout=30.0  # 30s timeout for A/B tests
            )
            
            if result and isinstance(result, list):
                print(f"       -> Generated {len(result)} A/B test ideas")
                return result[:num_tests]
            elif result and isinstance(result, dict):
                for key in ["tests", "ab_tests", "suggestions"]:
                    if key in result and isinstance(result[key], list):
                        return result[key][:num_tests]
        
        except asyncio.TimeoutError:
            print(f"       [!] A/B test generation timeout")
        except Exception as e:
            print(f"       [!] A/B test generation failed: {e}")
        
        # Fallback tests
        print(f"       -> Using fallback A/B tests")
        return self._generate_fallbacks(num_tests)
    
    def _generate_fallbacks(self, num: int) -> List[Dict[str, Any]]:
        """Generate fallback test suggestions."""
        fallbacks = [
            {
                "test_name": "Hook Style Test",
                "hypothesis": "Question hooks perform better than statement hooks",
                "variant_a": "Statement hook opening",
                "variant_b": "Question hook opening",
                "metric_to_track": "Hook rate (3s views / impressions)",
                "expected_impact": "High",
                "implementation_effort": "Low"
            },
            {
                "test_name": "CTA Urgency Test",
                "hypothesis": "Adding urgency to CTA increases conversions",
                "variant_a": "Standard CTA: 'Shop now'",
                "variant_b": "Urgent CTA: 'Limited time - shop now'",
                "metric_to_track": "CTR",
                "expected_impact": "Medium",
                "implementation_effort": "Low"
            },
            {
                "test_name": "Social Proof Test",
                "hypothesis": "Adding customer quote increases trust",
                "variant_a": "No social proof",
                "variant_b": "Customer testimonial quote overlay",
                "metric_to_track": "CVR",
                "expected_impact": "Medium",
                "implementation_effort": "Medium"
            }
        ]
        return fallbacks[:num]
    
    async def prioritize_tests(
        self,
        tests: List[Dict[str, Any]],
        constraints: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Simple prioritization based on impact/effort."""
        impact_scores = {"High": 3, "Medium": 2, "Low": 1}
        effort_scores = {"Low": 3, "Medium": 2, "High": 1}
        
        for test in tests:
            impact = impact_scores.get(test.get('expected_impact', 'Medium'), 2)
            effort = effort_scores.get(test.get('implementation_effort', 'Medium'), 2)
            test['priority_score'] = impact * effort
        
        return sorted(tests, key=lambda x: x.get('priority_score', 0), reverse=True)
    
    async def generate_test_roadmap(
        self,
        prioritized_tests: List[Dict[str, Any]],
        timeline_weeks: int = 12
    ) -> Dict[str, Any]:
        """Generate simple test roadmap."""
        weeks_per_test = max(2, timeline_weeks // len(prioritized_tests)) if prioritized_tests else 4
        
        roadmap = []
        for i, test in enumerate(prioritized_tests):
            roadmap.append({
                "test": test.get('test_name', f'Test {i+1}'),
                "week_start": i * weeks_per_test + 1,
                "week_end": (i + 1) * weeks_per_test
            })
        
        return {"roadmap": roadmap, "total_weeks": timeline_weeks}
    
    async def analyze_test_results(self, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simple test result analysis."""
        return {
            "recommendation": "Continue testing with more variations",
            "confidence": "Medium",
            "next_steps": ["Run for more impressions", "Test additional variants"]
        }
