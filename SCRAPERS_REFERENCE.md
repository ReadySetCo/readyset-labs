# Scrapers Reference Guide

Detailed documentation for each scraper in the system.

---

## 1. FirecrawlScraper

**File:** `app/services/scrapers/firecrawl.py`
**API:** Firecrawl v1 (https://firecrawl.dev)

### Rate Limiting
- 2 concurrent requests (global semaphore)
- 2 second minimum between requests
- 429 retry: 3 attempts with 5s + 10s + 15s delays

### Methods

| Method | Platform | Query Type |
|--------|----------|------------|
| `search_reddit(query)` | Reddit | `{query} site:reddit.com` |
| `scrape_subreddit(subreddit)` | Reddit | Scrapes top monthly posts |
| `search_trustpilot(brand)` | Trustpilot | Brand reviews |
| `search_reviews(brand)` | G2, Capterra | Product reviews |
| `search_news_mentions(brand)` | News sites | Brand mentions |
| `search_competitors(brand, sector)` | Web | Competitor comparisons |
| `search_forums(query)` | Forums | Discussion threads |
| `search_youtube_comments(brand)` | YouTube | Video comments |
| `search_quora(query)` | Quora | Q&A discussions |
| `search_medium_articles(brand)` | Medium | Blog posts |
| `search_linkedin_posts(brand)` | LinkedIn | Professional posts |
| `deep_search_segment(keywords)` | Web | Problem/solution discussions |

### Configuration
```python
MAX_POSTS_PER_SOURCE = 100  # in config.py
SCRAPE_TIMEOUT = 60  # seconds
```

---

## 2. ApifyScraper

**File:** `app/services/scrapers/apify.py`
**API:** Apify Cloud (https://apify.com)

### Actors Used

| Platform | Actor | Memory | Timeout |
|----------|-------|--------|---------|
| Twitter/X | `apidojo/tweet-scraper` | 4096 MB | 60s |
| TikTok | `clockworks/tiktok-scraper` | 4096 MB | 60s |
| Instagram | `apify/instagram-scraper` | 4096 MB | 60s |
| Facebook | `apify/facebook-posts-scraper` | 4096 MB | 60s |
| Amazon | `junglee/amazon-reviews-scraper` | 4096 MB | 120s |
| Google Reviews | `compass/google-maps-reviews-scraper` | 4096 MB | 120s |

### Methods

| Method | Purpose | Track |
|--------|---------|-------|
| `scrape_twitter(queries, track)` | Search tweets | 1 or 2 |
| `scrape_tiktok(queries, track)` | Search videos | 1 or 2 |
| `scrape_instagram(queries, track)` | Search posts | 1 or 2 |
| `scrape_facebook(queries)` | Page posts | 1 |
| `scrape_amazon_reviews(products)` | Product reviews | 2 |
| `scrape_google_reviews(businesses)` | Business reviews | 2 |

### Configuration
```python
# In ApifyScraper.__init__
self.client = ApifyClient(settings.APIFY_API_TOKEN)
```

### Checking Availability
```python
if self.apify.is_available:
    # Has valid API token
    data = await self.apify.scrape_tiktok(queries)
```

---

## 3. SocialMediaAnalyzer

**File:** `app/services/social_media_analyzer.py`
**APIs:** yt-dlp (download), Gemini Vision (analysis)

### Video Download
- Uses yt-dlp subprocess
- Max file size: 50MB
- Timeout: 60 seconds
- Output: `output/social_media/{platform}/`

### Video Analysis (Gemini)
- Model: `gemini-2.0-flash`
- Processing timeout: 60s
- Analysis timeout: 60s
- 1 second delay between videos

### Methods

| Method | Purpose |
|--------|---------|
| `download_video(url, platform, id)` | Download via yt-dlp |
| `analyze_video(path, context)` | Analyze with Gemini |
| `analyze_social_content(data, platform, max)` | Batch process |
| `aggregate_social_insights(data)` | Summarize findings |

### Analysis Output
```json
{
  "transcription": "Full spoken text",
  "hook": "First 3 seconds content",
  "hook_type": "question/statement/visual",
  "hook_strength_1to5": 4,
  "content_type": "tutorial/review/trend",
  "pacing": "slow/medium/fast",
  "pain_points_mentioned": ["list"],
  "quotable_phrases": ["list"],
  "customer_language": "Verbatim expressions"
}
```

---

## 4. AdLibraryScraper

**File:** `app/services/adlibrary.py`
**API:** yt-dlp + Gemini Vision

### Ad Types
- Video ads (downloaded with yt-dlp)
- Image ads (downloaded with httpx)

### Methods

| Method | Purpose |
|--------|---------|
| `discover_ad_library_url(brand, website)` | Find ad library page |
| `scrape_ads(url)` | Extract ad data |
| `download_ad_video(url)` | Download video |
| `download_ad_image(url)` | Download image |

### Output Directory
```
output/adlibrary/
├── brand_name/
│   ├── video_001.mp4
│   ├── video_002.mp4
│   └── image_001.jpg
```

---

## 5. AdAnalyzer

**File:** `app/services/adlibrary.py`
**API:** Gemini Vision

### Video Analysis
- Model: `gemini-2.0-flash`
- Upload timeout: 60s
- Analysis timeout: 300s

### Methods

| Method | Purpose |
|--------|---------|
| `analyze_ad_video(path)` | Single video |
| `analyze_ads_batch(ads)` | Batch process |
| `aggregate_patterns(analyzed)` | Find patterns |

### Analysis Output
```json
{
  "transcription": "Full verbatim",
  "hook_text": "First 3 seconds",
  "hook_type": "question/statement",
  "hook_strength_1to5": 5,
  "framework": "PAS/AIDA/BAB",
  "effectiveness_score_1to10": 8,
  "scene_breakdown": [
    {"time": "0:00-0:03", "visual": "...", "audio": "..."}
  ],
  "creative_dimensions": {
    "tonality": "urgent/friendly",
    "style": "ugc/professional"
  }
}
```

---

## Usage Examples

### Track 1 Scraping (Brand)
```python
# Inside orchestrator
brand_queries = queries.get("brand_queries", {})

# Reddit via Firecrawl
reddit_data = await self.firecrawl.search_reddit(brand_name)

# Twitter via Apify
if self.apify.is_available:
    twitter_data = await self.apify.scrape_twitter(
        brand_queries.get("twitter", [brand_name]),
        track=1
    )

# TikTok with video analysis
if self.apify.is_available:
    tiktok_data = await self.apify.scrape_tiktok(queries, track=1)
    analyzed = await self.social_analyzer.analyze_social_content(
        tiktok_data, platform="tiktok", max_videos=5
    )
```

### Track 2 Scraping (Segment)
```python
segment_queries = queries.get("segment_queries", {})

# Subreddit scraping
for subreddit in segment_queries.get("subreddits", []):
    data = await self.firecrawl.scrape_subreddit(subreddit)

# Problem-focused Reddit searches
for query in segment_queries.get("reddit_searches", []):
    data = await self.firecrawl.search_reddit(query)

# Quora questions
for question in segment_queries.get("quora_questions", []):
    # Via Firecrawl search with site:quora.com
```

### Ad Library Processing
```python
ads = await self.adlib_scraper.scrape_ads(ad_library_url)
analyzed = await self.ad_analyzer.analyze_ads_batch(ads)
patterns = self.ad_analyzer.aggregate_patterns(analyzed)
```

---

## Error Handling

All scrapers follow this pattern:
```python
try:
    data = await scraper.method(query)
    print(f"    [Source] Found {len(data)} items")
except Exception as e:
    print(f"    [!] Source error: {str(e)[:60]}")
    data = []
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| 429 Rate Limited | Too many requests | Auto-retry with backoff |
| Timeout | Slow response | Increase timeout |
| No API key | Missing env var | Set env variable |
| Actor failed | Apify actor issue | Check actor status |
| Download failed | Invalid URL | Skip video |
