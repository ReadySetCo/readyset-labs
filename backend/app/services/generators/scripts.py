# -*- coding: utf-8 -*-
"""
Script Generator - Generates professional ad scripts with rich context.
Uses Gemini for long prompts, generates one at a time with timeouts.
Enhanced with creative frameworks from proven SLP concepts database.
"""

from typing import Dict, Any, List
import asyncio
from ..llm.client import get_llm_client
from ..adlibrary.taxonomies import (
    FRAMEWORK, HOOK_TYPE, EMOTION, CREATIVE_FORMAT, 
    VISUAL_TYPE, TALENT_TYPE, PACING, SETTING_TYPE
)
from ..creative_reference import get_creative_frameworks, get_hooks_for_industry


SCRIPT_SYSTEM_PROMPT = """INTERNAL PROCESS: Run all quality gates silently. Do not output reasoning. Do not output explanations. Only return the final JSON.
OUTPUT RULE: Return raw JSON only. Do not wrap in markdown fences. Do not add comments. Do not add prose before or after.

# Readyset AI Assist — Script Generation System Prompt
# OUTPUT: 1 Video Script per call (with creative brief metadata embedded)
# OUTPUT FORMAT: Raw JSON only — no markdown, no prose, no fences

## IDENTITY & ROLE

You are Readyset AI — the senior creative strategist and brand psychologist inside the Readyset platform.

You don't just write scripts. You architect narrative systems that exploit cognitive biases to stop the scroll, earn trust, and drive action — all within the cultural and linguistic norms of the target platform.

You function as a bridge between media buying data and human desire. You think in psychological triggers, narrative arcs, and production frames simultaneously. Your outputs are used directly by production teams. Every word, every visual direction, every timing note either gets shot or gets cut.

## CREATIVE PHILOSOPHY

### 1. Find the Brand Soul First

Before generating a single word of copy, identify three things from the brand data:

**The Core Belief:** The brand's unique worldview that drives everything.
> GOOD: "Credit should not be a privilege — it's a tool." / "Quality skincare was never meant to cost $300."

**The Brand Enemy:** What or who the brand is disrupting or fighting against. Specific, named, emotionally resonant.
> BAD: "The status quo."
> GOOD: "The predatory banking system that profit-maps first-time borrowers and calls it 'credit building.'"

**The Transformation:** The exact emotional shift the product enables — from the specific "Before" state (pain, frustration, embarrassment, stagnation) to the specific "After" state (relief, confidence, momentum, pride). This Before-After contrast must be physically visible in the script's camera work and editing energy.

### 2. Brand Data Assimilation Protocol

To ensure the brand feels the output is theirs — not just a vertical template — execute this silent internal cross-check:

**Rule A — The Verbatim Echo:**
Locate one (1) unique phrase from the brand's verbatim quotes or customer language. This exact phrase MUST appear in the hook or body copy.

**Rule B — The Friction Point:**
Identify the specific, granular micro-moment of frustration from customer pain points. The Problem Agitation shot must visually depict this exact micro-moment, not a generic category version of it.
> BAD: "Customer looks frustrated at their phone."
> GOOD: "ECU of the payment terminal screen: DECLINED. Held for 0.8s. Let the embarrassment land. [SFX: card machine beep — three times]. Smash cut to dark frame."

**Rule C — The Vertical Differentiation Anchor:**
In notes, explicitly name the #1 Creative Cliche this script is replacing and what it is being replaced with.

### 3. Behavioral Economics Layering

Every angle must be rooted in at least one cognitive trigger. Tag each scene with its trigger. The narrative arc must be psychologically coherent.

| Trigger | Definition | Best Used When |
|---|---|---|
| Loss Aversion | People fear loss 2x more than equivalent gain | ICP is bleeding money, time, or status without realizing it |
| Social Signaling | Product elevates user's identity/status in their tribe | Purchase is publicly visible or identity-adjacent |
| Zero-Risk Bias | Eliminating psychological friction of "making a mistake" | High-ticket, skepticism-heavy, or new-category products |
| The Pratfall Effect | Admitting a small flaw builds disproportionate trust | Challenger/underdog brand; category full of puffery |
| Scarcity / FOMO | Limited availability triggers urgency independent of value | Drops, seasonal offers, limited cohorts |
| Authority Bias | Credentialed sources or social proof reduce resistance | Regulated industries (finance, health, legal) |
| The Zeigarnik Effect | Unfinished loops create tension demanding resolution | Hook opens a question the viewer cannot ignore |
| Anchoring | First number shapes all subsequent value perception | Pricing comparisons, time savings, result claims |
| Reciprocity | Giving genuine value first creates obligation to engage | Educational/tutorial content before the offer |

### 4. Trigger Escalation Closed Loop (mandatory narrative arc)

| Script Phase | Function | Trigger Used |
|---|---|---|
| Scene 1 — Hook | Initiate the loop | Zeigarnik Effect (open the question) |
| Scene 2-3 — Agitation | Intensify the Primary Trigger | The trigger matching the ICP's awareness state (e.g., Loss Aversion) |
| Scene 4-5 — Resolution | Relieve the Primary Trigger via product | Zero-Risk Bias and/or Authority Bias |
| Final Scene — CTA | Close the loop with urgency | Scarcity/FOMO or Reciprocity |

### 5. Linguistic Authenticity — The Insider Test

Extract 2-3 industry-specific terms or ICP slang from the brand data or vertical knowledge. Embed these in dialogue and overlays — as proof of cultural proximity to the target audience.

| Vertical | Example Insider Language |
|---|---|
| SaaS / Tech | "Churn", "tech debt", "LTV", "CAC", "ship fast", "zero downtime" |
| Fitness | "Progressive overload", "macros", "DOMS", "PRs", "your third pull day" |
| Finance / DTC Credit | "APR", "utilization rate", "hard pull", "credit-building loop", "thin file" |
| Beauty / Skincare | "Skin barrier", "comedogenic", "actives", "slugging", "glass skin" |
| Food / Nutrition | "Macro-friendly", "whole food", "bioavailability", "clean label", "binders" |
| Fashion | "Colorway", "drop", "grail", "deadstock", "capsule" |
| Health / Wellness | "Cortisol spike", "nervous system reset", "circadian rhythm", "somatic" |
| Pets | "BARF diet", "prey model", "kibble-fed", "zoonotic", "enrichment" |
| Education / Coaching | "Cohort", "async", "mindset shift", "accountability partner", "framework" |

### 6. Data-Backed Hook Strategy (Motion Creative Benchmarks 2026)

Based on $1.3B+ in ad spend across 550,000+ creatives (BFCM 2025 - Jan 2026), these hook typologies carry the highest hit rates:

**Tier 1 — Highest hit rate & spend use ratio:**
- Newness — "Introducing the only [X] that does [Y]"
- Price anchor — "Stop paying $X for Y when you can get Z for $W"
- Sale / Urgency — "Last 48 hours / Limited drop / Selling out fast"
- Offer only — Lead with the deal before any product explanation
- Confession — "I was embarrassed to admit I..."
- Bold claim — Audacious, specific, provable: "We replaced [big thing] in 7 days"
- Shocking statement — "Most [category] advice is completely wrong"
- Curiosity / If-then — "If you're still doing X, watch this before you regret it"
- Direct address — "Attention [specific persona]..."
- Warning — "Do NOT buy [category] until you see this"
- Authority — "As seen in [publication] / [N]K customers later..."
- Giveaway / Exclusivity — "Only for the next 200 people..."

**Hook selection rule:** Match hook type to brand tone AND ICP awareness state:
- Pain-aware: Confession, Warning, Loss Aversion
- Solution-aware: Bold Claim, Demo, Zero-Risk Bias
- Product-aware: Offer, Urgency, Social Signaling

### 7. Visual Format Intelligence by Vertical

| Vertical | Top Formats by Hit Rate |
|---|---|
| Health & Wellness | Stitch, Reaction video, Unboxing, Founder, Transformation |
| Fashion & Apparel | Post-it, Quiz, Stylized product shot, Meme, Product showcase |
| Beauty & Personal Care | Unboxing, Testimonial, Tutorial, Before & After |
| Food & Nutrition | Demo, How-to, Lifestyle-product, Montage |
| Technology | Screen recording, Feature benefit, How-to, Expert explained |
| Finance | Authority, Case study, Statistic, Problem agitation |
| Fitness & Sports | Transformation, Before & After, POV, Founder |
| Home & Lifestyle | Montage, Demo, Product showcase, How-to |
| Education | How-to, Expert explained, Screen recording, Listicle |
| Pets | UGC, Testimonial, Founder, POV |

Universal high-performers: Offer-First Banner (1.3x spend use ratio), Demo (6.5% hit rate), Testimonial (6.5% hit rate), Unboxing (9.8% hit rate).

## THE HOOK LAB

For every script, generate 3 distinct hook options. All three must:
- Be 15 words or fewer (spoken) or a precise visual direction
- Map to a different psychological trigger
- Be genuinely different in structure — not the same idea reworded

Required hook types:
1. **Pattern Interrupt** — Breaks visual or auditory expectation in 1 second or less. Trigger: Zeigarnik Effect.
2. **Direct Call-out** — Targets the ICP's identity, pain, or behavior immediately. Trigger: Loss Aversion or Social Signaling.
3. **Curiosity Gap** — Opens an unresolved loop that can only be closed by watching. Trigger: Zeigarnik Effect.

## CREATIVE FRAMEWORKS

Use exactly ONE per script:

**F1: Problem-Solution** — Pain-aware ICPs.
Hook - Agitation (Friction Point visual) - Solution reveal - Proof - Transformation - CTA

**F2: Before-After-Bridge** — Transformation products.
Hook (Show Before) - Feel the before - Bridge (introduce product) - Show After clearly - CTA

**F3: Testimonial / Social Proof** — Trust-building, retargeting.
Hook (Disarming first-person) - Problem confession - Discovery - Specific result - CTA

**F4: Listicle / Reasons Why** — Feature-rich, Education, Tech.
Hook (N reasons why...) - Point 1 + visual proof - Point 2 - Point 3 - Offer anchor - CTA

**F5: How-To / Tutorial** — Products with learning curve or ritual.
Hook (The right way to [X]) - Step 1 - Step 2 - Step 3 - Result reveal - CTA

**F6: Pattern Interrupt / Contrarian** — Saturated categories.
Hook (breaks expectation) - Everyone does X, but... - Brand POV - Evidence - CTA

## PLATFORM-NATIVE PRODUCTION RULES

### TikTok
- Hook: 0-1.5 seconds — no grace period
- Tone: conversational, lo-fi, direct — native content, not advertising
- Cuts: 1.5-2.5s per shot average
- Text overlays: essential; assume muted viewing

### Instagram Reels
- Hook: 0-2 seconds; slightly more polished than TikTok

### Meta (Facebook/Instagram Feed)
- Hook: 0-3 seconds — more tolerance; slightly older demographic
- Offer-first banner: 1.3x spend-use ratio — use for conversion campaigns

### YouTube
- 16:9; first 5 seconds are the skip/watch decision
- More narrative depth and production value accepted

### All Platforms
- NEVER open with logo or brand name
- First frame = most compelling frame
- Text overlays: max 2-3 words/second
- CTAs: on-screen AND spoken

## SHOT COUNT BY DURATION

| Duration | Shots | Narrative Budget |
|---|---|---|
| 15s | 3 | Hook + Product reveal + CTA |
| 30s | 5 | Hook - Problem - Solution - Proof - CTA |
| 45s | 7 | Hook - Problem - Agitation - Solution - Demo - Social Proof - CTA |
| 60s+ | 8+ | Hook - Problem - Story - Solution - Features - Proof - Offer - CTA |

## PRODUCTION STANDARDS

### Shot-to-Shot Continuity
Each visual description must reference spatial continuity, camera movement, and lighting from the previous shot.

### Visual-VO Sync Principle
Never duplicate information between spoken words and visual text.
- Spoken words: emotion and narrative
- Visual text: proof and action

### Audio Design
Embed SFX and music cues explicitly:
- [SFX: sharp cash register ding at 0:03]
- [Music: lo-fi trap, 120bpm — beat drops as product rotates into frame]
- [Silence: 0.5s pause before hook lands — forces cognitive attention]

### VO Cadence
Speakable in one natural breath. Max 12-15 words for hooks. Contractions, active verbs. No corporate phrasing.

### Objection Preemption Shot
At least one scene addresses the #1 purchase barrier without sounding defensive.

## KPI MAPPING

| Campaign Goal | Primary KPI |
|---|---|
| Awareness | Thumb-stop rate >65% at 3s |
| Consideration | View-through rate >40% at 50% completion |
| Conversions | CTA click-through >1.8%, CPA below brand threshold |
| Retargeting | Completed views >55%, add-to-cart rate improvement |

### CTA Temperature
- High urgency / pain: "Claim your 30% off before midnight."
- Trust / retargeting: "See why 14,200 customers switched."
- Curiosity / discovery: "Tap to see how it works in 10 seconds."
- Soft awareness: "Follow for more." / "Save this for later."

## ANTI-HALLUCINATION GUARDS

- Never invent statistics, customer counts, certifications, or press mentions
- Missing proof: use qualitative language: "Trusted by [vertical] professionals"
- Every quantified claim must trace to brand data
- Feature only the most relevant product

## QUALITY GATES — INTERNAL SILENT SELF-REVIEW

Run silently before outputting. Rewrite any failing section:

1. Verbatim Echo: Does the hook or body contain at least one phrase from customer verbatims?
2. Friction Point: Does the Problem scene depict the specific micro-moment of pain, not a generic version?
3. Vertical Differentiation: Does notes state the #1 Creative Cliche being replaced?
4. Hook Gate: Does the hook stop a thumb-scroll in 1.5s (TikTok) / 2s (IG) / 3s (Meta)? No brand name opener?
5. Hook Lab: Are all three hooks meaningfully different in structure AND psychological mechanism?
6. Trigger Escalation: Does the psychologicalTrigger sequence form a coherent closed loop?
7. Voice Gate: Does the script pass the brand tone mirror test? No forbidden corporate phrases?
8. Insider Test: Does the dialogue sound written by a peer inside this industry?
9. Continuity: Do all scenes flow visually? Is visual-VO sync maintained?
10. Proof Gate: Every claim backed by visual, testimonial, demo, or verbatim quote?
11. CTA Gate: Final CTA matches emotional temperature, on-screen AND spoken?
12. Production Gate: Could a DP, editor, and talent execute every shot without clarification?

## ABSOLUTE PROHIBITIONS

- Never output prose, reasoning, or explanations outside the JSON object
- Never wrap output in markdown fences
- Never start a hook with the brand name
- Never write vague visual directions ("show the product", "happy scene", "customer smiling")
- Never use forbidden corporate language: "empower", "leverage", "innovative", "cutting-edge", "seamlessly", "game-changing", "holistic", "synergy", "next level", "unlock your potential", "experience the difference", "industry-leading"
- Never produce the same angle twice with different vocabulary
- Never fabricate statistics, customer counts, certifications, or press mentions
- Never describe what the ad IS — describe what it DOES to the viewer emotionally
- Never produce a CTA weaker than the emotional pitch that preceded it

ALWAYS return valid JSON only. No markdown, no explanation."""


class ScriptGenerator:
    """Generates professional ad scripts using Gemini with rich context."""
    
    def __init__(self):
        self.llm = get_llm_client(task_type="creative")
    
    async def generate_scripts(
        self,
        brand_info: Dict[str, Any],
        ad_patterns: Dict[str, Any],
        insights: Dict[str, Any],
        num_scripts: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Generate professional ad scripts ONE AT A TIME for reliability.
        Uses Gemini with rich context prompts.
        """
        scripts = []
        
        # Build rich context (but organized efficiently)
        context = self._build_context(brand_info, ad_patterns, insights)
        
        # Frameworks to generate (aligned with DRAFT F1-F6 creative frameworks)
        frameworks = [
            ("Problem-Solution", "Direct Call-out"),
            ("Before-After-Bridge", "Curiosity Gap"),
            ("Testimonial", "Pattern Interrupt"),
            ("Listicle", "Direct Call-out"),
            ("How-To", "Curiosity Gap"),
            ("Pattern Interrupt / Contrarian", "Pattern Interrupt"),
        ][:num_scripts]
        
        print(f"       -> Generating {num_scripts} PRO scripts with Gemini...")
        print(f"       -> Context: {len(context.get('pain_points', []))} pain points, {len(context.get('verbatim_quotes', []))} quotes, {len(context.get('icps', []))} ICPs")
        
        for i, (framework, hook_type) in enumerate(frameworks):
            try:
                print(f"          Script {i+1}/{num_scripts}: {framework} ({hook_type})...")
                script = await self._generate_single_script(
                    context=context,
                    framework=framework,
                    hook_type=hook_type,
                    script_num=i + 1
                )
                if script:
                    scripts.append(script)
                    print(f"          [OK] Script {i+1} generated: {script.get('script_name', 'Untitled')[:40]}")
                else:
                    print(f"          [!] Script {i+1} returned None, using fallback")
                    scripts.append(self._create_fallback_script(context['brand_name'], framework, i+1))
            except asyncio.TimeoutError:
                print(f"          [!] Script {i+1} timed out after 120s, using fallback")
                scripts.append(self._create_fallback_script(context['brand_name'], framework, i+1))
            except Exception as e:
                print(f"          [!] Script {i+1} error ({type(e).__name__}): {str(e)[:80]}")
                scripts.append(self._create_fallback_script(context['brand_name'], framework, i+1))
        
        if not scripts:
            scripts = [self._create_fallback_script(context['brand_name'], "Problem-Solution", 1)]
        
        print(f"       -> Generated {len(scripts)} scripts total")
        return scripts
    
    def _build_context(self, brand_info: Dict, ad_patterns: Dict, insights: Dict) -> Dict:
        """Build organized context from all data sources - FULLY ENRICHED with real VoC data."""
        
        # Brand info
        brand_name = brand_info.get('name', 'Brand')
        sector = brand_info.get('sector', '')
        products = str(brand_info.get('products', ''))[:500]
        value_props = str(brand_info.get('value_propositions', ''))[:500]
        target_audience = str(brand_info.get('target_audience', ''))[:300]
        
        # === PAIN POINTS (Enriched - top 15 with sources) ===
        pain_points = []
        raw_pains = insights.get('pain_points', [])[:15]
        for p in raw_pains:
            if isinstance(p, dict):
                pain = p.get('pain_point', p.get('name', str(p)))[:200]
                intensity = p.get('intensity', p.get('frequency', 0))
                sources = p.get('sources', p.get('evidence', []))
                pain_str = f"• {pain} (intensity: {intensity})"
                if sources and isinstance(sources, list):
                    pain_str += f" - mentioned in: {', '.join(str(s)[:30] for s in sources[:3])}"
                pain_points.append(pain_str)
            elif isinstance(p, str):
                pain_points.append(f"• {p[:200]}")
        
        # === VERBATIM QUOTES (Enriched - top 20 with context and use_case) ===
        verbatims = insights.get('verbatim_quotes', [])[:20]
        verbatim_list = []
        for q in verbatims:
            if isinstance(q, dict):
                quote = str(q.get('quote', q.get('text', '')))[:400]
                source = q.get('source', q.get('platform', 'customer'))
                sentiment = q.get('sentiment', '')
                topic = q.get('topic', q.get('category', ''))
                use_case = q.get('use_case', '')  # How to use this quote in ads
                
                quote_str = f'"{quote}"'
                details = []
                if source:
                    details.append(source)
                if sentiment:
                    details.append(sentiment)
                if topic:
                    details.append(topic)
                if details:
                    quote_str += f" [{', '.join(details)}]"
                if use_case:
                    quote_str += f" → Use as: {use_case[:80]}"
                verbatim_list.append(quote_str)
            elif isinstance(q, str):
                verbatim_list.append(f'"{q[:400]}"')
        
        # === CUSTOMER LANGUAGE (exact phrases customers use) ===
        customer_language = insights.get('customer_language', [])[:15]
        language_list = []
        for phrase in customer_language:
            if isinstance(phrase, str) and phrase.strip():
                language_list.append(f'• "{phrase[:150]}"')
            elif isinstance(phrase, dict):
                text = phrase.get('phrase', phrase.get('text', str(phrase)))[:150]
                language_list.append(f'• "{text}"')
        
        # === CUSTOMER DESIRES (what customers want) ===
        customer_desires = insights.get('customer_desires', [])[:10]
        desire_list = []
        for d in customer_desires:
            if isinstance(d, str) and d.strip():
                desire_list.append(f"• {d[:200]}")
            elif isinstance(d, dict):
                desire = d.get('desire', d.get('want', str(d)))[:200]
                desire_list.append(f"• {desire}")
        
        # === OBJECTIONS with COUNTER MESSAGES (top 8) ===
        objections = insights.get('objections', [])[:8]
        objection_list = []
        for o in objections:
            if isinstance(o, dict):
                obj = o.get('objection', o.get('concern', ''))[:200]
                counter = o.get('counter_message', o.get('counter_messaging', o.get('counter', o.get('response', ''))))[:250]
                freq = o.get('frequency', '')
                obj_str = f"OBJECTION: \"{obj}\""
                if counter:
                    obj_str += f"\nCOUNTER: {counter}"
                if freq:
                    obj_str += f" (freq: {freq})"
                objection_list.append(obj_str)
        
        # === AD PATTERNS (from brand's analyzed ads) ===
        top_frameworks = list(ad_patterns.get('frameworks', {}).keys())[:7]
        top_hooks = list(ad_patterns.get('hook_types', {}).keys())[:7]
        top_emotions = list(ad_patterns.get('emotions', {}).keys())[:7]
        avg_hook_strength = ad_patterns.get('avg_hook_strength', 3.5)
        
        # === TRANSCRIPTION EXAMPLES (Enriched - top 5 with full context) ===
        transcriptions = ad_patterns.get('top_transcriptions', [])[:5]
        trans_examples = []
        for t in transcriptions:
            if isinstance(t, dict):
                text = str(t.get('text', t.get('transcription', '')))[:1000]  # Much longer for better examples
                fw = t.get('framework', 'Unknown')
                hook = t.get('hook_strength', t.get('hook_strength_1to5', 3))
                hook_text = t.get('opening_copy', t.get('hook', ''))[:150]
                cta = t.get('cta_all', t.get('cta', ''))[:100]
                emotion = t.get('emotion', t.get('target_emotion', ''))
                
                if text:
                    example = f"=== SUCCESSFUL AD ({fw}, Hook Strength: {hook}/5, Emotion: {emotion}) ==="
                    if hook_text:
                        example += f"\nHOOK: \"{hook_text}\""
                    example += f"\nFULL SCRIPT:\n{text}"
                    if cta:
                        example += f"\nCTA: {cta}"
                    trans_examples.append(example)
        
        # === RECOMMENDED HOOKS (from insights analysis) ===
        recommended_hooks = insights.get('recommended_hooks', [])[:10]
        hook_suggestions = []
        for h in recommended_hooks:
            if isinstance(h, dict):
                hook_text = h.get('hook', h.get('text', ''))[:200]
                hook_type = h.get('type', '')
                target = h.get('target_persona', h.get('target', ''))
                reasoning = h.get('reasoning', h.get('why', ''))[:150]
                
                if hook_text:
                    suggestion = f'• "{hook_text}"'
                    if hook_type:
                        suggestion += f" [{hook_type}]"
                    if target:
                        suggestion += f" → targets: {target}"
                    if reasoning:
                        suggestion += f"\n  Why: {reasoning}"
                    hook_suggestions.append(suggestion)
            elif isinstance(h, str):
                hook_suggestions.append(f'• "{h[:200]}"')
        
        # === COMPETITOR HOOKS (what competitors are doing) ===
        competitor_hooks = ad_patterns.get('competitor_hooks', [])[:5]
        comp_hook_list = []
        for ch in competitor_hooks:
            if isinstance(ch, dict):
                comp = ch.get('competitor', 'Competitor')
                hook = ch.get('hook', ch.get('opening_copy', ''))[:150]
                hook_type = ch.get('hook_type', '')
                if hook:
                    comp_hook_list.append(f"• {comp}: \"{hook}\" [{hook_type}]")
            elif isinstance(ch, str):
                comp_hook_list.append(f"• {ch[:150]}")
        
        # === AD EXAMPLES (real analyzed ads with summaries) ===
        ad_examples = ad_patterns.get('ad_examples', {})
        
        # Brand ad examples (real ads that worked)
        brand_ad_examples = []
        for ad in ad_examples.get('brand_ads', [])[:5]:
            summary = ad.get('ad_summary', '')[:600]
            if summary:
                example = f"=== BRAND AD ({ad.get('framework', 'Unknown')}, {ad.get('media_type', 'video')}) ==="
                example += f"\n{summary}"
                if ad.get('hook'):
                    example += f"\nHOOK: \"{ad['hook'][:150]}\""
                if ad.get('transcription'):
                    example += f"\nFULL SCRIPT: {ad['transcription'][:500]}"
                brand_ad_examples.append(example)
        
        # Competitor ad examples
        competitor_ad_examples = []
        for ad in ad_examples.get('competitor_ads', [])[:5]:
            summary = ad.get('ad_summary', '')[:500]
            if summary:
                comp_name = ad.get('competitor', 'Competitor')
                example = f"=== {comp_name.upper()} AD ({ad.get('framework', 'Unknown')}) ==="
                example += f"\n{summary}"
                if ad.get('hook'):
                    example += f"\nHOOK: \"{ad['hook'][:150]}\""
                competitor_ad_examples.append(example)
        
        # Best hooks from all ads
        best_hooks = []
        for h in ad_examples.get('best_hooks', [])[:10]:
            hook_text = h.get('hook', '')[:150]
            if hook_text:
                source = h.get('source', 'brand')
                strength = h.get('strength', 0)
                framework = h.get('framework', '')
                best_hooks.append(f"• \"{hook_text}\" [Strength: {strength}/5, {framework}, from: {source}]")
        
        # === ICPs (Enriched - top 5 with full profile) ===
        icps = insights.get('ideal_customer_profiles', insights.get('icps', []))[:5]
        icp_list = []
        for icp in icps:
            if isinstance(icp, dict):
                name = icp.get('name', icp.get('persona', 'Customer'))
                pain = icp.get('primary_pain', icp.get('pain_point', icp.get('pain_points', '')))
                if isinstance(pain, list):
                    pain = ', '.join(str(p)[:50] for p in pain[:3])
                else:
                    pain = str(pain)[:150]
                desire = icp.get('primary_desire', icp.get('goal', icp.get('desire', icp.get('motivations', ''))))
                if isinstance(desire, list):
                    desire = ', '.join(str(d)[:50] for d in desire[:3])
                else:
                    desire = str(desire)[:150]
                demo = icp.get('demographics', icp.get('description', icp.get('age_range', '')))[:150]
                characteristics = icp.get('characteristics', [])
                
                icp_str = f"**{name}**"
                if demo:
                    icp_str += f"\n  Demographics: {demo}"
                if characteristics and isinstance(characteristics, list):
                    icp_str += f"\n  Characteristics: {', '.join(str(c)[:40] for c in characteristics[:4])}"
                if pain:
                    icp_str += f"\n  Pain Points: {pain}"
                if desire:
                    icp_str += f"\n  Desires/Goals: {desire}"
                icp_list.append(icp_str)
        
        # === PURCHASE TRIGGERS (what makes people buy) ===
        triggers = insights.get('purchase_triggers', [])[:8]
        trigger_list = []
        for t in triggers:
            if isinstance(t, dict):
                trigger = t.get('trigger', t.get('name', str(t)))[:120]
                impact = t.get('impact', t.get('strength', ''))
                quote = t.get('quote', t.get('example', ''))[:100]
                trigger_str = f"• {trigger}"
                if impact:
                    trigger_str += f" (impact: {impact})"
                if quote:
                    trigger_str += f' - e.g., "{quote}"'
                trigger_list.append(trigger_str)
            elif isinstance(t, str):
                trigger_list.append(f"• {t[:120]}")
        
        # === MESSAGING ANGLES (from insights - with evidence) ===
        messaging_angles = insights.get('messaging_angles', [])[:5]
        angle_list = []
        for a in messaging_angles:
            if isinstance(a, dict):
                angle = a.get('angle', a.get('name', a.get('hook', '')))[:150]
                rationale = a.get('rationale', a.get('description', a.get('why', '')))[:150]
                evidence = a.get('supporting_evidence', a.get('evidence', ''))[:100]
                if angle:
                    angle_str = f"• {angle}"
                    if rationale:
                        angle_str += f"\n  Why: {rationale}"
                    if evidence:
                        angle_str += f"\n  Evidence: \"{evidence}\""
                    angle_list.append(angle_str)
            elif isinstance(a, str):
                angle_list.append(f"• {a[:150]}")
        
        # === INDUSTRY-SPECIFIC HOOK TEMPLATES (from proven creative frameworks) ===
        industry_hooks = get_hooks_for_industry(sector)
        
        # === TIKTOK SEGMENT ANALYSIS (trending patterns + segment insights) ===
        tiktok_trends = insights.get('tiktok_trends', {})
        tiktok_segment = tiktok_trends.get('segment_analysis', {}) if tiktok_trends else {}
        tiktok_insights_list = []
        if tiktok_segment:
            aggregated = tiktok_segment.get('aggregated', {})
            if aggregated:
                # Customer language from TikTok
                if aggregated.get('customer_language_patterns'):
                    lang_patterns = aggregated['customer_language_patterns']
                    if isinstance(lang_patterns, dict):
                        phrases = lang_patterns.get('common_phrases', [])[:5]
                        slang = lang_patterns.get('slang', [])[:3]
                        if phrases:
                            tiktok_insights_list.append(f"Common TikTok phrases: {', '.join(str(p)[:50] for p in phrases)}")
                        if slang:
                            tiktok_insights_list.append(f"TikTok slang: {', '.join(str(s)[:30] for s in slang)}")
                # Trending formats
                if aggregated.get('trending_formats'):
                    formats = aggregated['trending_formats'][:3]
                    tiktok_insights_list.append(f"Trending formats: {', '.join(str(f)[:40] for f in formats)}")
                # Top hooks
                if aggregated.get('recommended_hook_types'):
                    hooks = aggregated['recommended_hook_types'][:4]
                    tiktok_insights_list.append(f"Best TikTok hooks: {', '.join(str(h)[:40] for h in hooks)}")
        
        # === INSTAGRAM BRAND PRESENCE (brand voice, aesthetic, content pillars) ===
        ig_brand = insights.get('instagram_brand_presence', {})
        ig_brand_context = []
        if ig_brand:
            if ig_brand.get('brand_voice'):
                voice = ig_brand['brand_voice']
                if isinstance(voice, dict):
                    tone = voice.get('tone', voice.get('primary_tone', ''))
                    if tone:
                        ig_brand_context.append(f"Brand tone: {str(tone)[:80]}")
                else:
                    ig_brand_context.append(f"Brand voice: {str(voice)[:100]}")
            if ig_brand.get('content_pillars'):
                pillars = ig_brand['content_pillars'][:4]
                ig_brand_context.append(f"Content pillars: {', '.join(str(p)[:50] for p in pillars)}")
            if ig_brand.get('messaging_themes'):
                themes = ig_brand['messaging_themes'][:3]
                ig_brand_context.append(f"Key themes: {', '.join(str(t)[:50] for t in themes)}")
            if ig_brand.get('brand_archetype'):
                ig_brand_context.append(f"Brand archetype: {str(ig_brand['brand_archetype'])[:50]}")
        
        # === HOOKS LIBRARY (structured hooks from creative briefs) ===
        hooks_library = insights.get('hooks_library', {})
        library_hooks = []
        if isinstance(hooks_library, dict) and not hooks_library.get("status"):
            raw_hooks = []
            if isinstance(hooks_library.get("all_hooks"), list):
                raw_hooks.extend(hooks_library.get("all_hooks", []))

            for bucket_key in ("by_type", "by_emotion"):
                bucket = hooks_library.get(bucket_key, {})
                if isinstance(bucket, dict):
                    for bucket_hooks in bucket.values():
                        if isinstance(bucket_hooks, list):
                            raw_hooks.extend(bucket_hooks[:3])

            seen_hooks = set()
            normalized_hooks = []
            for h in raw_hooks:
                if isinstance(h, dict):
                    hook_text = str(h.get("hook_text") or h.get("hook") or h.get("text") or "")[:160]
                    if not hook_text or hook_text in seen_hooks:
                        continue
                    seen_hooks.add(hook_text)
                    normalized_hooks.append({
                        "text": hook_text,
                        "type": h.get("hook_type") or h.get("type") or "",
                        "emotion": h.get("target_emotion") or h.get("emotion") or "",
                        "awareness": h.get("awareness_level") or "",
                        "format": h.get("recommended_format") or "",
                        "source": h.get("verbatim_source") or "",
                        "strength": h.get("strength_score") or 3,
                    })
                elif isinstance(h, str) and h not in seen_hooks:
                    seen_hooks.add(h)
                    normalized_hooks.append({"text": h[:160], "type": "", "emotion": "", "awareness": "", "format": "", "source": "", "strength": 3})

            normalized_hooks.sort(key=lambda item: item.get("strength") or 0, reverse=True)
            for h in normalized_hooks[:10]:
                hook_str = f"- \"{h['text']}\""
                tags = [str(value) for value in [h.get("type"), h.get("emotion"), h.get("awareness"), h.get("format")] if value]
                if tags:
                    hook_str += f" [{', '.join(tags)}]"
                if h.get("source"):
                    hook_str += f"\n  Source quote: \"{str(h['source'])[:120]}\""
                library_hooks.append(hook_str)

            if library_hooks:
                hooks_library = {}
        if False and hooks_library:
            # Retired legacy hook categories kept unreachable for backwards diff context.
            for category_key in []:
                category_hooks = hooks_library.get(category_key, [])[:2]
                for h in category_hooks:
                    if isinstance(h, dict):
                        hook_text = h.get('hook', h.get('text', ''))[:120]
                        if hook_text:
                            library_hooks.append(f"• {hook_text}")
                    elif isinstance(h, str):
                        library_hooks.append(f"• {h[:120]}")
        
        if not library_hooks:
            library_hooks = hook_suggestions[:6] or angle_list[:6]

        return {
            'brand_name': brand_name,
            'sector': sector,
            'products': products,
            'value_props': value_props,
            'target_audience': target_audience,
            'pain_points': pain_points,
            'verbatim_quotes': verbatim_list,
            'customer_language': language_list,
            'customer_desires': desire_list,
            'objections': objection_list,
            'top_frameworks': top_frameworks,
            'top_hooks': top_hooks,
            'top_emotions': top_emotions,
            'avg_hook_strength': avg_hook_strength,
            'transcription_examples': trans_examples,
            'recommended_hooks': hook_suggestions,
            'competitor_hooks': comp_hook_list,
            'icps': icp_list,
            'purchase_triggers': trigger_list,
            'messaging_angles': angle_list,
            # Real ad examples from Ad Library
            'brand_ad_examples': brand_ad_examples,
            'competitor_ad_examples': competitor_ad_examples,
            'best_hooks_from_ads': best_hooks,
            # Industry-specific hook templates
            'industry_hook_templates': industry_hooks,
            # NEW: TikTok segment insights
            'tiktok_insights': tiktok_insights_list,
            # NEW: Instagram brand presence
            'instagram_brand': ig_brand_context,
            # NEW: Hooks library
            'hooks_from_library': library_hooks,
        }
    
    async def _generate_single_script(
        self,
        context: Dict,
        framework: str,
        hook_type: str,
        script_num: int
    ) -> Dict[str, Any]:
        """Generate one script with rich context and 90s timeout."""
        
        # Build focused but rich prompt with ALL enriched data
        # Organized to match DRAFT system prompt's expected data fields
        prompt = f"""Generate ONE professional video ad script using the Readyset AI system. Use the REAL customer data below.

=== BRAND DATA ===
Brand Name: {context['brand_name']}
Sector / Vertical: {context['sector']}
Products: {context['products']}
Value Propositions: {context['value_props']}
Target Audience: {context['target_audience']}

=== CUSTOMER PAIN POINTS ({len(context['pain_points'])} from scraped data) ===
{chr(10).join(context['pain_points']) if context['pain_points'] else '- Common frustrations in this category'}

=== VERBATIM QUOTES — GOLD (The Verbatim Echo rule requires at least one) ===
{chr(10).join(context['verbatim_quotes']) if context['verbatim_quotes'] else '- "I wish there was a better solution"'}

=== CUSTOMER LANGUAGE — USE THESE EXACT PHRASES ===
{chr(10).join(context.get('customer_language', [])) if context.get('customer_language') else '- Natural conversational language'}

=== CUSTOMER DESIRES ===
{chr(10).join(context.get('customer_desires', [])) if context.get('customer_desires') else '- Better solutions, convenience, results'}

=== ICPs ({len(context['icps'])} identified) — Pick ONE primary ICP for this script ===
{chr(10).join(context['icps']) if context['icps'] else 'General audience in the ' + context['sector'] + ' space'}

=== OBJECTIONS ({len(context['objections'])} identified) — Address #1 barrier naturally ===
{chr(10).join(context['objections']) if context['objections'] else 'OBJECTION: "Is it worth the price?"\nCOUNTER: Focus on value and results'}

=== MESSAGING ANGLES (with evidence) ===
{chr(10).join(context.get('messaging_angles', [])) if context.get('messaging_angles') else '- Value-focused messaging'}

=== PURCHASE TRIGGERS ===
{chr(10).join(context.get('purchase_triggers', [])) if context.get('purchase_triggers') else '- Urgency and social proof'}

=== TOP HOOKS FROM RESEARCH ===
{chr(10).join(context.get('recommended_hooks', [])) if context.get('recommended_hooks') else '- Use pain point questions'}

=== AD LIBRARY PATTERNS (from {len(context.get('transcription_examples', []))} analyzed ads) ===
Winning Frameworks: {', '.join(context['top_frameworks']) if context['top_frameworks'] else 'Problem-Solution, Testimonial'}
Winning Hook Types: {', '.join(context['top_hooks']) if context['top_hooks'] else 'Question, Statement'}
Emotions that Convert: {', '.join(context['top_emotions']) if context['top_emotions'] else 'Relief, Curiosity'}
Avg Hook Strength: {context['avg_hook_strength']}/5

=== SUCCESSFUL AD TRANSCRIPTIONS (study their structure) ===
{chr(10).join(context['transcription_examples'][:5]) if context['transcription_examples'] else 'No examples available'}

=== BRAND AD EXAMPLES (from Ad Library) ===
{chr(10).join(context.get('brand_ad_examples', [])[:3]) if context.get('brand_ad_examples') else 'No brand ad examples available'}

=== COMPETITOR AD EXAMPLES ===
{chr(10).join(context.get('competitor_ad_examples', [])[:3]) if context.get('competitor_ad_examples') else 'No competitor ad examples available'}

=== TOP PERFORMING HOOKS FROM ADS ===
{chr(10).join(context.get('best_hooks_from_ads', [])[:8]) if context.get('best_hooks_from_ads') else 'No hook data available'}

=== COMPETITOR HOOKS ===
{chr(10).join(context.get('competitor_hooks', [])) if context.get('competitor_hooks') else 'No competitor data'}

=== INDUSTRY HOOK TEMPLATES (proven for {context['sector']}) ===
{chr(10).join('- ' + h for h in context.get('industry_hook_templates', [])) if context.get('industry_hook_templates') else '- Standard hook patterns'}

=== TIKTOK TRENDS ===
{chr(10).join(context.get('tiktok_insights', [])) if context.get('tiktok_insights') else 'No TikTok-specific data'}

=== INSTAGRAM BRAND VOICE ===
{chr(10).join(context.get('instagram_brand', [])) if context.get('instagram_brand') else 'No Instagram brand data'}

=== HOOKS LIBRARY ===
{chr(10).join(context.get('hooks_from_library', [])) if context.get('hooks_from_library') else 'No hooks library available'}

=== CREATIVE DIRECTION ===
Framework: {framework}
Hook Type: {hook_type}
Platform: TikTok / Instagram Reels / Meta Feed
Duration: 60-90 seconds
Campaign Goal: Conversions

EXECUTE the full Readyset AI system:
1. Find the Brand Soul (Core Belief, Brand Enemy, Transformation)
2. Run Brand Data Assimilation Protocol (Verbatim Echo, Friction Point, Vertical Differentiation Anchor)
3. Select primary psychological trigger matched to ICP awareness state
4. Build the Trigger Escalation Closed Loop across all scenes
5. Generate the Hook Lab (3 distinct hooks: Pattern Interrupt, Direct Call-out, Curiosity Gap)
6. Write production-ready scenes with full visual/audio/SFX direction
7. Run all Quality Gates silently before output

Return this exact JSON structure:
{{
    "script_name": "Catchy descriptive name that hints at the angle",
    "framework": "{framework}",
    "hook_type": "{hook_type}",
    "hook": "The CHOSEN hook from hook_lab — the strongest for this framework and brand tone",
    "hook_strength_estimate": 4,
    "target_emotion": "Primary emotion this script evokes",
    "target_persona": "Which ICP this script speaks to",
    "estimated_length_seconds": 75,
    "brand_psychology": {{
        "core_belief": "The brand's worldview in 1 charged sentence",
        "brand_enemy": "What/who the brand is disrupting — specific, named",
        "transformation": "Before state -> After state emotional shift"
    }},
    "strategic_rationale": "2 sentences: name the Primary Trigger, explain WHY it matches this ICP's awareness state. Connect to the Trigger Escalation sequence.",
    "hook_lab": [
        {{"type": "Pattern Interrupt", "psychological_trigger": "Zeigarnik Effect", "hook": "Exact hook text, 15 words max", "notes": "Why this stops scroll for this ICP"}},
        {{"type": "Direct Call-out", "psychological_trigger": "Loss Aversion", "hook": "Exact hook text, 15 words max", "notes": "The specific pain being targeted"}},
        {{"type": "Curiosity Gap", "psychological_trigger": "Zeigarnik Effect", "hook": "Exact hook text, 15 words max", "notes": "The open loop and why ICP cannot scroll past"}}
    ],
    "general_treatment": {{
        "style": "2-3 sentences: visual and audio treatment, production style (UGC vs high-production), casting energy",
        "editing_energy": 8,
        "sound_landscape": "Audio DNA: music genre/energy, SFX density, use of silence, VO delivery style",
        "pre_visualization": "Emotional texture direction contrasting Before and After states. Written for DP, gaffer, and talent."
    }},
    "insider_terminology": ["Term 1 — how it appears in script", "Term 2 — how it appears", "Term 3 — how it appears"],
    "full_script": "COMPLETE script with [VISUAL: description], [AUDIO: spoken words], [TEXT OVERLAY: caption], [SFX: sound effect] for each scene. 200-400 words, ready to shoot.",
    "scene_breakdown": [
        {{"scene": 1, "duration": "0-3s", "visual": "Full DP-level direction: shot type, subject action, environment, lighting, camera movement, safe-zone compliance", "audio": "Exact spoken words", "text_overlay": "Exact text + placement", "psychological_trigger": "Zeigarnik Effect"}},
        {{"scene": 2, "duration": "3-10s", "visual": "The Friction Point shot — specific micro-moment of pain, NOT generic", "audio": "Spoken words", "text_overlay": "", "psychological_trigger": "Loss Aversion"}},
        {{"scene": 3, "duration": "...", "visual": "...", "audio": "...", "text_overlay": "...", "psychological_trigger": "..."}}
    ],
    "cta": "Specific call to action — on-screen AND spoken, matched to CTA temperature",
    "why_it_works": "Data-backed explanation referencing: the psychological trigger used, specific pain points, customer language incorporated, and how the Trigger Escalation resolves",
    "based_on_verbatims": ["Exact quote 1 you incorporated", "Exact quote 2", "Exact quote 3"],
    "customer_language_used": ["Exact phrase 1 from customer language", "Phrase 2"],
    "desire_addressed": "Which customer desire this script fulfills",
    "objection_addressed": "The specific objection and how the script handles it",
    "pain_points_addressed": ["Pain point 1", "Pain point 2", "Pain point 3"],
    "notes": "#1 Creative Cliche Replaced: [old format] -> [new format we are using and why]. Any [INFERENCE REQUIRED] flags."
}}"""

        # Call Gemini with 120 second timeout per script (increased for long prompts)
        try:
            print(f"          Calling Gemini for {framework} script...")
            result = await asyncio.wait_for(
                self.llm.complete_json(prompt=prompt, system_prompt=SCRIPT_SYSTEM_PROMPT, temperature=0.75),
                timeout=120.0
            )
            
            if result and isinstance(result, dict):
                result['script_num'] = script_num
                if not result.get('based_on_verbatims') and result.get('verbatims_used'):
                    result['based_on_verbatims'] = result.get('verbatims_used')
                
                # Ensure full_script exists
                if not result.get('full_script') or len(result.get('full_script', '')) < 100:
                    result['full_script'] = self._build_full_script_from_scenes(result)
                
                print(f"          [+] Script generated: {result.get('script_name', 'Untitled')[:50]}")
                return result
            else:
                print(f"          [!] Gemini returned invalid response type: {type(result)}")
                return None
            
        except asyncio.TimeoutError:
            print(f"          [!] Gemini timeout after 120s for {framework}")
            raise
        except Exception as e:
            print(f"          [!] LLM error ({type(e).__name__}): {str(e)[:100]}")
            raise
    
    def _build_full_script_from_scenes(self, script: Dict) -> str:
        """Build full script from scene breakdown if LLM didn't provide it."""
        scenes = script.get('scene_breakdown', [])
        if not scenes:
            return f"""[SCENE 1 - HOOK]
{script.get('hook', 'Opening hook')}

[SCENE 2-6 - BODY]
{script.get('body', 'Main content developing the message...')}

[FINAL SCENE - CTA]
{script.get('cta', 'Call to action')}
"""

        parts = []
        for scene in scenes:
            s_num = scene.get('scene', '?')
            dur = scene.get('duration', '')
            visual = scene.get('visual', '')
            audio = scene.get('audio', '')
            text = scene.get('text_overlay', '')
            trigger = scene.get('psychological_trigger', '')

            header = f"[SCENE {s_num} - {dur}]"
            if trigger:
                header += f" ({trigger})"
            part = header
            if visual:
                part += f"\n[VISUAL: {visual}]"
            if audio:
                part += f"\n\"{audio}\""
            if text:
                part += f"\n[TEXT: {text}]"
            parts.append(part)

        return "\n\n".join(parts)
    
    def _create_fallback_script(self, brand_name: str, framework: str, num: int) -> Dict[str, Any]:
        """Create professional fallback script with full schema compatibility."""
        return {
            "script_name": f"{framework} Script #{num}",
            "framework": framework,
            "hook_type": "Direct Call-out",
            "hook": "Still struggling with [problem]? Here's what finally worked for me...",
            "hook_strength_estimate": 4,
            "target_emotion": "Relief",
            "target_persona": "General audience",
            "estimated_length_seconds": 60,
            "brand_psychology": {
                "core_belief": f"{brand_name} believes there's a better way.",
                "brand_enemy": "The outdated solutions that waste people's time and money.",
                "transformation": "Frustration and wasted effort -> Relief and confidence"
            },
            "strategic_rationale": "Uses Loss Aversion to surface the cost of inaction, then resolves with Zero-Risk Bias via the product's value proposition.",
            "hook_lab": [
                {"type": "Pattern Interrupt", "psychological_trigger": "Zeigarnik Effect", "hook": "Stop. You're wasting money on this every single month.", "notes": "Jarring command opens curiosity loop"},
                {"type": "Direct Call-out", "psychological_trigger": "Loss Aversion", "hook": "Still struggling with [problem]? Here's what finally worked for me...", "notes": "Targets the ICP's core frustration directly"},
                {"type": "Curiosity Gap", "psychological_trigger": "Zeigarnik Effect", "hook": "I almost didn't try this — but the results were too good to ignore.", "notes": "Opens unresolved loop demanding resolution"}
            ],
            "general_treatment": {
                "style": "UGC-native, handheld, direct-to-camera energy. Talent speaks like a friend sharing a discovery.",
                "editing_energy": 7,
                "sound_landscape": "No music during hook (silence forces attention). Lo-fi beat enters at solution reveal. On-camera VO throughout.",
                "pre_visualization": "Tight, slightly claustrophobic framing during the problem phase. Opens up to wider, warmer shots as the solution lands."
            },
            "insider_terminology": [],
            "full_script": f"""[SCENE 1 - 0-3s] (Zeigarnik Effect)
[VISUAL: MCU — talent looks directly at camera, slight frustration visible]
"I was SO tired of dealing with [problem]..."

[SCENE 2 - 3-12s] (Loss Aversion)
[VISUAL: B-roll showing the specific micro-moment of frustration]
"I tried everything. Nothing worked."

[SCENE 3 - 12-25s] (Reciprocity)
[VISUAL: Discovery moment — talent's expression shifts to curiosity]
"Then someone told me about {brand_name}..."

[SCENE 4 - 25-40s] (Zero-Risk Bias)
[VISUAL: Using product, genuine reaction, warm lighting shift]
"And honestly? It changed everything."

[SCENE 5 - 40-52s] (Authority Bias)
[VISUAL: Results/transformation — concrete proof visible]
"Now I [benefit]. Every single day."

[SCENE 6 - 52-60s] (Scarcity / FOMO)
[VISUAL: Direct to camera with product visible]
"Click the link and try {brand_name}. You'll thank me later."
[TEXT: Link in bio / Shop now]
""",
            "scene_breakdown": [
                {"scene": 1, "duration": "0-3s", "visual": "MCU — talent looks at camera, frustration visible", "audio": "I was SO tired of dealing with [problem]...", "text_overlay": "", "psychological_trigger": "Zeigarnik Effect"},
                {"scene": 2, "duration": "3-12s", "visual": "B-roll showing the specific micro-moment of frustration", "audio": "I tried everything. Nothing worked.", "text_overlay": "", "psychological_trigger": "Loss Aversion"},
                {"scene": 3, "duration": "12-25s", "visual": "Discovery moment — expression shifts", "audio": f"Then someone told me about {brand_name}...", "text_overlay": "", "psychological_trigger": "Reciprocity"},
                {"scene": 4, "duration": "25-40s", "visual": "Using product, warm lighting shift", "audio": "And honestly? It changed everything.", "text_overlay": "", "psychological_trigger": "Zero-Risk Bias"},
                {"scene": 5, "duration": "40-52s", "visual": "Results — concrete proof visible", "audio": "Now I [benefit]. Every single day.", "text_overlay": "", "psychological_trigger": "Authority Bias"},
                {"scene": 6, "duration": "52-60s", "visual": "Direct to camera with product", "audio": f"Click the link and try {brand_name}.", "text_overlay": "Shop now", "psychological_trigger": "Scarcity / FOMO"},
            ],
            "cta": f"Click the link and try {brand_name}. You'll thank me later.",
            "why_it_works": "Problem-solution framework using Trigger Escalation: Zeigarnik opens the loop, Loss Aversion surfaces the cost of inaction, Zero-Risk Bias resolves via product, Scarcity closes with urgency.",
            "based_on_verbatims": [],
            "customer_language_used": [],
            "desire_addressed": "",
            "objection_addressed": "",
            "pain_points_addressed": [],
            "notes": "#1 Creative Cliche Replaced: [generic talking head] -> [specific micro-moment of pain in Scene 2]. [INFERENCE REQUIRED: Verify brand data before shoot]",
            "script_num": num,
            "_fallback": True
        }
    
    async def generate_variations(self, original_script: Dict, variation_type: str = "hook") -> List[Dict]:
        """Generate variations of a script."""
        return [original_script]  # Simplified for reliability
    
    async def adapt_script_for_platform(self, script: Dict, platform: str) -> Dict:
        """Adapt script for platform."""
        adapted = script.copy()
        adapted['platform'] = platform
        return adapted
