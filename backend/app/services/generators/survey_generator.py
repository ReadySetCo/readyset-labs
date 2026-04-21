# -*- coding: utf-8 -*-
"""
Post-Purchase Survey Generator.
Designs post-purchase surveys that produce the language creative teams need
to write winning ads — not satisfaction ratings.
"""

from typing import Dict, Any
import asyncio
from ..llm.client import get_llm_client


SURVEY_SYSTEM_PROMPT = """You are a customer research strategist who designs post-purchase surveys for DTC brands running Meta ads.

Most post-purchase surveys ask questions the brand wants answered. Your surveys ask the questions that produce the language creative teams need to write winning ads. A survey that produces "great product, fast shipping" is useless. A survey that produces "I tried everything else for three years and nothing worked until this" is a brief.

## OPERATING RULES

1. Every question must be designed to produce quotable ad copy — not a satisfaction rating.
2. Open-ended over closed-ended. Scales and star ratings produce numbers. Numbers do not become hooks. Words do.
3. Target the moment of decision. The most valuable question in any post-purchase survey is: what almost stopped you from buying? The answer is your best hook.
4. Match questions to awareness levels. Some questions surface problem-aware language. Others surface solution-aware language. Design intentionally.
5. Brevity wins responses. Every question that does not produce creative-ready language should be cut. Five great questions beat fifteen average ones.

ALWAYS return valid JSON only. No markdown, no explanation."""


class SurveyGenerator:
    """Generates post-purchase survey questions designed to extract creative intelligence."""

    def __init__(self):
        self.llm = get_llm_client(provider="gemini")

    async def generate_survey(
        self,
        brand_info: Dict[str, Any],
        insights: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a complete post-purchase survey."""
        brand_name = brand_info.get('name', 'Brand')
        sector = brand_info.get('sector', '')
        products = str(brand_info.get('products', ''))[:300]

        # Summarize existing data for context
        pain_points = ', '.join(
            (p.get('pain_point', str(p))[:60] if isinstance(p, dict) else str(p)[:60])
            for p in insights.get('pain_points', [])[:5]
        ) or 'No pain points identified yet'

        objections = ', '.join(
            o.get('objection', str(o))[:60] for o in insights.get('objections', [])[:5] if isinstance(o, dict)
        ) or 'No objections identified yet'

        print(f"       -> Generating Post-Purchase Survey for {brand_name}...")

        prompt = f"""Generate a complete post-purchase survey designed to extract maximum creative intelligence for {brand_name}.

=== BRAND CONTEXT ===
Brand: {brand_name}
Sector: {sector}
Products: {products}

=== EXISTING RESEARCH (use to make questions category-specific) ===
Known Pain Points: {pain_points}
Known Objections: {objections}

Return this exact JSON:
{{
    "core_five": [
        {{
            "question": "The question exactly as it should appear to the customer",
            "creative_output_designed_for": "What type of creative output this question is designed to produce (e.g., 'Failed solution hooks', 'Transformation testimonials')",
            "awareness_level_surfaced": "Which awareness level language this typically surfaces (Problem Aware / Solution Aware / Product Aware)",
            "example_winning_response": "An example of the type of response that would become a winning hook"
        }}
    ],

    "category_specific_questions": [
        {{
            "question": "Category-specific question tailored to {sector}",
            "angle_it_surfaces": "Which creative angle this question is designed to surface",
            "how_to_use_in_brief": "How the response would be used in a creative brief"
        }}
    ],

    "single_best_question": {{
        "question": "The ONE question that, if answered honestly, produces the most powerful creative language in the entire survey",
        "why_its_the_best": "Why this question is the most valuable — what psychological mechanism it activates in the respondent"
    }},

    "survey_design_notes": {{
        "recommended_format": "Where and how to present this survey (email, in-app, post-checkout)",
        "recommended_timing": "When to send it relative to purchase/delivery",
        "opening_framing": "How to frame the opening line so customers understand why they're being asked — and feel motivated to give real answers, not polite ones",
        "framing_mistake_to_avoid": "The one framing mistake that kills response quality and how to avoid it"
    }}
}}"""

        try:
            result = await asyncio.wait_for(
                self.llm.complete_json(prompt=prompt, system_prompt=SURVEY_SYSTEM_PROMPT, temperature=0.7),
                timeout=120.0
            )
            if result and isinstance(result, dict):
                print(f"          [OK] Survey generated with {len(result.get('core_five', []))} core + {len(result.get('category_specific_questions', []))} category questions")
                return result
            return self._create_fallback(brand_name)
        except asyncio.TimeoutError:
            print(f"          [!] Survey generation timeout")
            return self._create_fallback(brand_name)
        except Exception as e:
            print(f"          [!] Survey generation error: {str(e)[:100]}")
            return self._create_fallback(brand_name)

    def _create_fallback(self, brand_name: str) -> Dict[str, Any]:
        """Minimal fallback survey."""
        return {
            "core_five": [
                {
                    "question": f"What almost stopped you from buying {brand_name}?",
                    "creative_output_designed_for": "Objection-handling hooks",
                    "awareness_level_surfaced": "Product Aware",
                    "example_winning_response": "I almost didn't buy because I'd been burned by [competitor] before"
                }
            ],
            "category_specific_questions": [],
            "single_best_question": {
                "question": f"What almost stopped you from buying {brand_name}?",
                "why_its_the_best": "The answer reveals the #1 purchase barrier — which becomes the strongest hook"
            },
            "survey_design_notes": {
                "recommended_format": "Post-delivery email",
                "recommended_timing": "3-5 days after delivery",
                "opening_framing": "We want to hear your honest experience — not a review, just the real story.",
                "framing_mistake_to_avoid": "Don't ask 'How satisfied are you?' — it produces politeness, not copy."
            },
            "_fallback": True
        }
