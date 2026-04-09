# ScrapedData Model Contract

> Schema definition for raw scraped data from all sources.

---

## Table: `scraped_data`

**Purpose:** Stores all scraped content from 15+ platforms with classification and analysis metadata.

---

## Schema

### Core Fields

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | Integer | No | Primary key |
| `session_id` | Integer | No | FK → research_sessions.id |
| `source_type` | String(50) | No | Platform identifier |
| `source_url` | String(1000) | Yes | Original URL |
| `track` | Integer | No | 1=Brand mentions, 2=Segment |

### Content

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `title` | Text | Yes | Post/article title |
| `content` | Text | Yes | Full text content |
| `author` | String(255) | Yes | Author username |
| `posted_at` | DateTime | Yes | Original post date |

### Metrics

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `likes` | Integer | Yes | Like/upvote count |
| `comments_count` | Integer | Yes | Comment count |
| `shares` | Integer | Yes | Share/repost count |
| `rating` | Float | Yes | Review rating (1-5) |

### Classification

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `mention_type` | String(50) | Yes | See values below |
| `sentiment` | String(20) | Yes | positive/negative/neutral |
| `sentiment_score` | Float | Yes | -1.0 to 1.0 |
| `relevance_score` | Float | Yes | 0.0 to 1.0 |
| `detected_topics` | JSON | Yes | Array of topic tags |

### Video Analysis

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `video_analysis` | JSON | Yes | Gemini analysis results |
| `video_file` | String(500) | Yes | Path to downloaded video |

### Intake Engine Fields

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `primary_trigger` | String(255) | Yes | Why they start searching |
| `blocker_type` | String(50) | Yes | friction/objection/none |
| `desired_outcome_level` | String(50) | Yes | functional/emotional/identity |
| `proof_type_trusted` | String(100) | Yes | What evidence they trust |
| `language` | String(10) | Yes | Content language (en, es) |
| `validation_level` | Integer | No | 1-5, default 1 |
| `classification_confidence` | Float | Yes | 0.0 to 1.0 |
| `language_cues` | JSON | Yes | Repeated phrases, slang |

### Storage

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `raw_data` | JSON | Yes | Original API response |
| `scraped_at` | DateTime | No | When scraped (UTC) |

---

## Enum Values

### `source_type`
```
reddit, twitter, tiktok, instagram, facebook,
amazon, google, trustpilot, forum, website,
news_blog, competitor_comparison, quora, medium,
linkedin, youtube, adlibrary
```

### `mention_type`
```
direct_brand        - Explicit brand mention
segment_discussion  - Industry/category discussion
competitor_mention  - Competitor comparison
problem_discussion  - Pain point discussion
```

### `blocker_type`
```
friction   - "Can't" barriers (access, price, complexity)
objection  - "Won't" barriers (trust, skepticism)
none       - No blockers detected
```

### `desired_outcome_level`
```
functional  - "I want to solve X"
emotional   - "I want to feel X"
identity    - "I want to be X"
```

---

## Indexes

| Column | Type |
|--------|------|
| `id` | Primary Key |
| `session_id` | Foreign Key |
| `source_type` | Index (recommended) |

---

## Video Analysis Schema

```json
{
  "transcription": "Full spoken text from video",
  "hook": "First 3 seconds content",
  "hook_type": "question|statement|visual|shock",
  "hook_strength_1to5": 4,
  "content_type": "tutorial|review|trend|ugc|ad",
  "pacing": "slow|medium|fast",
  "pain_points_mentioned": ["string array"],
  "quotable_phrases": ["string array"],
  "customer_language": "Verbatim expressions used"
}
```

---

## Example Record

```json
{
  "id": 12345,
  "session_id": 77,
  "source_type": "reddit",
  "source_url": "https://reddit.com/r/mealprep/comments/xyz",
  "track": 1,
  "title": "GoodFood review after 3 months",
  "content": "I've been using GoodFood for 3 months now...",
  "author": "u/healthyuser123",
  "posted_at": "2025-12-01T15:30:00Z",
  "likes": 47,
  "comments_count": 12,
  "shares": null,
  "rating": null,
  "mention_type": "direct_brand",
  "sentiment": "positive",
  "sentiment_score": 0.72,
  "relevance_score": 0.89,
  "detected_topics": ["quality", "value", "convenience"],
  "video_analysis": null,
  "video_file": null,
  "primary_trigger": "busy lifestyle",
  "blocker_type": "none",
  "desired_outcome_level": "functional",
  "proof_type_trusted": "reviews_ugc",
  "language": "en",
  "validation_level": 1,
  "classification_confidence": 0.85,
  "language_cues": ["honestly", "game changer", "worth every penny"],
  "raw_data": {"original": "api response"},
  "scraped_at": "2026-01-08T04:05:00Z"
}
```

---

## Lineage

| Producer | Consumer |
|----------|----------|
| Firecrawl scraper | Processors |
| Apify scraper | Processors |
| Ad Library scraper | AdLibrary Processor |
| Processors | Insights engine |
| Processors | Cross-source analyzer |
| All | RAG indexing |
