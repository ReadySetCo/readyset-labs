# -*- coding: utf-8 -*-
"""
UGC Creator Brief Generator — Generates briefs for UGC creators, not production teams.
A creator brief is NOT a script. It's talking points, tone direction, and a non-negotiable hook
that a creator who has never heard of the brand can execute without a follow-up question.
"""

from typing import Dict, Any, List
import asyncio
from ..llm.client import get_llm_client


UGC_BRIEF_SYSTEM_PROMPT = """You are a performance creative producer who writes UGC briefs for Meta ads.

A bad brief produces bad footage no matter how good the creator is. Your briefs are not shot lists — they are creative strategies written in plain language that a creator who has never heard of this brand can execute without a single follow-up question. Every element of the brief must be justified by the customer data it came from.

## OPERATING RULES

1. The brief serves the angle — not the creator. Every instruction exists to protect the angle from being diluted in production.
2. Specificity prevents mistakes. Write every instruction as if you cannot be on the shoot to clarify it.
3. The hook is non-negotiable. The creator has freedom in the body — the opening 3 seconds must be executed as written. Make this clear.
4. Tone comes from awareness level. A solution-aware customer is sceptical. A problem-aware customer is frustrated. The creator's energy must match. Explain this to them.
5. Show don't tell. Instead of "seem relaxed," write "film in your kitchen like you're telling a friend something you just figured out."

## HOOK SELECTION BY AWARENESS LEVEL
- Pain-aware audience: lead with the problem, frustrated/urgent energy
- Solution-aware audience: lead with a failed solution, skeptical/knowing energy
- Product-aware audience: lead with a specific result or comparison, confident energy

## ABSOLUTE PROHIBITIONS
- Never write a full word-for-word script — creators sound robotic reading scripts
- Never use marketing jargon in talking points ("leverage", "innovative", "game-changing")
- Never leave tone direction vague ("be natural" — instead: "talk like you're at brunch telling your friend about this")
- Never skip the "what NOT to do" section — it prevents the most common UGC mistakes

ALWAYS return valid JSON only. No markdown, no explanation."""


class UGCBriefGenerator:
    """Generates UGC creator briefs using Gemini with research context."""

    def __init__(self):
        self.llm = get_llm_client(task_type="creative")

    async def generate_briefs(
        self,
        brand_info: Dict[str, Any],
        ad_patterns: Dict[str, Any],
        insights: Dict[str, Any],
        num_briefs: int = 3
    ) -> List[Dict[str, Any]]:
        """Generate UGC creator briefs ONE AT A TIME for reliability."""
        briefs = []
        context = self._build_context(brand_info, ad_patterns, insights)

        # Different angles for each brief
        angle_types = [
            ("Pain Point", "Problem Aware"),
            ("Failed Solution", "Solution Aware"),
            ("Transformation", "Problem Aware"),
            ("Social Proof", "Product Aware"),
            ("Curiosity / Discovery", "Unaware"),
        ][:num_briefs]

        print(f"       -> Generating {num_briefs} UGC creator briefs...")

        for i, (angle, awareness) in enumerate(angle_types):
            try:
                print(f"          Brief {i+1}/{num_briefs}: {angle} ({awareness})...")
                brief = await self._generate_single_brief(
                    context=context, angle_type=angle, awareness_level=awareness, brief_num=i + 1
                )
                if brief:
                    briefs.append(brief)
                    print(f"          [OK] Brief {i+1}: {brief.get('brief_name', 'Untitled')[:40]}")
                else:
                    print(f"          [!] Brief {i+1} returned None, using fallback")
                    briefs.append(self._create_fallback_brief(context['brand_name'], angle, i + 1))
            except asyncio.TimeoutError:
                print(f"          [!] Brief {i+1} timed out, using fallback")
                briefs.append(self._create_fallback_brief(context['brand_name'], angle, i + 1))
            except Exception as e:
                print(f"          [!] Brief {i+1} error: {str(e)[:80]}")
                briefs.append(self._create_fallback_brief(context['brand_name'], angle, i + 1))

        if not briefs:
            briefs = [self._create_fallback_brief(context['brand_name'], "Pain Point", 1)]

        print(f"       -> Generated {len(briefs)} UGC briefs total")
        return briefs

    def _build_context(self, brand_info: Dict, ad_patterns: Dict, insights: Dict) -> Dict:
        """Build context for UGC brief generation — reuses script generator's data patterns."""
        brand_name = brand_info.get('name', 'Brand')
        sector = brand_info.get('sector', '')
        products = str(brand_info.get('products', ''))[:500]
        value_props = str(brand_info.get('value_propositions', ''))[:500]

        # Pain points
        pain_points = []
        for p in insights.get('pain_points', [])[:10]:
            if isinstance(p, dict):
                pain_points.append(p.get('pain_point', p.get('name', str(p)))[:200])
            elif isinstance(p, str):
                pain_points.append(p[:200])

        # Verbatim quotes
        verbatims = []
        for q in insights.get('verbatim_quotes', [])[:15]:
            if isinstance(q, dict):
                verbatims.append(str(q.get('quote', q.get('text', '')))[:300])
            elif isinstance(q, str):
                verbatims.append(q[:300])

        # Customer language
        language = []
        for phrase in insights.get('customer_language', [])[:10]:
            if isinstance(phrase, str) and phrase.strip():
                language.append(phrase[:150])
            elif isinstance(phrase, dict):
                language.append(phrase.get('phrase', str(phrase))[:150])

        # Objections
        objections = []
        for o in insights.get('objections', [])[:5]:
            if isinstance(o, dict):
                obj = o.get('objection', o.get('concern', ''))[:200]
                counter = o.get('counter_message', o.get('counter_messaging', ''))[:200]
                if obj:
                    objections.append(f"{obj} → Counter: {counter}" if counter else obj)

        # ICPs
        icps = []
        for icp in insights.get('ideal_customer_profiles', insights.get('icps', []))[:3]:
            if isinstance(icp, dict):
                name = icp.get('name', icp.get('persona', ''))
                pain = icp.get('primary_pain', icp.get('pain_points', ''))
                if isinstance(pain, list):
                    pain = ', '.join(str(p)[:50] for p in pain[:2])
                icps.append(f"{name}: {str(pain)[:150]}")

        return {
            'brand_name': brand_name,
            'sector': sector,
            'products': products,
            'value_props': value_props,
            'pain_points': pain_points,
            'verbatims': verbatims,
            'customer_language': language,
            'objections': objections,
            'icps': icps,
        }

    async def _generate_single_brief(
        self, context: Dict, angle_type: str, awareness_level: str, brief_num: int
    ) -> Dict[str, Any]:
        """Generate one UGC creator brief."""

        prompt = f"""Generate ONE complete UGC creator brief for {context['brand_name']}.

=== BRAND ===
Brand: {context['brand_name']}
Sector: {context['sector']}
Products: {context['products']}
Value Props: {context['value_props']}

=== ICPs ===
{chr(10).join('- ' + icp for icp in context['icps']) if context['icps'] else '- General audience'}

=== PAIN POINTS ===
{chr(10).join('- ' + p for p in context['pain_points']) if context['pain_points'] else '- Common category frustrations'}

=== CUSTOMER LANGUAGE (use these EXACT phrases in talking points) ===
{chr(10).join('- "' + l + '"' for l in context['customer_language']) if context['customer_language'] else '- Natural conversational language'}

=== VERBATIM QUOTES (the hook MUST use one of these) ===
{chr(10).join('- "' + v + '"' for v in context['verbatims'][:10]) if context['verbatims'] else '- No verbatims available'}

=== OBJECTIONS (address one naturally) ===
{chr(10).join('- ' + o for o in context['objections']) if context['objections'] else '- Price/value concern'}

=== CREATIVE DIRECTION ===
Angle: {angle_type}
Awareness Level: {awareness_level}
Platform: TikTok / Instagram Reels

Return this exact JSON:
{{
    "brief_name": "Short internal name for this brief",
    "angle_type": "{angle_type}",
    "awareness_level": "{awareness_level}",
    "target_persona": "One specific person in a specific situation — not a demographic",

    "overview": "3 sentences MAX: what this ad is trying to do, who it speaks to, what emotional shift it creates",

    "hook_non_negotiable": {{
        "exact_line": "The EXACT opening line, word-for-word as the creator must deliver it. Built from customer verbatims.",
        "visual_direction": "What the creator should be doing visually in the first 2-3 seconds (setting, framing, body language)",
        "what_not_to_do": "What the creator must NOT do in the opening (e.g., 'Do NOT smile. Do NOT start with the product in frame.')",
        "energy": "The creator's energy in one phrase (e.g., 'exhausted but hopeful', 'skeptical friend at brunch', 'genuinely surprised')"
    }},

    "body_talking_points": [
        "Talking point 1 — key idea to hit, in the creator's own natural words",
        "Talking point 2 — what to say next, with the emotional shift noted",
        "Talking point 3 — where to bring in the product naturally",
        "Talking point 4 — address the objection without sounding defensive"
    ],

    "must_say_verbatim": ["Exact phrase from customer language that MUST appear word-for-word", "Another phrase"],

    "emotional_journey": "The creator's energy arc: e.g., 'Start frustrated/tired → shift to curious → land on relieved/confident'",

    "close": {{
        "how_it_ends": "How the ad ends — what the creator does and says",
        "cta_language": "Specific CTA words to use",
        "cta_energy": "The energy of the close (e.g., 'casual recommendation, not a hard sell')"
    }},

    "production_notes": {{
        "setting": "Where to film and WHY (e.g., 'bathroom mirror — this is where the pain happens')",
        "wardrobe": "What to wear and why (e.g., 'everyday clothes, no makeup — authenticity over polish')",
        "what_to_avoid": ["Common UGC mistake 1 to avoid", "Mistake 2", "Mistake 3"],
        "platform_notes": "TikTok/Reels specific: vertical, captions on, hook in first 1.5s"
    }},

    "what_success_looks_like": "One paragraph describing the finished video if the brief was executed correctly — what it feels like to watch, what the viewer thinks, and why they don't scroll past."
}}"""

        try:
            result = await asyncio.wait_for(
                self.llm.complete_json(prompt=prompt, system_prompt=UGC_BRIEF_SYSTEM_PROMPT, temperature=0.75),
                timeout=120.0
            )
            if result and isinstance(result, dict):
                result['brief_num'] = brief_num
                return result
            return None
        except asyncio.TimeoutError:
            raise
        except Exception as e:
            print(f"          [!] UGC Brief LLM error: {str(e)[:100]}")
            raise

    def _create_fallback_brief(self, brand_name: str, angle_type: str, num: int) -> Dict[str, Any]:
        """Create fallback UGC brief."""
        return {
            "brief_name": f"{angle_type} UGC Brief #{num}",
            "angle_type": angle_type,
            "awareness_level": "Problem Aware",
            "target_persona": "Someone actively frustrated with current solutions in this category",
            "overview": f"This ad targets someone who knows they have a problem but hasn't found {brand_name} yet. The creator shares their genuine frustration and discovery moment.",
            "hook_non_negotiable": {
                "exact_line": "Okay so I need to talk about this because I was literally about to give up.",
                "visual_direction": "Direct to camera, slightly messy/real setting, no product visible yet",
                "what_not_to_do": "Do NOT smile. Do NOT start with the product. Do NOT use a ring light.",
                "energy": "Exhausted but about to share something important"
            },
            "body_talking_points": [
                "Share what you were struggling with (be specific, not vague)",
                "Mention what you tried before that didn't work",
                f"How you found {brand_name} (keep it casual — a friend told me, I saw it on my feed)",
                "The specific moment you realized it was working"
            ],
            "must_say_verbatim": [],
            "emotional_journey": "Frustrated/tired → curious/skeptical → genuinely surprised → relieved",
            "close": {
                "how_it_ends": "Direct to camera, product casually visible, natural recommendation",
                "cta_language": f"Seriously just try {brand_name}. Link in bio.",
                "cta_energy": "Casual friend recommendation — not a hard sell"
            },
            "production_notes": {
                "setting": "Wherever the problem naturally happens — kitchen, bathroom, desk",
                "wardrobe": "Everyday clothes, no styling — authenticity over polish",
                "what_to_avoid": ["Over-produced lighting", "Reading from a script", "Holding product in frame for the entire video"],
                "platform_notes": "9:16 vertical, captions always on, hook must land in first 1.5s"
            },
            "what_success_looks_like": f"The finished video feels like a friend texting you about something they just discovered. The viewer sees themselves in the creator's frustration, believes the discovery was organic, and taps through to {brand_name} because the recommendation feels earned — not sponsored.",
            "brief_num": num,
            "_fallback": True
        }
