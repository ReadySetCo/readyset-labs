# -*- coding: utf-8 -*-
"""
Full Funnel Creative Strategy Generator.
Synthesizes all research outputs (insights, angles, hooks, CTPs, ad analysis)
into a complete funnel strategy with persona architecture, funnel map, 90-day roadmap,
and the first 3 priority briefs.
"""

from typing import Dict, Any, List
import asyncio
from ..llm.client import get_llm_client


FUNNEL_STRATEGY_SYSTEM_PROMPT = """You are a senior performance creative strategist building a full-funnel creative strategy for a DTC brand on Meta.

Most accounts fail not because of bad ads but because of an incomplete funnel — too much budget concentrated at one awareness level, the same personas hit over and over, no system for bringing new audiences in at the top while converting warm ones at the bottom.

Your job is to produce a complete creative strategy document that a media buyer and a creative team can both execute from without a single follow-up question.

## OPERATING RULES

1. Strategy before execution. The funnel architecture comes first. Individual briefs follow from it.
2. Every creative decision must be justified. Do not recommend a format or awareness level without explaining why.
3. The funnel is not three ads. Full-funnel creative means multiple angles, multiple formats, and multiple personas operating across awareness levels simultaneously.
4. Frequency is a health metric. A healthy funnel maintains frequency between 2-4. Frequency above 5 means the top of the funnel is starved.
5. The system compounds. The goal is not to find one winning ad. The goal is to build a creative infrastructure where every dollar spent generates signal that makes the next brief better.

## AWARENESS LEVEL DEFINITIONS
- Unaware: doesn't know the problem exists — educate with content
- Problem Aware: knows the pain, hasn't searched for solutions — lead with the pain
- Solution Aware: knows solutions exist, comparing options — differentiate
- Product Aware: knows your product, hasn't bought — handle objections, build trust
- Most Aware: ready to buy — lead with offer, urgency, social proof

ALWAYS return valid JSON only. No markdown, no explanation."""


class FunnelStrategyGenerator:
    """Generates full-funnel creative strategy from all research data."""

    def __init__(self):
        self.llm = get_llm_client(provider="gemini")

    async def generate_strategy(
        self,
        brand_info: Dict[str, Any],
        ad_patterns: Dict[str, Any],
        insights: Dict[str, Any],
        competitor_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate a complete funnel strategy."""
        context = self._build_context(brand_info, ad_patterns, insights, competitor_data)

        print(f"       -> Generating Full Funnel Creative Strategy...")

        prompt = f"""Build a complete full-funnel creative strategy for {context['brand_name']}.

=== BRAND ===
Brand: {context['brand_name']}
Sector: {context['sector']}
Products: {context['products']}
Value Props: {context['value_props']}

=== CUSTOMER INTELLIGENCE ===
ICPs: {context['icps_summary']}
Pain Points: {context['pain_points_summary']}
Objections: {context['objections_summary']}
Purchase Triggers: {context['triggers_summary']}

=== CREATIVE INTELLIGENCE ===
Current Ad Patterns: {context['ad_patterns_summary']}
Hooks Library Size: {context['hooks_count']} hooks generated
Messaging Angles: {context['angles_summary']}
Competitor Landscape: {context['competitor_summary']}

=== CTP DATA (if available) ===
{context['ctp_summary']}

Return this exact JSON:
{{
    "account_diagnosis": {{
        "current_awareness_distribution": "Estimated % at each awareness level based on existing ad patterns",
        "identified_gaps": ["Specific gaps in the funnel — which levels are underserved"],
        "frequency_assessment": "What current frequency signals about funnel health",
        "biggest_creative_bottleneck": "The single biggest bottleneck preventing scale right now"
    }},

    "persona_architecture": [
        {{
            "persona_name": "A specific person, not a demographic (e.g., 'The Skeptical Researcher')",
            "description": "1-2 sentences: who they are, what situation they're in",
            "awareness_level": "Where they sit in the awareness spectrum",
            "primary_pain_or_desire": "The #1 thing driving them",
            "hook_direction": "One hook direction written specifically for this persona",
            "emotional_trigger": "The primary emotion to activate"
        }}
    ],

    "funnel_map": {{
        "top_of_funnel": {{
            "goal": "What TOF creative needs to accomplish",
            "awareness_levels": "Unaware to Problem Aware",
            "recommended_formats": ["Top 3 formats for this stage and why"],
            "angle_directions": ["2-3 angle directions to test"],
            "example_hook": "One example hook for this stage",
            "budget_allocation": "Recommended % of creative budget"
        }},
        "middle_of_funnel": {{
            "goal": "What MOF creative needs to accomplish",
            "awareness_levels": "Problem Aware to Solution Aware",
            "recommended_formats": ["Top 3 formats"],
            "angle_directions": ["2-3 angle directions"],
            "example_hook": "One example hook",
            "budget_allocation": "Recommended %"
        }},
        "bottom_of_funnel": {{
            "goal": "What BOF creative needs to accomplish",
            "awareness_levels": "Product Aware to Most Aware",
            "recommended_formats": ["Top 3 formats"],
            "offer_and_cta_direction": "How to structure the offer and CTA",
            "example_static_concept": "One example static ad concept",
            "budget_allocation": "Recommended %"
        }}
    }},

    "ninety_day_roadmap": {{
        "phase_1_foundation": {{
            "weeks": "1-4",
            "priority_angles": ["Which angles to test first and why"],
            "minimum_creative_volume": "How many creatives to produce",
            "signal_to_watch": "What signal you're looking for to validate"
        }},
        "phase_2_validation": {{
            "weeks": "5-8",
            "how_to_read_data": "How to interpret Phase 1 results",
            "scale_kill_iterate": "Decision framework: what to scale, kill, and iterate",
            "second_wave_directions": ["Brief directions for wave 2"]
        }},
        "phase_3_compounding": {{
            "weeks": "9-12",
            "winner_iteration": "How to iterate winners into new formats and hooks",
            "persona_expansion": "How to expand proven angles to new personas",
            "healthy_account_indicators": "What a compounding account looks like at this stage"
        }}
    }},

    "creative_tracker_setup": {{
        "naming_convention": "Recommended naming convention sortable by: persona, angle, format, awareness level, hook type",
        "example_ad_name": "One example ad name using the convention",
        "how_to_rank_by_angle": "How to rank ads by angle after 30 days of spend"
    }},

    "first_three_briefs": [
        {{
            "priority": 1,
            "angle": "The angle",
            "target_persona": "Which persona",
            "awareness_level": "Which funnel stage",
            "format": "Recommended format",
            "hook_direction": "The hook direction",
            "why_first": "Why this is the right brief to run first"
        }},
        {{
            "priority": 2,
            "angle": "Second priority angle",
            "target_persona": "Which persona",
            "awareness_level": "Which funnel stage",
            "format": "Format",
            "hook_direction": "Hook direction",
            "why_first": "Why this is second"
        }},
        {{
            "priority": 3,
            "angle": "Third priority angle",
            "target_persona": "Which persona",
            "awareness_level": "Which funnel stage",
            "format": "Format",
            "hook_direction": "Hook direction",
            "why_first": "Why this is third"
        }}
    ]
}}"""

        try:
            result = await asyncio.wait_for(
                self.llm.complete_json(prompt=prompt, system_prompt=FUNNEL_STRATEGY_SYSTEM_PROMPT, temperature=0.7),
                timeout=180.0
            )
            if result and isinstance(result, dict):
                print(f"          [OK] Funnel strategy generated")
                return result
            print(f"          [!] Funnel strategy returned invalid response")
            return self._create_fallback()
        except asyncio.TimeoutError:
            print(f"          [!] Funnel strategy timeout (180s)")
            return self._create_fallback()
        except Exception as e:
            print(f"          [!] Funnel strategy error: {str(e)[:100]}")
            return self._create_fallback()

    def _build_context(self, brand_info: Dict, ad_patterns: Dict, insights: Dict, competitor_data: Dict = None) -> Dict:
        """Build summarized context for strategy generation."""
        # Summarize ICPs
        icps = insights.get('ideal_customer_profiles', insights.get('icps', []))[:5]
        icps_summary = ', '.join(
            icp.get('name', icp.get('persona', 'Unknown')) for icp in icps if isinstance(icp, dict)
        ) or 'No ICPs identified'

        # Summarize pain points
        pains = insights.get('pain_points', [])[:8]
        pains_summary = ', '.join(
            (p.get('pain_point', p.get('name', str(p)))[:60] if isinstance(p, dict) else str(p)[:60])
            for p in pains
        ) or 'No pain points'

        # Summarize objections
        objs = insights.get('objections', [])[:5]
        objs_summary = ', '.join(
            o.get('objection', str(o))[:60] for o in objs if isinstance(o, dict)
        ) or 'No objections identified'

        # Summarize triggers
        triggers = insights.get('purchase_triggers', [])[:5]
        triggers_summary = ', '.join(
            (t.get('trigger', t.get('name', str(t)))[:60] if isinstance(t, dict) else str(t)[:60])
            for t in triggers
        ) or 'No triggers identified'

        # Ad patterns summary
        frameworks = list(ad_patterns.get('frameworks', {}).keys())[:5]
        hook_types = list(ad_patterns.get('hook_types', {}).keys())[:5]
        ad_summary = f"Frameworks: {', '.join(frameworks)}. Hook types: {', '.join(hook_types)}. Avg hook strength: {ad_patterns.get('avg_hook_strength', 'N/A')}/5"

        # Messaging angles
        angles = insights.get('messaging_angles', [])[:5]
        angles_summary = ', '.join(
            a.get('name', a.get('angle', str(a)))[:50] for a in angles if isinstance(a, dict)
        ) or 'No angles'

        # Competitor data
        comp_summary = 'No competitor data'
        if competitor_data and isinstance(competitor_data, dict):
            profiles = competitor_data.get('competitor_profiles', [])
            if profiles:
                comp_summary = ', '.join(p.get('name', 'Unknown') for p in profiles[:5] if isinstance(p, dict))

        # CTP data
        ctp_data = insights.get('ctp_data', [])
        ctp_summary = 'No CTP data available'
        if ctp_data and isinstance(ctp_data, list):
            ctp_names = [c.get('ctp_name', 'Unknown') for c in ctp_data if isinstance(c, dict)]
            ctp_summary = f"CTPs identified: {', '.join(ctp_names)}" if ctp_names else 'No CTPs'

        hooks_library = insights.get('hooks_library', {})
        hooks_count = hooks_library.get('total_hooks', 0) if isinstance(hooks_library, dict) else 0

        return {
            'brand_name': brand_info.get('name', 'Brand'),
            'sector': brand_info.get('sector', ''),
            'products': str(brand_info.get('products', ''))[:500],
            'value_props': str(brand_info.get('value_propositions', ''))[:500],
            'icps_summary': icps_summary,
            'pain_points_summary': pains_summary,
            'objections_summary': objs_summary,
            'triggers_summary': triggers_summary,
            'ad_patterns_summary': ad_summary,
            'hooks_count': hooks_count,
            'angles_summary': angles_summary,
            'competitor_summary': comp_summary,
            'ctp_summary': ctp_summary,
        }

    def _create_fallback(self) -> Dict[str, Any]:
        """Minimal fallback strategy."""
        return {
            "account_diagnosis": {"biggest_creative_bottleneck": "Insufficient data to diagnose — run full research first"},
            "persona_architecture": [],
            "funnel_map": {},
            "ninety_day_roadmap": {},
            "creative_tracker_setup": {},
            "first_three_briefs": [],
            "_fallback": True
        }
