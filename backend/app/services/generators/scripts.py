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


SCRIPT_SYSTEM_PROMPT = """You are an elite DTC creative strategist who has generated $100M+ in revenue.

## PROVEN HOOK PATTERNS (use these exact structures):

### Problem/Solution Hooks
- "That feeling when you realize your [problem]... But then you find [solution]"
- "I've tried everything for [problem] and nothing worked until..."
- "If you're googling [symptom/problem]... you need this"

### PSA / Call-Out Hooks  
- "PSA to all [target audience]"
- "[Target audience], watch this if you're dealing with [problem]"

### Testimonial Hooks
- "I actually thought I was just [symptom]. Turns out it was [real cause]..."
- "[Number] reasons why I love [product]"
- "Why I'll never go back to [old way]"

### Pattern Interrupt / Controversial
- "Don't [do thing] like it's the 1950s!"
- "Unpopular opinion: You don't need to [common belief]"

### Text Message / Friend Format
- "Hey, can you tell me more about that [product] you've been using?"
- "Just me texting my friend about how [product] changed my life"

## AD BODY STRUCTURES:
1. Problem → Agitate → Solution → Results → CTA
2. Testimonial Journey: Struggle → Discovery → Product → Results → CTA
3. Quick Listicle: Hook → Reason 1 → Reason 2 → Reason 3 → CTA

## RULES:
- Hook MUST be in first 1-3 seconds (before thumb scrolls)
- Feel native to platform (TikTok = casual, fast; Meta = can be longer)
- Use customer's EXACT words from verbatims
- Address objections naturally in narrative
- Clear, compelling CTA

ALWAYS return valid JSON only. No markdown, no explanation."""


class ScriptGenerator:
    """Generates professional ad scripts using Gemini with rich context."""
    
    def __init__(self):
        # Use Gemini specifically for scripts (handles long prompts better)
        self.llm = get_llm_client(provider="gemini")
    
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
        
        # Frameworks to generate (different for each script)
        frameworks = [
            ("Problem-Solution", "Question"),
            ("Testimonial", "Testimonial Quote"),
            ("How-To", "How-To"),
            ("Listicle", "Listicle Number"),
            ("Before-After", "Statement"),
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
        if hooks_library:
            # Get hooks by category
            for category_key in ['attention_grabbers', 'pain_point_hooks', 'curiosity_hooks', 'social_proof_hooks']:
                category_hooks = hooks_library.get(category_key, [])[:2]
                for h in category_hooks:
                    if isinstance(h, dict):
                        hook_text = h.get('hook', h.get('text', ''))[:120]
                        if hook_text:
                            library_hooks.append(f"• {hook_text}")
                    elif isinstance(h, str):
                        library_hooks.append(f"• {h[:120]}")
        
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
        prompt = f"""Generate ONE professional 60-90 second video ad script. Use the REAL customer data below.

=== BRAND ===
Brand: {context['brand_name']}
Sector: {context['sector']}
Products: {context['products']}
Value Props: {context['value_props']}
Target: {context['target_audience']}

=== TARGET CUSTOMER PERSONAS ({len(context['icps'])} identified) ===
{chr(10).join(context['icps']) if context['icps'] else 'General audience in the ' + context['sector'] + ' space'}

=== REAL CUSTOMER PAIN POINTS ({len(context['pain_points'])} from scraped data) ===
{chr(10).join(context['pain_points']) if context['pain_points'] else '- Common frustrations in this category'}

=== CUSTOMER LANGUAGE - USE THESE EXACT PHRASES! ===
These are the exact words and expressions customers use. Incorporate them to sound authentic:
{chr(10).join(context.get('customer_language', [])) if context.get('customer_language') else '- Natural conversational language'}

=== WHAT CUSTOMERS WANT (desires) ===
{chr(10).join(context.get('customer_desires', [])) if context.get('customer_desires') else '- Better solutions, convenience, results'}

=== VERBATIM CUSTOMER QUOTES ({len(context['verbatim_quotes'])} real quotes) ===
These are real quotes from Reddit, Trustpilot, reviews, and social media. Incorporate at least 3-4 into your script:
{chr(10).join(context['verbatim_quotes']) if context['verbatim_quotes'] else '- "I wish there was a better solution"'}

=== MESSAGING ANGLES THAT RESONATE (with evidence) ===
{chr(10).join(context.get('messaging_angles', [])) if context.get('messaging_angles') else '- Value-focused messaging'}

=== PURCHASE TRIGGERS (what makes people buy) ===
{chr(10).join(context.get('purchase_triggers', [])) if context.get('purchase_triggers') else '- Urgency and social proof'}

=== OBJECTIONS TO ADDRESS ({len(context['objections'])} identified) ===
Pick one objection and weave the counter naturally into the script:
{chr(10).join(context['objections']) if context['objections'] else 'OBJECTION: "Is it worth the price?"\nCOUNTER: Focus on value and results'}

=== RESEARCH-BACKED HOOK SUGGESTIONS ===
These hooks were identified from analyzing customer language and pain points:
{chr(10).join(context.get('recommended_hooks', [])) if context.get('recommended_hooks') else '- Use pain point questions\n- Use customer language verbatims'}

=== WHAT'S WORKING (from {len(context.get('transcription_examples', []))} analyzed ads) ===
Winning Frameworks: {', '.join(context['top_frameworks']) if context['top_frameworks'] else 'Problem-Solution, Testimonial'}
Winning Hook Types: {', '.join(context['top_hooks']) if context['top_hooks'] else 'Question, Statement'}
Emotions that Convert: {', '.join(context['top_emotions']) if context['top_emotions'] else 'Relief, Curiosity'}
Avg Hook Strength: {context['avg_hook_strength']}/5

=== SUCCESSFUL AD TRANSCRIPTIONS (model your script after these) ===
{chr(10).join(context['transcription_examples'][:5]) if context['transcription_examples'] else 'No examples available - create based on best practices'}

=== REAL BRAND AD EXAMPLES (analyzed from Ad Library) ===
These are real ads from {context['brand_name']} that have been analyzed. Study their structure:
{chr(10).join(context.get('brand_ad_examples', [])[:3]) if context.get('brand_ad_examples') else 'No brand ad examples available'}

=== COMPETITOR AD EXAMPLES (what competitors are doing) ===
{chr(10).join(context.get('competitor_ad_examples', [])[:3]) if context.get('competitor_ad_examples') else 'No competitor ad examples available'}

=== TOP PERFORMING HOOKS FROM ADS (proven to work) ===
These hooks are from actual analyzed ads with high hook strength scores:
{chr(10).join(context.get('best_hooks_from_ads', [])[:8]) if context.get('best_hooks_from_ads') else 'No hook data available'}

=== COMPETITOR HOOKS (for competitive awareness) ===
{chr(10).join(context.get('competitor_hooks', [])) if context.get('competitor_hooks') else 'No competitor data'}

=== INDUSTRY-SPECIFIC HOOK TEMPLATES (proven patterns for {context['sector']}) ===
Use these proven hook structures, adapting them to {context['brand_name']}:
{chr(10).join('• ' + h for h in context.get('industry_hook_templates', [])) if context.get('industry_hook_templates') else '• Standard hook patterns'}

=== TIKTOK TRENDING INSIGHTS (what's working on TikTok right now) ===
{chr(10).join(context.get('tiktok_insights', [])) if context.get('tiktok_insights') else 'No TikTok-specific data available'}

=== INSTAGRAM BRAND VOICE (how this brand sounds/looks on Instagram) ===
Use these to maintain brand consistency:
{chr(10).join(context.get('instagram_brand', [])) if context.get('instagram_brand') else 'No Instagram brand data available'}

=== HOOKS LIBRARY (proven hooks from creative briefs) ===
{chr(10).join(context.get('hooks_from_library', [])) if context.get('hooks_from_library') else 'No hooks library available'}

=== YOUR TASK ===
Framework: {framework}
Hook Type: {hook_type}

CRITICAL REQUIREMENTS:
1. First 3 seconds: Pattern-interrupt hook that scores 4+/5 (use the RECOMMENDED HOOKS and study the transcription examples)
2. USE CUSTOMER'S EXACT WORDS from verbatim quotes AND customer language phrases - don't paraphrase!
3. Address one specific objection from the list - show how to counter it naturally
4. Connect to customer DESIRES - show them getting what they want
5. Include 8-12 distinct scenes with detailed visual and audio directions
6. End with a clear, compelling CTA that creates urgency
7. Make it feel authentic, not like an ad - more like a real person sharing their experience

Return this exact JSON structure:
{{
    "script_name": "Catchy descriptive name that hints at the angle",
    "framework": "{framework}",
    "hook_type": "{hook_type}",
    "hook": "The exact opening 3 seconds - make it impossible to scroll past",
    "hook_strength_estimate": 4,
    "target_emotion": "Primary emotion this script evokes",
    "target_persona": "Which ICP this script speaks to",
    "estimated_length_seconds": 75,
    "full_script": "COMPLETE script with [VISUAL: description], [AUDIO: what's said], [TEXT OVERLAY: caption] for each scene. 200-300 words, ready to shoot.",
    "scene_breakdown": [
        {{"scene": 1, "duration": "0-3s", "visual": "Detailed visual description", "audio": "Exact dialogue", "text_overlay": "Caption text"}},
        {{"scene": 2, "duration": "3-10s", "visual": "Description", "audio": "Dialogue", "text_overlay": ""}},
        {{"scene": 3, "duration": "...", "visual": "...", "audio": "...", "text_overlay": "..."}}
    ],
    "cta": "Specific call to action with urgency element",
    "why_it_works": "Data-backed explanation referencing specific pain points, quotes, and customer language you used",
    "verbatims_used": ["Exact quote 1 you incorporated", "Exact quote 2 you used", "Exact quote 3"],
    "customer_language_used": ["Exact phrase 1 from customer language", "Phrase 2 you incorporated"],
    "desire_addressed": "Which customer desire this script fulfills",
    "objection_addressed": "The specific objection this handles and how",
    "pain_points_addressed": ["Pain point 1", "Pain point 2", "Pain point 3"]
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
            
            part = f"[SCENE {s_num} - {dur}]"
            if visual:
                part += f"\n[VISUAL: {visual}]"
            if audio:
                part += f"\n\"{audio}\""
            if text:
                part += f"\n[TEXT: {text}]"
            parts.append(part)
        
        return "\n\n".join(parts)
    
    def _create_fallback_script(self, brand_name: str, framework: str, num: int) -> Dict[str, Any]:
        """Create professional fallback script."""
        return {
            "script_name": f"{framework} Script #{num}",
            "framework": framework,
            "hook_type": "Problem Statement",
            "hook": f"Still struggling with [problem]? Here's what finally worked for me...",
            "hook_strength_estimate": 4,
            "target_emotion": "Relief",
            "estimated_length_seconds": 60,
            "full_script": f"""[SCENE 1 - 0-3s]
[VISUAL: Close-up, frustrated expression]
"I was SO tired of dealing with [problem]..."

[SCENE 2 - 3-12s]
[VISUAL: B-roll showing the struggle]
"I tried everything. Nothing worked."

[SCENE 3 - 12-25s]
[VISUAL: Discovery moment]
"Then someone told me about {brand_name}..."

[SCENE 4 - 25-40s]
[VISUAL: Using product, genuine reaction]
"And honestly? It changed everything."

[SCENE 5 - 40-52s]
[VISUAL: Results/transformation]
"Now I [benefit]. Every single day."

[SCENE 6 - 52-60s]
[VISUAL: Direct to camera with product]
"Click the link and try {brand_name}. You'll thank me later."
[TEXT: Link in bio / Shop now]
""",
            "scene_breakdown": [
                {"scene": 1, "duration": "0-3s", "visual": "Close-up frustrated face", "audio": "I was SO tired of dealing with [problem]...", "text_overlay": ""},
                {"scene": 2, "duration": "3-12s", "visual": "B-roll problem", "audio": "I tried everything. Nothing worked.", "text_overlay": ""},
                {"scene": 3, "duration": "12-25s", "visual": "Discovery", "audio": f"Then someone told me about {brand_name}...", "text_overlay": ""},
                {"scene": 4, "duration": "25-40s", "visual": "Using product", "audio": "And honestly? It changed everything.", "text_overlay": ""},
                {"scene": 5, "duration": "40-52s", "visual": "Results", "audio": "Now I [benefit]. Every single day.", "text_overlay": ""},
                {"scene": 6, "duration": "52-60s", "visual": "CTA", "audio": f"Click the link and try {brand_name}.", "text_overlay": "Shop now"},
            ],
            "cta": f"Click the link and try {brand_name}. You'll thank me later.",
            "why_it_works": "Problem-solution framework with personal story creates relatability",
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
