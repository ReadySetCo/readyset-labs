# -*- coding: utf-8 -*-
"""
Creative Reference Service

Loads and provides access to the creative strategy knowledge base (SLP Concepts Database).
This is used to improve script and hook generation with proven frameworks and examples.
"""

from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


# Creative frameworks extracted from the Deck of Decks / SLP Concepts Database
CREATIVE_FRAMEWORKS = """
# CREATIVE STRATEGY FRAMEWORKS - SLP Concepts Database

## Hook Types (Proven Performers)

### 1. Problem/Solution Hooks
- "That feeling when you realize your [problem]... But then you find [solution]"
- "Can't [achieve goal]? There's a reason why..."
- "I've tried everything for [problem] and nothing worked until..."
- "If you're googling [symptom/problem]... you need this"

### 2. PSA / Call-Out Hooks  
- "PSA to all [target audience]"
- "This is a PSA to start using [product] if you want [benefit]"
- "[Target audience], watch this if you're dealing with [problem]"

### 3. Myth-Busting Hooks
- "Myth: [common misconception]. Reality: [truth]"
- "POV: [negative belief]... Reality: [positive truth with product]"
- "Everyone thinks [myth] but actually..."

### 4. Testimonial/Review Hooks
- "I actually thought I was just [problem]. Turns out it was [real cause]..."
- "[Number] reasons why I love [product]"
- "Why I'll never go back to [old way]"
- "This is why I'm using [product] for [benefit]"

### 5. Controversial/Pattern Interrupt Hooks
- "Don't [do thing] like it's the [old year]!"
- "Unpopular opinion: You don't need to [common belief]"
- "If you want to [goal] in [year] then you're late to the party"

### 6. Text Message / Friend Hooks
- "Hey, can you tell me more about that [product] you've been using?"
- "Sis, what's the name of that [product] that [benefit]?"
- "Just me texting my friend about how [product] changed my life"

### 7. FOMO Hooks
- "The 1 thing stopping you from [desired outcome]..."
- "Your [business/life] is losing [money/time] because of 1 thing..."
- "Imagine not knowing there's a [solution] that can [benefit]!"

### 8. How-To / Educational Hooks
- "[Number] steps to [benefit]"
- "This hack will save you [time/money/stress]"
- "Here's how [target audience] should [do thing]"

### 9. Desirable Situation vs Problems
- "When I started my [business/journey]: [list of problems]. Then I found [solution]"
- "How my [clients/friends] think I react to [problem] vs How I actually react..."

### 10. Results-First Hooks
- "My [result] vs my [routine/product]"
- "This is how I finally [achieved result]"
- "The clarity in my [skin/business/life] vs [the product/routine]"


## Ad Body Structures

### Structure 1: Problem → Agitate → Solution
1. Hook with relatable problem
2. Agitate - describe the frustration/pain
3. Introduce solution
4. Walk through features/benefits
5. Show results/testimonials
6. CTA

### Structure 2: Testimonial Journey
1. Personal hook - "I used to struggle with..."
2. Describe the journey/failures
3. Discovery moment - "Until I found..."
4. Product introduction + how it works
5. Results achieved
6. Recommendation + CTA

### Structure 3: Quick Listicle
1. Hook - "[X] reasons why..."
2. Reason 1 + visual proof
3. Reason 2 + visual proof  
4. Reason 3 + visual proof
5. Recap value props
6. CTA

### Structure 4: Walkthrough/How-To
1. Hook - "Here's how to [benefit]"
2. Step 1: [Action]
3. Step 2: [Action]
4. Step 3: [Action]
5. Show result
6. CTA


## Emotional Triggers (by category)

### Weight Loss / Health
- Frustration with failed diets
- Feeling out of control
- Wanting to feel confident
- Sustainable vs quick-fix
- Personalization appeal
- Science-backed trust

### Business/Productivity (B2B)
- Time savings
- Stress reduction
- Work-life balance
- Growth/scaling
- Professionalism
- Competitive advantage

### Skincare/Beauty
- Self-care as priority
- Visible results
- Natural ingredients
- Routine simplicity
- Confidence boost

### Tech/Software
- Speed improvements (10x faster)
- Feeling like "cheating"
- Keeping up with trends
- Free tier appeal
- Automation benefits


## CTA Patterns

- "Get started today"
- "Try [product] free for [time]"
- "Click the link to [specific action]"
- "Don't let [problem] hold you back"
- "Join the [number] of [people] who [benefit]"
- "Start your journey to [desired outcome]"
- "Melt away [pain point] with [product]"


## Platform-Specific Notes

### TikTok
- Native feel essential
- Fast pacing (1-3 second cuts)
- Trending sounds usage
- Text overlays for sound-off
- Green screen popular format
- Comment reply format

### Meta (FB/IG)
- Sound-off first
- Strong opening visual (thumbstop)
- Before/after transitions work well
- Carousel format for listicles
- Longer form acceptable (60-90s)

### YouTube
- Hook within first 5 seconds
- More educational/longer content
- Clear value proposition upfront
"""


INDUSTRY_SPECIFIC_HOOKS = {
    "health_wellness": [
        "I've tried everything for {problem} and nothing worked until...",
        "Stop battling {symptom} - here's how I found relief",
        "{Number} reasons why you should try {product} for {benefit}",
        "Do you wake up every morning with {symptom}?",
        "The biggest {category} mistake you're making...",
        "If you're feeling {symptom_list} - {cause} might be the reason why",
    ],
    "saas_tech": [
        "This {tool_type} feels like cheating",
        "I'm saving HOURS of {task} because of this FREE tool",
        "The tool {job_title}s don't want you to know about",
        "POV: Your boss thinks you've been {working_hard} but thanks to {product}...",
        "This hack will save you hours of {task}",
        "{Target_audience}, you'll ditch {competitor} after watching this",
    ],
    "ecommerce_dtc": [
        "What I ordered vs What I got",
        "I tried {product} to see if the rumors were true",
        "This is my secret to {benefit}",
        "I finally get the hype after trying {product}",
        "My {result} at my {age/stage} vs my {product/routine}",
    ],
    "services_local": [
        "PSA to all {business_type} owners",
        "Is your {business_type} running you?",
        "Every {profession} knows the struggle...",
        "I said goodbye to {pain_point} stress",
        "Wave business stress goodbye with this",
        "If {pain_point} is slowly ruining your business then you need this",
    ],
}


def get_creative_frameworks() -> str:
    """Get the full creative frameworks reference."""
    return CREATIVE_FRAMEWORKS


def get_hooks_for_industry(industry: str) -> list:
    """Get industry-specific hook templates."""
    # Map common industries to our categories
    industry_map = {
        "health": "health_wellness",
        "wellness": "health_wellness",
        "fitness": "health_wellness",
        "supplements": "health_wellness",
        "medical": "health_wellness",
        "pharma": "health_wellness",
        "weight loss": "health_wellness",
        "skincare": "health_wellness",
        "beauty": "health_wellness",
        
        "tech": "saas_tech",
        "software": "saas_tech",
        "saas": "saas_tech",
        "app": "saas_tech",
        "ai": "saas_tech",
        "productivity": "saas_tech",
        
        "ecommerce": "ecommerce_dtc",
        "dtc": "ecommerce_dtc",
        "retail": "ecommerce_dtc",
        "fashion": "ecommerce_dtc",
        "consumer": "ecommerce_dtc",
        
        "services": "services_local",
        "local": "services_local",
        "salon": "services_local",
        "barbershop": "services_local",
        "cleaning": "services_local",
        "home services": "services_local",
    }
    
    # Find matching category
    industry_lower = industry.lower()
    matched_category = None
    
    for key, category in industry_map.items():
        if key in industry_lower:
            matched_category = category
            break
    
    if matched_category and matched_category in INDUSTRY_SPECIFIC_HOOKS:
        return INDUSTRY_SPECIFIC_HOOKS[matched_category]
    
    # Return generic hooks if no match
    return [
        "I've tried everything for {problem} and nothing worked until...",
        "This changed everything for me",
        "Here's what nobody tells you about {topic}",
        "{Number} reasons why I switched to {product}",
        "Stop doing {old_way} - try this instead",
    ]


def get_enhanced_script_prompt(brand_info: dict, insights: dict) -> str:
    """
    Generate an enhanced prompt for script generation that includes
    creative frameworks and industry-specific guidance.
    """
    sector = brand_info.get("sector", "general")
    industry_hooks = get_hooks_for_industry(sector)
    
    prompt = f"""
{CREATIVE_FRAMEWORKS}

---

## Industry-Specific Hooks for {sector.title()}:
{chr(10).join(f'- {hook}' for hook in industry_hooks)}

---

## Brand Context:
- Brand: {brand_info.get('name', 'Unknown')}
- Sector: {sector}
- Products: {brand_info.get('products', [])}
- Value Props: {insights.get('value_props', [])}
- Pain Points: {insights.get('pain_points', [])}
- ICPs: {[icp.get('name', '') for icp in insights.get('icps', [])]}

## Instructions:
Using the creative frameworks above as reference, generate ad scripts that:
1. Start with a HOOK that matches one of the proven hook types
2. Follow a clear body structure (Problem→Solution, Testimonial, or Listicle)
3. Use emotional triggers relevant to the industry
4. End with a compelling CTA
5. Include visual/audio notes for production

The scripts should feel native to TikTok/Meta while incorporating brand-specific insights.
"""
    return prompt


# Singleton instance
_creative_reference_instance = None

def get_creative_reference():
    """Get or create the creative reference instance."""
    global _creative_reference_instance
    if _creative_reference_instance is None:
        _creative_reference_instance = {
            "frameworks": CREATIVE_FRAMEWORKS,
            "industry_hooks": INDUSTRY_SPECIFIC_HOOKS,
        }
    return _creative_reference_instance
