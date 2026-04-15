"""
LLM Prompts for Creative Target Persona (CTP) generation.
Stance classification, CTP refinement, and hypothesis layer generation.
"""

# ============ Stance Classification ============

STANCE_CLASSIFICATION_PROMPT = """You are classifying customer feedback snippets by GENERAL STANCE — the psychological worldview a person holds about the problem the product addresses.

General Stance is NOT about what triggered them or what blocks them. It's about HOW they fundamentally see, understand, and relate to the problem. Two people can both be triggered by "product_failure" but have completely different stances: one is a fatalist ("nothing works, it's genetic"), the other is a bio-hacker ("that product failed, but I'll find the right protocol").

STANCE TAXONOMY (use these when they fit, or propose a new one if the data clearly warrants it):

- "fatalist" — Believes the problem is inevitable/genetic/permanent. Has given up trying. "It runs in my family, there's nothing I can do."
- "skeptic" — Has tried multiple solutions, been burned by false promises. Demands hard proof. "I've tried everything and nothing works. Show me a real clinical study."
- "bio_hacker" — Proactive optimizer. Researches obsessively, stacks solutions, wants the science. "I'm running minoxidil + finasteride + microneedling + red light therapy."
- "desperate_seeker" — In acute pain/crisis, willing to try anything NOW. Emotional, urgent. "I'm losing my hair so fast, please help, I'll try anything."
- "passive_accepter" — Resigned but quietly open. Won't seek solutions actively but will try something easy/low-risk. "I guess it is what it is, but if there's something simple..."
- "social_conformist" — Driven by how others perceive them. Social pressure is the core motivator. "People at work have started noticing, I need to fix this before my wedding."
- "budget_pragmatist" — Wants to solve it but price/value is the lens for every decision. "Is this actually worth $50/month when I could just buy generic minoxidil?"
- "authority_follower" — Only trusts doctors, experts, official sources. Won't try anything without professional endorsement. "My dermatologist hasn't mentioned this, so I'm not touching it."

There are {num_snippets} snippets below. Classify EACH one.

{snippets_text}

For EACH snippet, identify:
- general_stance: The stance key from the taxonomy above, OR a new descriptive key if none fit (use snake_case)
- stance_label: Human-readable name for this stance (e.g., "The Fatalist", "The Skeptic")
- stance_belief: A first-person belief statement that captures this person's worldview (15-30 words)
- stance_confidence: 0.0-1.0

You MUST return a JSON array with EXACTLY {num_snippets} objects, one per snippet in order.

Example:
[
  {{"general_stance": "skeptic", "stance_label": "The Skeptic", "stance_belief": "I've been burned too many times by miracle products. Unless you show me real data, I'm not buying it.", "stance_confidence": 0.9}},
  {{"general_stance": "bio_hacker", "stance_label": "The Bio-Hacker", "stance_belief": "There's always a better protocol. I just need to find the right combination of treatments.", "stance_confidence": 0.85}}
]

Return ONLY the JSON array, no other text."""


# ============ CTP Refinement ============

CTP_REFINEMENT_PROMPT = """You are a consumer psychologist building a Creative Target Persona (CTP) from real customer review data.

BRAND: {brand_name}
STANCE: {stance_key} ({stance_label})
SNIPPET COUNT: {snippet_count} ({review_percentage:.0f}% of all reviews)

REPRESENTATIVE SNIPPETS FROM THIS STANCE:
{snippets_text}

EXISTING PAIN POINTS FROM DATABASE:
{pain_points_text}

EXISTING INTAKE CLASSIFICATIONS FOR THIS GROUP:
- Top triggers: {top_triggers}
- Top blockers: {top_blockers}
- Outcome distribution: {outcome_distribution}
- Proof types trusted: {proof_distribution}
- Top language cues: {top_language_cues}

Generate a complete CTP structure. Return JSON:

{{
    "ctp_name": "Brand-agnostic archetype label (e.g., 'The Skeptic', 'The Optimizer'). This is the cross-client learning handle — it should work for ANY product category, not just this one.",

    "core_insight_general_stance": "A first-person belief statement (CD6) that captures this person's worldview about the problem. Brand-agnostic. 15-30 words. Example: 'I've tried everything and nothing works. I need to see real clinical proof before I spend another dollar.'",

    "core_insight_product_anchored": "A near-verbatim quote from the snippets above that best captures how this person sees THIS SPECIFIC product. Pick the most representative real quote and lightly clean it up if needed. Keep it authentic.",

    "pain_points": [
        {{"pain_point": "Specific pain point", "frequency": 0, "sources": ["source1", "source2"]}}
    ],

    "barriers_objections": [
        {{"prompt": "A question or statement that captures this barrier/objection — written as something you'd put in an ad brief. E.g., 'If it worked, why hasn't my doctor recommended it?'", "type": "barrier|objection", "evidence": "Brief evidence from snippets"}}
    ],

    "kill_signals": {{
        "existence": ["Behavioral signals that this persona EXISTS in the market (e.g., 'Searching for problem + reddit', 'Joining specific subreddits')"],
        "engagement": ["Signals they are ACTIVELY ENGAGED (e.g., 'Reading multiple product reviews', 'Comparing ingredients lists')"],
        "conversion": ["Signals they are READY TO BUY (e.g., 'Looking for discount codes', 'Asking about money-back guarantee', 'Adding to cart and abandoning')]"
    }}
}}

IMPORTANT:
- barriers_objections: Provide exactly 4 items. Mix of barriers (structural "can't") and objections (belief-based "won't").
- kill_signals: Provide 2-4 signals per level.
- pain_points: Map from the database pain points above AND add any new ones you identify from the snippets. Include frequency count from the data.
- core_insight_product_anchored: Use a REAL quote from the snippets, not a fabricated one."""


# ============ Hypothesis Layer Generation ============

HYPOTHESIS_GENERATION_PROMPT = """You are a creative strategist generating hypothesis-layer suggestions for ad campaigns targeting a specific Creative Target Persona.

BRAND: {brand_name}
SECTOR: {sector}
VERTICAL: {vertical}

CTP: {ctp_name}
GENERAL STANCE (CD6): {core_insight}
WEIGHT: {weight}/10
SNIPPET COUNT: {snippet_count}

CTP PAIN POINTS:
{pain_points_text}

CTP BARRIERS/OBJECTIONS:
{barriers_text}

CTP KILL SIGNALS:
{kill_signals_text}

CTP TOP LANGUAGE CUES:
{language_cues_text}

AD LIBRARY PATTERNS (from brand's existing ads):
{ad_library_summary}

Generate the hypothesis layer for this CTP. This is a SUGGESTION for the Creative Strategist to validate at onboarding.

Return JSON:
{{
    "demographic_variables": {{
        "age_range": "Estimated age range",
        "gender_skew": "e.g., '60% Female' or 'Even split'",
        "income_level": "e.g., 'Middle to Upper-Middle'",
        "education": "e.g., 'College+' or 'Mixed'",
        "platform_affinity": ["Top 2-3 platforms where this persona is most active"],
        "geo_notes": "Any geographic skew observed or null"
    }},

    "angles": [
        {{
            "angle_name": "Descriptive angle name",
            "angle_description": "1-2 sentence description of the angle approach",
            "validation_tag": "data_backed|objection_driven|proof_type_match|language_pattern|hypothesis",
            "validation_evidence": "Brief evidence: what data supports this angle"
        }}
    ],

    "funnel_stage": {{
        "stage": "awareness|consideration|decision|retention",
        "rationale": "Why this CTP sits at this funnel stage based on their stance and behavior signals"
    }},

    "framework_tactic": {{
        "primary": "e.g., 'Problem-Agitate-Solution (PAS)'",
        "secondary": "e.g., 'Testimonial'",
        "rationale": "Why this framework fits this CTP's psychology"
    }},

    "visual_style": {{
        "style": "e.g., 'Documentary/Interview', 'UGC-native', 'Clinical/Clean', 'Before-After Split'",
        "rationale": "Why this visual style resonates with this CTP"
    }},

    "narrative_driver": {{
        "driver": "e.g., 'VO + Text', 'POV Story', 'Expert Interview', 'Montage'",
        "rationale": "Why this narrative approach fits"
    }},

    "tone": {{
        "primary": "e.g., 'Educational', 'Empathetic', 'Urgent', 'Aspirational'",
        "secondary": "e.g., 'Direct', 'Conversational'",
        "rationale": "Why this tone works for this CTP"
    }},

    "emotion": {{
        "arc": "e.g., 'Trust → Hope', 'Fear → Relief', 'Frustration → Curiosity'",
        "primary_emotion": "The dominant emotion to lead with",
        "rationale": "Why this emotional arc resonates"
    }}
}}

IMPORTANT:
- angles: Provide 3-5 angles. Each must have a validation_tag — prefer "data_backed" when you have strong evidence from snippets, "hypothesis" when it's a strategic guess.
- All rationale fields should reference the CTP's actual data (language cues, pain points, proof types, etc.), not generic strategy advice.
- This is meant to be a starting point for the CS team, not the final word. Be specific but acknowledge uncertainty."""
