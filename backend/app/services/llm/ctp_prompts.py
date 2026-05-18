"""
LLM Prompts for Creative Target Persona (CTP) generation.

Stance classification, CTP refinement, and hypothesis layer generation. Every
prompt is grounded in a `brand_context_block` rendered from real pipeline data
(see backend/app/services/brand_context.py). The LLM is told to interpret
abstract stances through that brand-specific context — no category-specific
examples (hair-loss, finance, etc.) are baked into the prompts themselves.
"""

# ============ Stance Classification ============

STANCE_CLASSIFICATION_PROMPT = """You are classifying customer voice-of-customer snippets by GENERAL STANCE — the psychological worldview a person holds about the problem the brand below addresses.

Read the brand context FIRST. Your stance interpretations must be grounded in this brand's category, audience, and customer language — not in generic examples. Two customers can be triggered by the same thing but see it through completely different worldviews; that's what stance captures.

{brand_context_block}

---

# STANCE TAXONOMY

You MUST classify each snippet using one of these 8 abstract stance keys. The descriptions are deliberately generic — interpret them through THIS brand's category and the verbatim customer language above. Do NOT invent new keys.

- "fatalist" — Believes the problem is inevitable / structural / out of their control. Has stopped actively trying. Tone: resigned, accepting.
- "skeptic" — Has been disappointed by similar products or claims before. Demands hard proof, side-by-side data, or independent validation before acting.
- "bio_hacker" — Proactive optimizer. Researches obsessively, layers solutions, follows ingredient lists / specs / mechanisms. Engages on the "how does this work" level.
- "desperate_seeker" — In acute pain or time pressure. Emotionally urgent. Will try almost anything that promises relief soon.
- "passive_accepter" — Quietly resigned but open. Won't seek solutions actively but will adopt something easy/low-risk if it crosses their path.
- "social_conformist" — Driven primarily by how others perceive them, peer dynamics, social proof, status, or aesthetic conformity.
- "budget_pragmatist" — Price/value is the primary lens. Always comparing cost-per-unit, weighing alternatives, sensitive to subscription pricing.
- "authority_follower" — Trusts experts, professionals, official sources. Won't act on peer or marketing claims alone — needs an authority sign-off.

If a snippet genuinely doesn't fit any of these, return general_stance="unknown" with stance_confidence < 0.5 — it will be dropped downstream rather than forcefit.

---

There are {num_snippets} snippets below. Classify EACH one.

{snippets_text}

For EACH snippet, return:
- general_stance: EXACTLY one of: fatalist, skeptic, bio_hacker, desperate_seeker, passive_accepter, social_conformist, budget_pragmatist, authority_follower, unknown
- stance_label: A SHORT (3-7 words) distinctive phrase grounded in THIS snippet's actual language and the brand context above. Must be specific to what the person is actually doing/feeling/saying. NEVER use generic archetype names like "The Skeptic", "The Bio-Hacker", "The Authority Seeker" — those repeat across every brand and convey nothing. Good labels reference brand category, behavior, or product detail; pull vocabulary from the snippet itself or the brand context.
- stance_belief: First-person belief sentence (15-30 words) using vocabulary from the snippet itself when possible.
- stance_confidence: 0.0-1.0. Use < 0.6 freely when the snippet doesn't strongly express any worldview — those will be dropped from clustering.

Return a JSON array with EXACTLY {num_snippets} objects in input order.

Return ONLY the JSON array."""


# ============ CTP Refinement ============

CTP_REFINEMENT_PROMPT = """You are a consumer psychologist building a Creative Target Persona (CTP) for {brand_name} from real customer voice-of-customer data.

Read the brand context FIRST. Every part of the CTP you generate must be grounded in this brand's reality (category, audience, customer language, ad-library observations) — not in generic templates.

{brand_context_block}

---

# THIS CTP

This CTP comes from clustering snippets that share the abstract stance "{stance_key}" (n={snippet_count}, ≈{review_percentage:.0f}% of classified snippets).

REPRESENTATIVE SNIPPETS FROM THIS CLUSTER:
{snippets_text}

INTAKE-ENGINE DISTRIBUTIONS FOR THIS CLUSTER (orthogonal to stance):
- Top triggers: {top_triggers}
- Top blockers: {top_blockers}
- Outcome levels: {outcome_distribution}
- Proof types trusted: {proof_distribution}
- Top language cues: {top_language_cues}

DATABASE-LEVEL PAIN POINTS (already extracted by earlier insight pipeline; merge into your output, do not invent):
{pain_points_text}

CANDIDATE BRAND HOOKS (you may select from these or write new ones grounded in this CTP):
{hook_candidates_text}

CANDIDATE BRAND VALUE PROPS (you may select from these or write new ones grounded in this CTP):
{value_prop_candidates_text}

---

# OUTPUT

Return a single JSON object with these fields:

{{
  "ctp_name": "A SHORT distinctive name (3-7 words) for THIS specific {brand_name} customer. MUST reference brand category + behavior or belief grounded in the snippets above. FORBIDDEN: generic archetype labels like 'The Skeptic', 'The Optimizer', 'The Seeker', 'The Authority Seeker', 'The Value Seeker', 'The Community Seeker', 'The Discerning Evaluator', 'The Bio-Hacker', 'The Fatalist', 'The Realist', 'The Enthusiast'. Those say nothing distinctive and repeat across brands. Good names encode brand+behavior, e.g. 'Burned-by-Generic Hims Veteran', 'Trader-Joe's Loyalist Eyeing Phlur', 'Refi Math Optimizer Watching Rates', 'Postpartum Hers Trier Looking for Proof'.",

  "core_insight_general_stance": "First-person belief (15-30 words) capturing this person's worldview about the problem. Use customer-language vocabulary from the snippets, not abstract MBA-speak.",

  "core_insight_product_anchored": "A near-verbatim quote from the snippets above that best captures how this person sees {brand_name}. Pick the most representative real quote, lightly cleaned.",

  "pain_points": [
    {{"pain_point": "Specific pain described in customer's own words", "frequency": <int from data>, "sources": ["source_type1", "source_type2"]}}
  ],

  "desires": [
    "Specific aspiration this person has about {brand_name} or its category. Phrase as something they'd say or wish for. Ground in snippet vocabulary."
  ],

  "barriers_objections": [
    {{"prompt": "Question or statement capturing the barrier/objection — written like ad-brief copy", "type": "barrier|objection", "evidence": "Brief evidence from snippets"}}
  ],

  "recommended_hooks": [
    {{"hook": "Hook copy that would land for THIS CTP", "source": "from_brand_library|new_for_this_ctp", "rationale": "Why it lands for this CTP — reference snippets/cues"}}
  ],

  "recommended_value_props": [
    {{"value_prop": "Value prop framed for THIS CTP", "source": "from_brand_library|new_for_this_ctp", "rationale": "Why it resonates with this CTP's psychology"}}
  ],

  "kill_signals": {{
    "existence":  ["Behavioral signals this persona EXISTS in the market"],
    "engagement": ["Signals this persona is ACTIVELY ENGAGED with {brand_name}'s category"],
    "conversion": ["Signals this persona is READY TO BUY"]
  }}
}}

# RULES

- ctp_name: re-read the FORBIDDEN list. If your first instinct is in that list, you haven't done the work. Look at what these snippets actually say.
- pain_points: 3-5 items. Pull frequency from data when possible.
- desires: 3 items. Each must read like something this customer would actually say or wish for, not a corporate aspiration.
- barriers_objections: exactly 4. Mix barriers (structural "can't") and objections (belief "won't").
- recommended_hooks: exactly 3. Each tagged "from_brand_library" if drawn from the candidate hooks above OR "new_for_this_ctp" if you wrote it.
- recommended_value_props: exactly 3. Same source-tagging rule.
- kill_signals: 2-4 per level.
- core_insight_product_anchored: must be a REAL quote from the snippets. Do not fabricate.

Return ONLY the JSON object."""


# ============ Archetype Discovery (NEW — replaces forced 8-bucket clustering) ============

CTP_DISCOVERY_PROMPT = """You are a senior consumer-psychology researcher reading the FULL data corpus for {brand_name}. Your job is to DISCOVER the customer archetypes that genuinely emerge from this data — not to fit customers into a predefined taxonomy.

Read everything below carefully. Ground every archetype you propose in the actual snippets, ad observations, and brand context. If an archetype isn't supported by ≥10 distinct snippets across at least 2 sources, do NOT include it.

# BRAND + VOC + COMPETITIVE CONTEXT
{brand_block}

# VOICE-OF-CUSTOMER SNIPPETS (numbered — reference by index in your output)
Each line: [INDEX] (metadata) "content"
The metadata includes: source, the abstract psychographic stance the per-snippet classifier assigned (one of 8: fatalist/skeptic/bio_hacker/desperate_seeker/passive_accepter/social_conformist/budget_pragmatist/authority_follower), confidence, intake-engine tags (trigger/blocker/outcome/proof/cues).

Treat the stance tag as ONE signal, not as a constraint. Real archetypes often span multiple stances or split a single stance into behaviorally distinct groups. You are free to invent archetype names and structures that no taxonomy contains, AS LONG AS the snippets support them.

{snippets_block}

# AD-LIBRARY OBSERVATIONS (per-ad analyzer output — what the brand is currently saying)
Each line: [AD#N] structured analyzer fields :: "ad copy"
{ads_block}

---

# DELIVERABLE

Discover 3–7 archetypes. Output a JSON object with this exact shape:

{{
  "rationale": "2-4 sentences explaining WHY exactly this number of archetypes emerged from the data. Mention any borderline ones you considered and rejected, and the threshold reasoning.",
  "archetypes": [
    {{
      "name": "A 3-7 word name that captures the DISTINCTIVE BEHAVIOR or PSYCHOLOGY of this archetype. Two hard rules: (1) FORBIDDEN generic labels — 'The Skeptic', 'The Optimizer', 'The Seeker', 'The Authority Seeker', 'The Value Seeker', 'The Community Seeker', 'The Discerning Evaluator', 'The Bio-Hacker', 'The Fatalist', 'The Realist', 'The Enthusiast'. They say nothing and repeat across brands. (2) DO NOT mechanically prepend or include '{brand_name}' as a lazy specificity marker (e.g., '{brand_name} Compliment-Chasing Wearer' — the brand name adds NO information here, the BEHAVIOR is what's distinctive). The brand name should ONLY appear if removing it would change the meaning of the segment — for example a name referencing a specific product, a discontinued line, or a brand-defining product feature. Good names describe what these customers DO, NOT just attach the brand. Examples of good names (note how the brand is implicit, not stuffed): 'Layering-and-Longevity Routine Builders', 'Compliment-Chasing Wedding-Day Wearers', 'Old-Formula Revival Loyalists' (brand era IS the segment), 'Decant-Tuesday Spreadsheet Buyers', 'Burned-by-Generic-Rx Veterans', 'Refi-Math Optimizers Watching Rates'.",

      "psychology": "3-5 sentences of psychological texture: how this person sees the problem, what they believe, what scares them, what excites them. Use vocabulary FROM THE SNIPPETS. Cite specific snippets parenthetically — e.g., '(see [12], [47], [89])'.",

      "behavioral_markers": [
        "Concrete observable behaviors that distinguish this archetype — purchasing patterns, search behavior, content consumed, decision rituals. 4-7 items. Each must be inferrable from the snippets, not invented."
      ],

      "snippet_indexes": [<integers>],
      "evidence_quotes": [
        "<verbatim quotes from the indexed snippets that PROVE this archetype exists>",
        "<at least 3, up to 6, from different sources if possible>"
      ],

      "source_distribution_signal": {{
        "<source_type_1>": <count>,
        "<source_type_2>": <count>
      }},

      "stance_tags": ["<which of the 8 abstract stances overlap with this archetype — can be 0, 1, or 2>"],

      "ad_alignment": [<integers — which AD#N indexes (if any) seem aimed at this archetype>],

      "estimated_share_pct": <number between 0 and 100 — what % of this brand's audience this archetype likely represents>,

      "counter_segment": "1-sentence description of who is NOT this archetype — to keep boundaries clear",

      "what_makes_them_unique": "1-2 sentences. The single most distinctive thing that separates this archetype from the others, in the actual data."
    }}
  ]
}}

# RULES

- snippet_indexes: at minimum 10 snippets per archetype, ideally 20-50. The indexes MUST exist in the snippets above.
- evidence_quotes: pull verbatim from those indexed snippets, not paraphrased.
- DO NOT force-fit. If only 4 archetypes are clearly supported by data, return 4. If 7 are clearly supported, return 7. Never return 8 (we don't want a one-per-stance fit).
- DO NOT invent psychology that the snippets don't show. If the data is shallow, say so in rationale.
- The same snippet CAN be referenced by 2 archetypes if it genuinely straddles. But each snippet's primary archetype should be unique.

Return ONLY the JSON object."""


# ============ Deep Per-Archetype CTP Construction ============

CTP_DEEP_ENRICHMENT_PROMPT = """You are building a deeply textured Creative Target Persona for {brand_name}, focused on the discovered archetype below. You have the FULL set of snippets attributed to this archetype, the brand context, and the ads currently aimed at this group. Use all of it.

# DISCOVERED ARCHETYPE TO BUILD OUT
Name: {archetype_name}
Psychology: {archetype_psychology}
Behavioral markers: {archetype_behavioral_markers}
Counter-segment: {archetype_counter_segment}
What makes them unique: {archetype_unique}
Stance tags (abstract psychographic overlap): {archetype_stance_tags}

# BRAND + COMPETITIVE CONTEXT
{brand_block}

# ALL ATTRIBUTED SNIPPETS FOR THIS ARCHETYPE
Each line: [INDEX] (metadata) "content"
{archetype_snippets_block}

# CANDIDATE BRAND HOOKS (you may select from these or write new ones)
{hook_candidates_text}

# CANDIDATE BRAND VALUE PROPS (you may select from these or write new ones)
{value_prop_candidates_text}

# ADS TARGETING THIS ARCHETYPE (current creative direction)
{ads_for_archetype_block}

---

Return a single JSON object. Use vocabulary FROM the snippets. Cite snippet indexes when claiming evidence. Do NOT generalize — be specific to this {brand_name} customer.

{{
  "ctp_name": "Same name as archetype, OR refine if you see a sharper one. Must describe BEHAVIOR/PSYCHOLOGY specifically. DO NOT mechanically prepend '{brand_name}' to the name — the brand name should appear ONLY if removing it changes the meaning (e.g., when referring to a specific product line or brand era). The reader knows which brand this is — they're reading {brand_name}'s deck.",

  "core_insight_general_stance": "First-person belief statement (15-30 words) capturing this person's worldview. Use THEIR vocabulary.",

  "core_insight_product_anchored": "A near-verbatim quote from the snippets that captures how this person sees {brand_name}. Cite snippet index. Lightly cleaned only.",

  "behavioral_markers": [
    "<copy/refine from the discovery output, with snippet citations>"
  ],

  "decision_factors": [
    {{
      "factor": "<what they weight when deciding>",
      "priority": "<high|medium|low based on snippet density>",
      "evidence": "<snippet index reference + verbatim phrase>"
    }}
  ],

  "vocabulary": [
    "<exact verbatim phrases this archetype uses — 8-15 items, distinctive ones, not generic English>"
  ],

  "pain_points": [
    {{
      "pain_point": "<specific pain in customer vocabulary>",
      "frequency": <int approx count from snippets>,
      "evidence_indexes": [<snippet indexes>]
    }}
  ],

  "desires": [
    {{
      "desire": "<aspiration in customer vocabulary>",
      "evidence_indexes": [<snippet indexes>]
    }}
  ],

  "barriers_objections": [
    {{
      "type": "barrier|objection",
      "prompt": "<question/statement an ad would need to address>",
      "evidence_indexes": [<snippet indexes>]
    }}
  ],

  "recommended_hooks": [
    {{
      "hook": "<hook copy>",
      "source": "from_brand_library|new_for_this_ctp",
      "rationale": "<why it lands for this archetype, citing snippet indexes>"
    }}
  ],

  "recommended_value_props": [
    {{
      "value_prop": "<prop framed for this archetype>",
      "source": "from_brand_library|new_for_this_ctp",
      "rationale": "<why it resonates>"
    }}
  ],

  "frameworks_that_resonate": [
    {{
      "framework": "<concrete framework e.g. Founder Story, Mythbusting, Comparison>",
      "rationale": "<why grounded in this archetype's psychology>"
    }}
  ],

  "tone_and_emotion_arc": {{
    "primary_tone": "<descriptor>",
    "emotion_arc": "<emotion → emotion>",
    "rationale": "<grounded reasoning>"
  }},

  "kill_signals": {{
    "existence":  ["<behaviors proving this archetype exists in market>"],
    "engagement": ["<signals they're actively engaged with the category>"],
    "conversion": ["<signals they're ready to buy>"]
  }},

  "ad_creative_gap": "1-2 sentences: based on the ads currently targeting this archetype (if any), what creative direction is MISSING that this archetype actually needs.",

  "anti_patterns": [
    "<creative approaches that would actively repel this archetype, with snippet evidence>"
  ]
}}

RULES:
- pain_points: 3-6 items. Each must cite ≥1 snippet_index.
- desires: 3-5 items.
- barriers_objections: 4-6, mixing barriers and objections.
- vocabulary: distinctive, NOT generic English. Pull verbatim phrases.
- recommended_hooks: 3-5 items. Tag each "from_brand_library" if drawn from candidates above OR "new_for_this_ctp" if you wrote it.
- recommended_value_props: 3-5 items. Same source-tagging rule.
- frameworks_that_resonate: 2-4 items.
- ad_creative_gap: don't write "more authentic content" — be specific about WHAT.
- anti_patterns: 2-4. What would repel them.

Return ONLY the JSON object."""


# ============ Target Persona Discovery (NEW — for prospects, not customers) ============
# Customer CTPs are people who already know the brand. Target Personas are the
# segments the brand SHOULD be acquiring but isn't yet — people who have the
# problem the brand solves but sit at Unaware / Problem-Aware / Solution-Aware
# (Schwartz). The prompt explicitly asks the LLM to look BEYOND brand mentions
# and surface the underlying category-level psychology.

TARGET_PERSONA_DISCOVERY_PROMPT = """You are a senior demand-generation strategist for {brand_name}. You're not building customer personas (we already have those). You're building TARGET PERSONAS — the segments {brand_name} SHOULD be acquiring at the top of the funnel but doesn't yet have as customers.

The data corpus below is rich, but biased: most snippets came from sources that mention {brand_name}. To find prospects, you have to read against that grain. Apply Eugene Schwartz's awareness framework:

  - UNAWARE: doesn't yet know they have the problem. Most powerful but hardest to reach.
  - PROBLEM AWARE: feels the problem, doesn't know solutions exist.
  - SOLUTION AWARE: knows solutions exist (e.g., better scents, longer-lasting fragrances), but not {brand_name} specifically.
  - PRODUCT AWARE: knows {brand_name}, not yet convinced. Already a CTP, don't include here.
  - MOST AWARE: ready to buy, just needs the right offer. Already a CTP, don't include here.

You're hunting for segments at the FIRST THREE awareness levels. To find them in this data:
  1. Look for snippets discussing the CATEGORY problem without naming {brand_name} (e.g., "how do I find a perfume that lasts" — not "I love Phlur Missing Person").
  2. Look for snippets describing FAILED EXPERIENCES with COMPETITORS — those people are pre-{brand_name} prospects who haven't found the right solution yet.
  3. Look for behavioral patterns implied by the data that {brand_name} could acquire (e.g., people building decant collections, people asking for sample programs, people switching scents seasonally).
  4. Consider what types of people would NATURALLY be in the data sources but might not have shown up because the search was brand-focused — and name them as potential gaps.

# BRAND + COMPETITIVE CONTEXT
{brand_block}

# VOICE-OF-CUSTOMER SNIPPETS (numbered — reference by index)
{snippets_block}

# AD-LIBRARY OBSERVATIONS (what {brand_name} is currently saying)
{ads_block}

# CTPS WE ALREADY HAVE (don't duplicate these — Target Personas are DIFFERENT people)
{existing_ctps_summary}

---

# DELIVERABLE

Return a JSON object:

{{
  "rationale": "2-4 sentences explaining your selection logic. Specifically: what evidence in the data points to PROSPECTS (not customers), and which awareness level you found most signal for. If a level had insufficient evidence, say so honestly.",

  "target_personas": [
    {{
      "name": "Behavior- and category-specific name (3-7 words). NOT brand-specific (these aren't {brand_name} customers yet). FORBIDDEN: 'The Skeptic', 'The Optimizer', generic archetype labels. Good names anchor in CATEGORY behavior or PROSPECT psychology — e.g., 'Decant-Trying Frag Newcomer', 'Bath-and-Body-Works Graduate', 'Designer-Fragrance Loyalist Bored Out'.",

      "awareness_level": "Unaware|Problem Aware|Solution Aware",

      "the_problem_they_have": "1-2 sentences in their own vocabulary describing the problem this person actively experiences. Cite snippet indexes.",

      "why_not_yet_a_customer": "1-2 sentences. Concrete reason this person hasn't bought from {brand_name} yet — not generic 'haven't heard of it' but specific (e.g., 'They're loyal to designer brands and don't trust online-only fragrance houses', 'They buy at Sephora and {brand_name} isn't there', 'They follow specific influencer recommendations and {brand_name} isn't being recommended in their bubble').",

      "current_solution_or_workaround": "What this person is doing INSTEAD of buying from {brand_name} right now. Cite evidence.",

      "what_would_unlock_them": "Specific creative or proposition direction that would convert this segment. Be concrete — not 'better marketing' but 'A side-by-side longevity test ad on TikTok showing Phlur outlasting their current designer scent for half the price'.",

      "acquisition_hook": "ONE ready-to-test hook copy that would stop their scroll. Use category vocabulary, not brand vocabulary. The viewer doesn't know {brand_name} yet — the hook needs to land on the problem.",

      "evidence_indexes": [<int>],
      "evidence_quotes": [
        "<verbatim quotes that prove this segment exists in the data>"
      ],

      "estimated_acquisition_difficulty": "low|medium|high",
      "estimated_share_of_addressable_market": <number 0-100, rough estimate of % of total category audience>,

      "demographic_hypothesis": {{
        "age_range": "<your best inference from snippets>",
        "platform_affinity": ["<top 1-3 platforms where this segment lives>"],
        "lifestyle_markers": ["<2-4 concrete lifestyle indicators>"]
      }},

      "creative_format_recommendation": "<UGC | Founder | Comparison | Tutorial | Mythbusting | Testimonial — pick ONE most-fit format and explain in one sentence>",

      "anti_pattern": "<creative direction that would actively repel this segment>"
    }}
  ]
}}

# RULES

- 2-5 target personas. NOT 8 buckets. If only 2 are clearly supported by data, return 2.
- Each persona needs ≥6 evidence_indexes from snippets that genuinely demonstrate UNBRANDED or competitive-but-not-yet-{brand_name} behavior.
- DO NOT just rename CTPs we already have. The summary of existing CTPs is provided — your output must be different segments.
- DO NOT invent psychology that the snippets don't show. If the data is shallow on prospects, return fewer personas and explain in rationale.
- Each acquisition_hook MUST work for someone who has never heard of {brand_name}. If the hook only makes sense to existing customers, it's wrong.

Return ONLY the JSON object."""


# ============ Hypothesis Layer Generation ============

HYPOTHESIS_GENERATION_PROMPT = """You are a creative strategist generating hypothesis-layer suggestions for ad campaigns targeting a specific Creative Target Persona of {brand_name}.

Ground every suggestion in this brand's reality:

{brand_context_block}

---

# THIS CTP

CTP NAME: {ctp_name}
GENERAL STANCE INSIGHT: {core_insight}
WEIGHT: {weight}/10  ({snippet_count} snippets supporting this CTP)

PAIN POINTS:
{pain_points_text}

BARRIERS / OBJECTIONS:
{barriers_text}

KILL SIGNALS:
{kill_signals_text}

LANGUAGE CUES FROM THIS CLUSTER:
{language_cues_text}

---

Return JSON. Every "rationale" field must reference THIS CTP's actual data (snippets, language cues, pain points, ad-library observations) — never generic strategy advice.

{{
  "demographic_variables": {{
    "age_range": "Estimated age range with reasoning anchored in snippet vocabulary/topics",
    "gender_skew": "e.g. '60% female' — only commit when there's evidence; otherwise 'mixed'",
    "income_level": "e.g. 'middle to upper-middle' — only commit when there's evidence",
    "education": "e.g. 'college+' or 'mixed'",
    "platform_affinity": ["Top 2-3 platforms with most signal in the data"],
    "geo_notes": "Geographic skew if observed, else null",
    "aspirations": ["What this CTP WANTS, in their own language. 2-4 items."],
    "lifestyle_markers": ["Concrete lifestyle indicators visible in the snippets — habits, life stage, daily routine cues"]
  }},

  "angles": [
    {{
      "angle_name": "Short descriptive name",
      "angle_description": "1-2 sentences describing the angle approach",
      "awareness_level": "Unaware|Problem Aware|Solution Aware|Product Aware|Most Aware",
      "emotional_trigger": "Primary emotion activated — pull from this CTP's language cues",
      "validation_tag": "data_backed|objection_driven|proof_type_match|language_pattern|hypothesis",
      "validation_evidence": "What snippet/cue/pattern supports this angle"
    }}
  ],

  "funnel_stage": {{
    "stage": "awareness|consideration|decision|retention",
    "rationale": "Why this CTP sits here, citing the snippets"
  }},

  "framework_tactic": {{
    "primary": "Concrete framework name (e.g. 'Problem-Agitate-Solution', 'Mythbusting', 'Founder Story')",
    "secondary": "A second framework that could complement",
    "rationale": "Why this framework fits — reference snippets and ad-library observations"
  }},

  "visual_style": {{
    "style": "Concrete visual approach (e.g. 'UGC selfie diary', 'Clinical-clean lab', 'Documentary interview')",
    "rationale": "Why it resonates with this CTP's mindset"
  }},

  "narrative_driver": {{
    "driver": "VO+text | POV story | Expert interview | Montage | etc.",
    "rationale": "Why this driver fits"
  }},

  "tone": {{
    "primary": "Specific tone descriptor",
    "secondary": "Backup tone descriptor",
    "rationale": "Reference the brand voice + this CTP's emotional state"
  }},

  "emotion": {{
    "arc": "Emotion → emotion (e.g. 'Skepticism → Curiosity', 'Frustration → Relief')",
    "primary_emotion": "Dominant emotion to lead with",
    "rationale": "Why this arc resonates"
  }}
}}

RULES:
- angles: 3-5. Prefer 'data_backed' tags when there's snippet evidence; use 'hypothesis' when you're inferring.
- aspirations: pulled from snippet vocabulary, not boardroom aspirations.
- All rationales must reference SOMETHING from this CTP or brand context, not generic advertising lore.

Return ONLY the JSON object."""
