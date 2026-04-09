# CORE PRINCIPLES - Brand Intelligence Scraper

> **CRITICAL DOCUMENT** - This defines the fundamental philosophy and technical requirements.
> MUST be understood by anyone working on this project.

---

## The Golden Rule

**EVERY PIECE OF DATA SCRAPED MUST SERVE A PURPOSE**

If we scrape it, it must:
1. Be analyzed (not just stored)
2. Inform the outputs (scripts, hooks, ICPs, dimensions creativas)
3. Add value to the final deliverables

**NO PLACEHOLDERS. NO TEMPLATES. REAL, DATA-DRIVEN OUTPUTS.**

---

## Data Flow Philosophy

```
SCRAPE → ANALYZE → SYNTHESIZE → GENERATE
   ↓         ↓          ↓           ↓
 Volume    Gemini    Insights    Scripts
  100+     per item   patterns    hooks
  posts    extract    themes      ICPs
                                  todas las
                                  dimensiones
```

---

# PLATFORM-BY-PLATFORM EXTRACTION

## Reddit

### How It Works
- **Firecrawl API** → `search_reddit(query)` and `scrape_subreddit(name)`
- Uses `site:reddit.com` search queries
- Returns: title, content, url, author, upvotes

### Brand Searches (Track 1)
```
"brand_name" site:reddit.com
"brand_name" review reddit
"brand_name" worth it reddit
```

### Niche Searches (Track 2)
```
Subreddits: r/tressless, r/loseit, r/SkincareAddiction (real communities)
Problem queries: "how to fix X", "why does Y happen", "best solution for Z"
```

### What Must Be Extracted
- Post title and full content
- Top comments (real customer language)
- Upvotes as quality signal
- Author for potential reach-out
- Subreddit context

### Goes to Database
→ `ScrapedData` with `source_type="reddit"`, `track=1 or 2`, `mention_type`

### Used By
- InsightsGenerator → pain points, verbatim quotes
- ICPs → real language patterns
- Scripts → authentic phrasing

---

## Twitter/X

### How It Works
- **Apify actor** `apidojo/twitter-scraper-lite` (100 tweets, 10 queries)
- Search by: @mentions, hashtags, keywords

### Brand Searches (Track 1)
```
@brand_handle
#brandname
"brand name" review
tried brand_name
```

### Niche Searches (Track 2)
```
"why is [problem] so hard"
"finally fixed my [problem]"
"anyone else struggle with [problem]"
#ProblemHashtag
```

### What Must Be Extracted
- Tweet full text
- Media (images, videos)
- Engagement (likes, retweets, replies)
- Author handle and follower count
- Thread context if reply

### Goes to Database
→ `ScrapedData` with `source_type="twitter"`

### Used By
- Real-time sentiment
- Trending language
- Objection handling phrases

---

## TikTok

### How It Works
- **Apify actor** `clockworks/tiktok-scraper`
- Downloads video files for Gemini analysis

### Brand Content (Track 1) - THE BRAND'S OWN TIKTOK
- Scrape brand's TikTok profile directly
- Get ALL their videos (recent 50-100)
- Analyze THEIR style, hooks, formats
- What trending sounds do THEY use

### Niche Content (Track 2) - THE ECOSYSTEM
- Search hashtags: `#HairLossTok`, `#SkincareCheck`, etc.
- Find what's VIRAL in this space
- Influencers already talking about this category
- Competitor content

### Video Analysis (EVERY VIDEO)
Each video → Gemini extracts:
```json
{
  "transcription": "full verbatim text",
  "hook": "first 3 seconds (critical)",
  "hook_type": "question/statement/visual/action",
  "hook_strength_1to5": 4,
  "content_type": "tutorial/review/trend/story",
  "pacing": "slow/medium/fast",
  "visual_style": "ugc/professional/lofi",
  "audio_type": "voiceover/trending_sound/dialogue",
  "trending_elements": ["sounds", "formats", "effects"],
  "pain_points_mentioned": [],
  "solutions_shown": [],
  "emotional_triggers": [],
  "quotable_phrases": [],
  "what_makes_it_work": "analysis",
  "replication_tips": "how to copy this"
}
```

### Goes to Database
→ `ScrapedData.video_analysis` (JSON field)
→ `ScrapedData.video_file` (path to downloaded file)

### Used By
- Hooks generation (model after best performers)
- Script frameworks
- Thumbnail suggestions
- Trending format detection

---

## Instagram

### How It Works
- **Apify actor** `apify/instagram-scraper`
- Profile scraping + hashtag search

### Brand Content (Track 1)
- Scrape brand's Instagram profile
- Get posts, reels, stories (if possible)
- Analyze their grid aesthetic
- Caption style and CTAs

### Niche Content (Track 2)
- Hashtag searches for niche
- Influencer content analysis
- Competitor grids

### What Must Be Extracted
- Caption (full copy)
- Hashtags used
- Image/video URLs
- Carousel content
- Engagement metrics
- Comments (for sentiment)

### For Reels (video analysis same as TikTok)
→ Gemini analysis with transcription, hooks, etc.

### Goes to Database
→ `ScrapedData` with video_analysis for reels

### Used By
- Visual style patterns
- Caption copywriting
- Hashtag strategy
- Grid aesthetic

---

## Facebook (Ad Library)

### How It Works
- Meta Ad Library URL discovery
- yt-dlp for video downloads
- httpx for image downloads
- Gemini for video analysis

### What Gets Scraped
- ALL active ads for the brand
- ALL ads for each competitor
- Videos, images, carousel ads
- Ad copy/captions
- Start dates (longevity = working)

### Video Analysis (CRITICAL - DEEP)
Each ad video → Gemini extracts:
```json
{
  "transcription": "VERBATIM full script",
  "scene_breakdown": [
    {"time": "0:00-0:03", "visual": "hook shot", "audio": "hook line", "text_overlay": "..."},
    {"time": "0:03-0:10", "visual": "problem agitation", "audio": "...", "text_overlay": "..."}
  ],
  "hook_text": "exact first line",
  "hook_type": "question/statement/statistic/story",
  "hook_strength_1to10": 8,
  "framework": "PAS/AIDA/BAB/HSO/4Ps",
  "effectiveness_score_1to10": 7,
  "creative_dimensions": {
    "tonality": "urgent/friendly/aspirational/educational",
    "style": "ugc/testimonial/professional/animated",
    "pacing": "fast_cuts/slow_build/rhythmic",
    "music_type": "trending/emotional/none",
    "cta_type": "shop_now/learn_more/limited_time",
    "social_proof": "reviews/testimonials/stats/ugc"
  },
  "actor_details": "solo presenter/couple/family/none",
  "setting": "studio/home/outdoor/animated",
  "product_demo": true/false,
  "offer_shown": "20% off/free shipping/etc",
  "urgency_tactics": ["limited time", "only X left"]
}
```

### Goes to Database
→ `Insight.ad_library_data` (brand ads)
→ `Insight.competitor_ads_data` (competitor ads)
→ `Insight.ad_creative_patterns` (aggregated patterns)

### Used By
- Script generation (MUST use these patterns)
- Hook generation (from real performers)
- A/B test suggestions
- Creative dimensions analysis

---

## Trustpilot / Reviews

### How It Works
- **Firecrawl** → `search_trustpilot(brand_name)`
- Also: G2, Capterra for B2B

### What Must Be Extracted
- Full review text
- Star rating
- Review title
- Reviewer info (if available)
- Response from brand (if any)

### Used By
- Objection handling (negative reviews)
- Testimonial mining (positive reviews)
- Pain points (pre-purchase concerns)
- Verbatim quotes for ads

---

## Quora

### How It Works
- **Firecrawl** with `site:quora.com`
- Questions and answers about problems

### What Must Be Extracted
- Question text
- Top answers
- Upvote counts
- Author credentials

### Used By
- Problem awareness stage language
- "What should I do about X" patterns
- Long-form pain point description

---

## Website / Landing Pages

### How It Works
- **Firecrawl** → scrape brand website
- LLM analysis of copy

### What Must Be Extracted
- Headlines (H1, H2)
- Value propositions
- CTAs used
- Pricing information
- Product descriptions
- Testimonials on site
- Colors, fonts (Brand DNA)
- Logo URL
- Social media links

### Used By
- Brand DNA (colors, fonts, aesthetic)
- Messaging consistency check
- Product understanding

---

## Competitors

### Competitor Workflow
1. Discover competitors from Brand Discovery
2. For EACH competitor:
   - Scrape their website
   - Get their Ad Library ads
   - Find mentions in Reddit
   - Check their Trustpilot
3. Build competitor profiles
4. Create competitive matrix
5. SWOT analysis

### Goes to Database
→ `Insight.competitor_profiles`
→ `Insight.competitive_matrix`
→ `Insight.swot_analysis`

### Used By
- Differentiation messaging
- Gap analysis
- Competitive angles

---

# DATABASE FLOW

## ScrapedData Table
```
session_id → Links to ResearchSession
source_type → reddit/twitter/tiktok/instagram/trustpilot/etc
track → 1 (brand) or 2 (niche)
mention_type → direct_brand/segment_discussion/problem_discussion
title, content → The actual scraped text
author, rating, likes, comments_count → Metrics
video_analysis → JSON with Gemini analysis
video_file → Path to downloaded video
raw_data → Original response
```

## Insight Table (ALL CREATIVE DIMENSIONS)
```
# Core Insights
- brand_summary, sentiment_score
- top_positives[], top_negatives[]
- market_pain_points[], customer_language[]

# ICPS (Ideal Customer Profiles)
- icps[] → Each with: name, demographics, psychographics, problems, goals, language

# Messaging
- messaging_angles[] → Specific angles to use
- value_props[] → Value propositions
- objections[] → Common objections + how to handle
- verbatim_quotes[] → Real quotes for ads

# Content Intelligence
- content_insights → From TikTok/IG analysis
- recommended_hooks[] → Best hooks found
- purchase_triggers[] → What makes people buy
- decision_factors[] → Key factors in decisions

# Ad Library Data
- ad_library_data → Brand's ads analysis
- competitor_ads_data → Competitor ads
- ad_creative_patterns → Aggregated patterns

# Generated Content
- generated_scripts[] → Scripts based on patterns
- thumbnail_suggestions[] → First frame ideas
- ab_test_suggestions[] → What to test

# Competitive
- competitor_profiles[]
- competitive_matrix
- swot_analysis
```

---

# ALL CREATIVE DIMENSIONS

The UI displays these sections - ALL must be populated with real data:

## 1. Brand DNA
- Colors (extracted from website)
- Logo URL
- Fonts
- Tagline
- Brand values
- Aesthetic keywords
- Tone of voice

## 2. ICPs (Multiple)
For each ICP:
- Name/archetype
- Demographics
- Psychographics
- Main problems
- Goals/desires
- Language they use
- Where they hang out

## 3. Pain Points
- Categorized by severity
- Verbatim examples
- Source citations

## 4. Value Propositions
- Matched to pain points
- Differentiated from competitors

## 5. Messaging Angles
- Specific angles (not generic)
- Match to ICP
- With example copy

## 6. Hooks
- From analyzed videos
- Categorized by type
- With effectiveness score

## 7. Objections & Rebuttals
- From negative reviews
- How to address each

## 8. Ad Creative Patterns
- Frameworks used (PAS, AIDA)
- Visual styles
- Audio types
- Pacing patterns
- CTAs that work

## 9. Scripts
- Based on Ad Library patterns
- Scene-by-scene
- Multiple versions/angles

## 10. Thumbnails
- Based on top performers
- Color patterns
- Text overlay patterns

## 11. A/B Tests
- What to test
- Based on data patterns

## 12. Verbatim Quotes
- Real customer language
- With source attribution
- For use in ads

## 13. Full Report
- Markdown summary
- All findings compiled

---

# ORCHESTRATOR WORKFLOW

## Optimal Execution Order

```
START
  │
  ├─→ [ASYNC] Ad Library scraping + video download (HEAVY - START FIRST)
  │
  ├─→ [ASYNC] Brand DNA extraction
  │
  ├─→ [ASYNC] Brand Discovery (competitors, sector, etc.)
  │
  └─→ WAIT for DNA + Discovery
        │
        ├─→ Query Generation (needs sector/products info)
        │
        ├─→ [PARALLEL] Track 1 scraping:
        │     - Reddit brand searches
        │     - Twitter brand mentions
        │     - Trustpilot reviews
        │     - TikTok brand hashtags → video download
        │     - Instagram brand → video download
        │
        ├─→ [PARALLEL] Track 2 scraping:
        │     - Subreddits
        │     - Problem searches
        │     - Quora questions
        │     - Niche hashtags
        │
        ├─→ AWAIT video downloads complete
        │
        ├─→ [BATCHED] Video analysis (Gemini)
        │     - TikTok videos
        │     - Instagram reels
        │     - Ad Library videos
        │
        ├─→ AWAIT Ad Library complete
        │
        ├─→ Competitor analysis
        │
        ├─→ Insights generation (WITH ALL DATA)
        │
        ├─→ Content generation:
        │     - Scripts (using Ad patterns)
        │     - Hooks (from video analysis)
        │     - Thumbnails
        │     - A/B tests
        │
        └─→ COMPLETE
```

---

# UI IMPROVEMENTS NEEDED

## Results Page
- [ ] Brand colors display correctly
- [ ] All dimensions cards populated
- [ ] Video analysis expandable sections
- [ ] Thumbnail grid interactive
- [ ] Source filters work

## Ad Intelligence Tab
- [ ] Ad thumbnails grid
- [ ] Video transcription display
- [ ] Pattern aggregation visualization
- [ ] Competitor ads section

## Raw Data Tab
- [ ] Filter by platform
- [ ] Filter by track
- [ ] Search functionality
- [ ] Export capability

## Generated Content Tab
- [ ] Scripts with scene breakdowns
- [ ] Hooks categorized
- [ ] Thumbnails with references
- [ ] A/B tests actionable

---

# VIDEO ANALYSIS REQUIREMENTS

Every video (TikTok, Instagram, Ad Library) MUST be analyzed with Gemini.

## Minimum Fields Required
- `transcription` - Word for word
- `hook` - First 3 seconds
- `hook_type` - question/statement/visual
- `hook_strength_1to5`
- `content_type`
- `key_message`
- `cta_used`

## Advanced Fields (for ads)
- `scene_breakdown[]` - Time-stamped
- `framework` - PAS/AIDA/etc
- `effectiveness_score`
- `creative_dimensions{}`
- `what_makes_it_work`

## Aggregation Required
After individual analysis:
- Top hooks across all videos
- Common frameworks
- Trending formats
- Effective CTAs

---

# FOR FUTURE DEVELOPERS

1. **Read this document FIRST**
2. The value is in SYNTHESIS, not collection
3. Every output must trace back to data
4. No placeholders, no templates
5. Test with real brands
6. Verify data flows end-to-end

**If the outputs don't reflect what was scraped and analyzed, the tool has ZERO value.**

