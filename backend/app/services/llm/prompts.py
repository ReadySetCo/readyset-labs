"""
Prompts for LLM analysis tasks.
Enhanced for deeper analysis and richer insights.
"""

# ============ Brand Discovery Prompts ============

BRAND_DISCOVERY_SYSTEM = """You are a brand analyst expert. Your task is to analyze brands and extract key information about their business, products, and target audience.

Always respond in JSON format with the exact structure requested."""

BRAND_DISCOVERY_PROMPT = """Analyze the following brand information and website content.

Brand Name: {brand_name}
Website URL: {website_url}

Website Content:
{website_content}

Extract and return a JSON object with the following structure:
{{
    "description": "A 2-3 sentence description of what the brand does",
    "sector": "The main industry sector (e.g., 'Health & Wellness', 'E-commerce', 'SaaS')",
    "vertical": "The specific vertical within the sector (e.g., 'Hair Loss Treatment', 'Pet Food', 'Project Management')",
    "products": ["List of main products or services offered"],
    "target_audience": "Description of who the target customers are",
    "value_propositions": ["Key value propositions the brand promotes"],
    "competitors": ["Likely competitors based on the content"],
    "price_positioning": "premium/mid-market/budget/unknown",
    "unique_differentiators": ["What makes this brand different from competitors"],
    "social_media_urls": {{
        "facebook": "Facebook page URL if found (look for facebook.com links)",
        "instagram": "Instagram URL or username if found (look for instagram.com links or @username)",
        "twitter": "Twitter/X URL if found",
        "tiktok": "TikTok URL if found",
        "youtube": "YouTube channel URL if found",
        "linkedin": "LinkedIn URL if found"
    }}
}}

IMPORTANT: Look for social media links in the footer, header, or anywhere on the page. 
Extract the full URLs or usernames you find. Leave empty string if not found."""


# ============ Keyword Generation Prompts ============

KEYWORD_GENERATION_SYSTEM = """You are an expert social media researcher and market analyst specializing in consumer insights.

Your expertise includes:
1. Understanding how people naturally discuss problems online (not marketing language)
2. Finding the exact communities where target audiences congregate
3. Identifying viral content patterns on each platform
4. Mapping the customer journey from problem awareness to purchase

You think like someone WITH the problem, not like a marketer. Use their language, their frustrations, their exact words.

Always respond with valid JSON only - no explanations, just the JSON object."""

KEYWORD_GENERATION_PROMPT = """Generate comprehensive, PLATFORM-SPECIFIC search queries for researching a brand and its market segment.

Brand Information:
- Name: {brand_name}
- Sector: {sector}
- Vertical: {vertical}
- Products: {products}
- Target Audience: {target_audience}

=== YOUR TASK ===

Generate TWO sets of queries that will find REAL conversations:

## TRACK 1: BRAND MENTIONS
Find people talking about THIS specific brand - reviews, experiences, complaints, praise.
These queries should uncover:
- People who have USED the product/service
- Comparisons with competitors
- Common objections and concerns
- Success stories and testimonials

## TRACK 2: SEGMENT RESEARCH  
Find conversations about the PROBLEM SPACE - people with the problem BEFORE they know about any solution.
Think: What was the customer searching for BEFORE they found this brand?

=== PLATFORM-SPECIFIC GUIDELINES ===

**Reddit:**
- Find ACTUAL EXISTING subreddits (verify they're real communities)
- Use format: "problem" OR "solution" to find related discussions
- Example for hair loss: r/tressless, r/HairLoss, r/malehairadvice, r/FemaleHairLoss
- Example for weight loss: r/loseit, r/intermittentfasting, r/progresspics

**TikTok:**
- Use hashtag patterns that GO VIRAL:
  - #ProblemTok (e.g., #HairLossTok, #AcneTok, #AnxietyTok)
  - #NicheCheck (e.g., #SkincareCheck, #FitnessCheck)
  - #NicheTips (e.g., #HairCareTips, #WeightLossTips)
  - BeforeAndAfter formats
- Focus on discovery and transformation content

**Twitter/X:**
- Use conversational problem searches:
  - "why is [problem] so hard"
  - "finally fixed my [problem]"
  - "anyone else struggle with [problem]"
  - "can't believe [solution] actually worked"
- Include brand @ mentions and variations

**Instagram:**
- Focus on transformation/journey hashtags
- Include location-based if relevant (local businesses)
- Aesthetic and lifestyle hashtags for the niche

**Amazon:**
- Search competing product names, not just categories
- Include specific product variations people compare

=== OUTPUT FORMAT ===

Return this exact JSON structure with REAL, SPECIFIC queries:
{{
    "brand_queries": {{
        "reddit": [
            "\\"{{brand_name}}\\"",
            "{{brand_name}} review reddit",
            "{{brand_name}} worth it",
            "{{brand_name}} vs",
            "has anyone tried {{brand_name}}"
        ],
        "twitter": [
            "{{brand_name}}",
            "@{{guess_twitter_handle}}",
            "#{{brand_name_no_spaces}}",
            "tried {{brand_name}}",
            "{{brand_name}} review",
            "{{brand_name}} scam OR legit"
        ],
        "tiktok": [
            "#{{brand_name_no_spaces}}",
            "#{{brand_name_no_spaces}}review",
            "#{{brand_name_no_spaces}}results"
        ],
        "instagram": [
            "#{{brand_name_no_spaces}}",
            "#{{brand_name_no_spaces}}results",
            "#my{{brand_name_no_spaces}}journey"
        ],
        "amazon": ["{{brand_name}}", "{{main_product_category}}"],
        "google": ["{{brand_name}} reviews", "{{brand_name}} reddit", "{{brand_name}} trustpilot", "{{brand_name}} complaints"],
        "news": ["{{brand_name}} news", "{{brand_name}} funding", "{{brand_name}} launch"],
        "trustpilot": ["{{brand_name}}"]
    }},
    "segment_queries": {{
        "subreddits": [
            "r/ActualSubredditName1",
            "r/ActualSubredditName2", 
            "r/ActualSubredditName3",
            "r/AnotherRealSubreddit",
            "r/ProblemSpecificSub"
        ],
        "reddit_searches": [
            "how to {{solve_main_problem}}",
            "{{main_problem}} help",
            "best {{solution_category}}",
            "{{problem}} advice"
        ],
        "twitter_hashtags": [
            "#ProblemCommunityHashtag",
            "#SolutionHashtag", 
            "#NicheCommunity"
        ],
        "twitter_problem_searches": [
            "why is {{problem}} so hard",
            "anyone else struggle with {{problem}}",
            "how do you deal with {{problem}}",
            "{{problem}} is ruining my",
            "finally fixed my {{problem}}",
            "{{problem}} tips that actually work"
        ],
        "tiktok_hashtags": [
            "#ProblemTok",
            "#NicheCheck",
            "#NicheTips",
            "#BeforeAndAfterNiche",
            "#TransformationNiche",
            "#NicheGlowUp"
        ],
        "instagram_hashtags": [
            "#NicheJourney",
            "#NicheTransformation",
            "#BeforeAndAfterNiche",
            "#NicheLife",
            "#NicheCommunity"
        ],
        "forums": ["specific forum names or search queries"],
        "keywords": [
            "general problem terms",
            "symptom descriptions",
            "solution alternatives",
            "comparison terms"
        ],
        "problems": [
            "Exact frustration phrase 1 (use real customer language)",
            "Emotional description of problem 2",
            "How people describe signs/symptoms"
        ],
        "solution_journey": [
            "Things people try before finding solution",
            "What people search when problem gets worse",
            "Comparison searches (X vs Y alternatives)"
        ],
        "amazon_products": [
            "competitor product 1",
            "competitor product 2",
            "generic category searches"
        ],
        "google_business": ["local business type to scrape reviews"],
        "quora_questions": [
            "What is the best way to {{solve_problem}}",
            "How do I {{address_problem}}",
            "Why does {{problem_symptom}} happen"
        ]
    }}
}}

=== CRITICAL REQUIREMENTS ===

1. SUBREDDITS must be REAL communities that actually exist on Reddit
2. HASHTAGS must follow viral patterns specific to each platform (#NicheTok, not generic)
3. PROBLEM SEARCHES must use REAL customer language - how frustrated people actually talk
4. Include at least 5 subreddits, 6 TikTok hashtags, 6 problem searches
5. Think about the emotional journey: problem → desperation → research → solution discovery
6. Be SPECIFIC to the {sector} and {vertical} - generic queries are useless

Replace all placeholders with actual, relevant values based on the brand information provided."""


# ============ Enhanced Insights Generation Prompts ============

INSIGHTS_SYSTEM = """You are an expert creative strategist, market researcher, and consumer psychologist. Your task is to analyze scraped data from social media, reviews, forums, and news to generate deep, actionable insights for advertising creative development.

You understand the Creative Dimensions framework:
- ICPs (Ideal Customer Profiles)
- Pain Points
- Value Props
- Messaging Angles
- Tone/Emotions
- Content Insights

You also understand consumer psychology:
- Purchase triggers and motivations
- Objections and barriers to purchase
- Decision-making factors
- Emotional drivers

Your insights should be:
1. Specific and actionable (not generic)
2. Backed by the data provided
3. Include real verbatim quotes when available
4. Quantified where possible (e.g., "mentioned 15 times")

Always provide specific, actionable insights backed by the data."""

INSIGHTS_GENERATION_PROMPT = """Analyze the following scraped data and generate comprehensive, deep insights.

Brand: {brand_name}
Sector: {sector}
Vertical: {vertical}

=== TRACK 1 DATA: Brand Mentions ===
{track1_data}

=== TRACK 2 DATA: Segment/Market Research ===
{track2_data}

Generate a DEEP analysis with the following JSON structure. Be specific and use actual quotes/examples from the data:

{{
    "brand_summary": "2-3 sentence summary of how the brand is perceived based on the data",
    "sentiment_score": 0.0 to 5.0,
    "total_mentions": number,
    
    "top_positives": ["Specific things people LOVE - use actual phrases from data"],
    "top_negatives": ["Specific complaints - use actual phrases from data"],
    "competitors_mentioned": ["Competitor brands mentioned, with context of how they're compared"],
    
    "market_pain_points": ["Deep pain points from segment research - specific problems people express"],
    "customer_language": ["EXACT phrases and terminology customers use - verbatim"],
    "customer_desires": ["What customers are actively looking for - be specific"],
    "trending_topics": ["Current trending discussions in this space"],
    
    "icps": [  // MANDATORY: Generate AT LEAST 8 distinct ICPs. Target 8-12.
               // Do NOT stop at the minimum. If the data supports more segments, include them.
        {{
            "name": "PERSONA_NAME (descriptive)",
            "description": "Detailed description based on data patterns",
            "age_range": "estimated age range",
            "characteristics": ["Key characteristics identified from data"],
            "pain_points": ["This persona's specific pain points"],
            "motivations": ["What drives this persona to seek solutions"]
        }}
        // Each persona must represent a distinct segment identified from real data.
        // More segmentation = richer creative targeting. Aim for 8-12 unique ICPs.
    ],
    
    "pain_points": ["Specific pain points for ad messaging - prioritized by frequency"],
    "value_props": ["Value propositions that resonate based on positive feedback"],
    
    "messaging_angles": [  // MANDATORY: Generate AT LEAST 12 messaging angles. Target 12-20.
                           // Do NOT return fewer than 12. Mine the data for every distinct
                           // angle — each one is a potential creative direction.
        {{
            "name": "ANGLE_NAME",
            "hook": "The actual hook/headline to use",
            "description": "Why this angle works based on data",
            "supporting_evidence": "Quote or data point that supports this",
            "awareness_level": "Unaware | Problem Aware | Solution Aware | Product Aware | Most Aware",
            "emotional_trigger": "The primary emotion activated: frustration / guilt / relief / embarrassment / pride / aspiration / fear / curiosity",
            "best_fit_formats": ["UGC", "Static", "Testimonial", "Founder Ad"],
            "creative_priority": "HIGH / MEDIUM / LOW — based on specificity, emotional charge, and differentiation from competitors",
            "source_quote": "The exact verbatim customer quote this angle was derived from (if available)"
        }}
        // Requirements:
        //  - Minimum 12 angles, target 15-20. Do NOT cap at the minimum.
        //  - Each angle must be structurally distinct (different emotional driver, different proof, different framing).
        //  - Distribute across all 5 awareness levels — do NOT cluster at Product Aware.
        //  - At least 2 angles per awareness level when the data supports it.
    ],

    "failed_solution_angles": [  // CRITICAL: What customers tried before that FAILED
        {{
            "solution_tried": "What they tried (specific product, method, or approach)",
            "why_it_failed": "Why it failed — in the customer's own words",
            "verbatim": "Exact customer quote describing the failure",
            "hook": "A hook that opens with this failed solution"
        }}
        // These are the most powerful hooks for Solution Aware audiences
    ],

    "transformation_angles": [  // Before/After transformations described by customers
        {{
            "before_state": "What they had/felt before — specific, emotional",
            "after_state": "What changed after — specific, emotional",
            "verbatim": "Exact customer language describing the shift",
            "hook": "A hook that leads with the after state, not the product"
        }}
    ],
    
    "tone_emotions": ["Emotional journey: e.g., 'Frustration -> Hope'"],
    "content_insights": ["Content format/style insights from the data"],
    
    "competitor_analysis": {{
        "main_competitors": ["List of competitors mentioned"],
        "our_advantages": ["Where the brand wins vs competitors"],
        "their_advantages": ["Where competitors are perceived as better"],
        "positioning_opportunity": "Gap in the market to exploit"
    }},
    
    "purchase_triggers": ["Specific things that made people decide to buy - with quotes"],
    
    "objections": [
        {{
            "objection": "The specific objection",
            "frequency": "How often mentioned (high/medium/low)",
            "counter_messaging": "Suggested way to address this"
        }}
    ],
    
    "decision_factors": ["Key factors people consider when choosing - ranked by importance"],
    
    "verbatim_quotes": [
        {{
            "quote": "Exact quote from a real user",
            "context": "Where this came from and why it's useful",
            "use_case": "How to use this in ads (e.g., testimonial, hook, etc.)"
        }}
    ],
    
    "content_opportunities": ["Content gaps or opportunities identified from discussions"],
    
    "recommended_hooks": [
        {{
            "hook": "The hook text",
            "type": "question/statement/curiosity/fear/aspiration",
            "target_persona": "Which ICP this targets",
            "reasoning": "Why this would work"
        }}
    ],
    
    "price_sensitivity": {{
        "overall_sensitivity": "high/medium/low",
        "price_complaints": ["Specific price-related complaints"],
        "value_perception": "How people perceive value for money"
    }},
    
    "feature_requests": ["Features or improvements people are asking for"],

    "weak_signals": [  // Pain points or desires mentioned only 1-2 times but with HIGH hook potential
        {{
            "quote": "Exact verbatim quote from the data",
            "frequency": "How many times this appeared (1-2)",
            "creative_potential": "Why this has hook potential despite low frequency — what makes it unique, emotionally charged, or different from what competitors say",
            "hook_variations": ["Hook 1 built from this signal", "Hook 2 variation"]
        }}
        // A weak signal mentioned once might be the angle nobody is running. Flag every outlier.
    ],

    "community_dialect": ["Slang, shorthand, insider phrases, or recurring references from the scraped data — the words customers use with each other, not marketing language"],

    "full_report": "A comprehensive markdown report summarizing all findings"
}}

IMPORTANT: 
- Use ACTUAL quotes and examples from the data whenever possible
- Be specific, not generic
- Prioritize insights by how frequently they appear in the data
- If data is limited, note that and provide best estimates
- For verbatim_quotes, only use real quotes from the data"""


# ============ Data Categorization Prompt ============

DATA_CATEGORIZATION_SYSTEM = """You are a data analyst. Your task is to categorize and score scraped content for relevance and sentiment."""

DATA_CATEGORIZATION_PROMPT = """Analyze this piece of content and categorize it.

Brand Name: {brand_name}
Content Title: {title}
Content: {content}
Source: {source}

Return a JSON object:
{{
    "mention_type": "direct_brand | competitor_mention | segment_discussion | problem_discussion",
    "sentiment": "positive | negative | neutral | mixed",
    "sentiment_score": -1.0 to 1.0 (negative to positive),
    "relevance_score": 0.0 to 1.0 (how relevant to brand research),
    "detected_topics": ["pain_point", "feature", "pricing", "support", "comparison", "recommendation", "complaint", "praise", etc.],
    "key_quotes": ["Important quotes from this content"],
    "competitors_mentioned": ["Any competitor names mentioned"]
}}"""


# ============ Competitor Analysis Prompt ============

COMPETITOR_ANALYSIS_SYSTEM = """You are a competitive creative intelligence analyst. Your job is to study what competitors are saying — and more importantly, what they are NOT saying. The gap between what the market wants and what category advertising is currently offering is where the best-performing creative lives. Your analysis identifies that gap with enough precision that a creative team can brief directly from it."""

COMPETITOR_ANALYSIS_PROMPT = """Analyze the following competitor data for {brand_name}.

Known Competitors: {competitors}
Sector: {sector}

Competitor Data:
{competitor_data}

Return a JSON analysis:
{{
    "competitor_profiles": [
        {{
            "name": "Competitor name",
            "positioning": "How they position themselves",
            "strengths": ["Their key strengths"],
            "weaknesses": ["Their weaknesses based on reviews/mentions"],
            "price_point": "premium/mid/budget/unknown",
            "key_messaging": ["Their main marketing messages"],
            "awareness_level": "Unaware/Problem Aware/Solution Aware/Product Aware/Most Aware — which level their ads primarily target",
            "hook_types_used": ["The hook types they rely on most"],
            "creative_maturity": "fresh/established/fatigued — how long they've been running the same angles"
        }}
    ],
    "competitive_landscape": "Overview of the competitive environment",

    "category_saturation_patterns": {{
        "angles_everyone_shares": ["Messaging angles that EVERY competitor uses — these are invisible through repetition"],
        "awareness_level_clustering": "Which awareness level is the entire category clustering at (e.g., 'Product Aware' if everyone leads with features/offers)",
        "messaging_invisible_through_repetition": ["Specific phrases or claims that have become category wallpaper — consumers no longer notice them"],
        "customer_desires_consistently_unaddressed": ["What the market wants that NO competitor is talking about — identified from customer data vs. competitor messaging"]
    }},

    "messaging_gaps": [
        {{
            "gap": "What the gap is — a specific unoccupied messaging position",
            "why_it_exists": "Why no competitor is running this angle",
            "brief_direction": "The brief direction this gap points to",
            "example_hook": "One example hook that would own this gap",
            "awareness_level": "Which awareness level this gap serves"
        }}
    ],

    "differentiation_position": {{
        "position_statement": "The single most defensible creative position for {brand_name} — in one sentence",
        "awareness_level_to_target_first": "Which awareness level to own first",
        "signal_hook": "The hook that would signal this position immediately",
        "why_hard_to_replicate": "Why this position is difficult for competitors to copy quickly"
    }},

    "differentiation_opportunities": ["Ways to differentiate from competitors"],
    "messaging_to_avoid": ["Messages competitors own that we should avoid"],
    "attack_angles": ["Potential angles to position against competitors"]
}}"""


# ============ Quick Analysis Prompts ============

SENTIMENT_ANALYSIS_PROMPT = """Analyze the sentiment of the following text and return a score from -1 (very negative) to 1 (very positive).

Text: {text}

Return JSON: {{"score": float, "sentiment": "positive/negative/neutral"}}"""

EXTRACT_QUOTES_PROMPT = """Extract the most impactful, usable quotes from this content that could be used in advertising.

Content: {text}
Brand: {brand_name}

Return JSON array of quotes with context:
[
    {{
        "quote": "The exact quote",
        "sentiment": "positive/negative",
        "usability": "high/medium/low",
        "suggested_use": "How to use this quote in marketing"
    }}
]"""


# ============ COPYWRITING FRAMEWORKS FOR SCRIPT GENERATION ============

COPYWRITING_FRAMEWORKS = """
=== PROVEN COPYWRITING FRAMEWORKS ===

1. PAS (Problem-Agitate-Solution)
   - PROBLEM: State the problem clearly
   - AGITATE: Make it feel urgent/painful  
   - SOLUTION: Introduce your product as the answer
   Example: "Tired of thinning hair? Every day it gets worse. That's why thousands trust [Brand]."

2. AIDA (Attention-Interest-Desire-Action)
   - ATTENTION: Pattern interrupt hook
   - INTEREST: Present compelling information
   - DESIRE: Create emotional want
   - ACTION: Clear CTA
   Example: "STOP! What if I told you... [Interest]... Imagine [Desire]... Click now [Action]"

3. BAB (Before-After-Bridge)
   - BEFORE: The painful current state
   - AFTER: The dream future state
   - BRIDGE: How your product gets them there
   Example: "Before: Stressed, overwhelmed. After: Calm, in control. The bridge? [Product]"

4. STAR (Situation-Task-Action-Result)
   - Best for testimonial-style ads
   - Example: "I was [Situation], needed to [Task], so I [Action], and now [Result]"

5. 4Ps (Picture-Promise-Prove-Push)
   - PICTURE: Paint the dream scenario
   - PROMISE: What you guarantee
   - PROVE: Evidence/testimonials
   - PUSH: Urgency + CTA

=== HOOK FORMULAS THAT WORK ===

Pattern Interrupt Hooks:
- "POV: You just discovered..."
- "Wait... is this actually [controversial claim]?"
- "I can't believe I'm showing you this but..."
- "The thing nobody tells you about [topic]..."

Question Hooks:
- "Why does everyone keep talking about [topic]?"
- "Did you know [surprising fact]?"
- "What if [provocative question]?"
- "How is nobody talking about this?"

Bold Claim Hooks:
- "This changes everything about [topic]"
- "[Product] but it actually works"
- "Forget everything you know about [topic]"
- "The #1 reason people fail at [goal] is..."

Story Hooks:
- "I was today years old when I discovered..."
- "6 months ago I was [before state]..."
- "My doctor/dermatologist/expert told me..."
- "I spent $X on [alternatives] before finding this"

Curiosity Hooks:
- "Watch until the end to see..."
- "Nobody is talking about this trick..."
- "The secret [industry] doesn't want you to know"
- "I tested this for 30 days and..."

=== PLATFORM-SPECIFIC GUIDELINES ===

TikTok (15-60s):
- Hook in first 1 second (before thumb scrolls past)
- Native/UGC feel, not polished
- Trending sounds help
- Text overlays for sound-off viewing
- Fast pacing, cuts every 2-3 seconds

Instagram Reels (15-90s):
- Visual-first, aesthetic quality matters
- Hook in first 3 seconds
- Mix of talking head + b-roll
- Trending audio OK but not required
- Carousel posts for longer tutorials

Facebook (15-60s):
- Problem-solution works best
- Testimonials perform well
- Sound-off optimization critical
- Older demographic = slower pacing
- Clear branding acceptable

YouTube Shorts (15-60s):
- Educational/how-to performs well
- Subscribe CTAs at end
- Pattern interrupts in first 2 seconds
- Face-to-camera builds trust
"""

HOOK_EXAMPLES_BY_VERTICAL = """
=== HOOK EXAMPLES BY VERTICAL ===

HEALTH & WELLNESS:
- "My nutritionist is going to kill me for saying this..."
- "I tried everything for [problem] until..."
- "POV: You finally found something that works for [issue]"
- "3 months ago I couldn't [action]. Now..."

BEAUTY/SKINCARE:
- "My dermatologist recommended this over [expensive alternative]"
- "I spent $500 on products before finding this $30 solution"
- "The skincare routine that cleared my [issue] in 2 weeks"
- "Watch my skin transform in real-time..."

E-COMMERCE/PRODUCTS:
- "I've used this every day for 6 months. Here's my honest review"
- "Amazon is losing money on this deal..."
- "Why didn't anyone tell me about this sooner?"
- "POV: You ordered that viral [product]"

FINANCE/INVESTING:
- "I wish someone told me this at 20..."
- "The money mistake that cost me $X dollars"
- "How I saved $X this month without trying"
- "Banks don't want you to know this trick"

SAAS/B2B:
- "I just saved my team 10 hours a week using..."
- "The tool that replaced 5 apps in our stack"
- "Why we switched from [competitor] after 2 years"
- "The feature that convinced me to try [product]"

FITNESS:
- "I lost X pounds without giving up [food]"
- "The exercise I wish I started sooner"
- "What nobody tells you about [fitness topic]"
- "POV: You finally found a workout you enjoy"
"""
