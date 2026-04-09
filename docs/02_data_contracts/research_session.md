# ResearchSession Model Contract

> Schema definition for research sessions - tracks pipeline execution state.

---

## Table: `research_sessions`

**Purpose:** Tracks the state and configuration of a research pipeline run.

---

## Schema

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | Integer | No | Primary key, auto-increment |
| `brand_id` | Integer | No | Foreign key to `brands.id` |
| `status` | String(50) | No | Pipeline status |
| `started_at` | DateTime | No | When pipeline started (UTC) |
| `completed_at` | DateTime | Yes | When pipeline completed (UTC) |
| `brand_queries` | JSON | Yes | Track 1 search queries |
| `segment_queries` | JSON | Yes | Track 2 search queries |

---

## Status Values

| Status | Description |
|--------|-------------|
| `pending` | Created but not yet started |
| `in_progress` | Pipeline is running |
| `completed` | Pipeline finished successfully |
| `failed` | Pipeline encountered fatal error |
| `cancelled` | User cancelled the session |

---

## Relationships

| Relation | Target | Type | Description |
|----------|--------|------|-------------|
| `brand` | Brand | Many-to-One | The brand being researched |
| `scraped_data` | ScrapedData | One-to-Many | All data scraped in this session |
| `insights` | Insight | One-to-Many | Generated insights (usually 1) |

---

## Indexes

| Column | Type |
|--------|------|
| `id` | Primary Key |
| `brand_id` | Foreign Key |

---

## Query Structure

### `brand_queries` (Track 1)

```json
{
  "reddit": ["brand_name review", "brand_name worth it"],
  "twitter": ["@brand_handle", "#brandname"],
  "tiktok": ["#brandreview", "#brand"],
  "instagram": ["#brand", "#brandlife"],
  "trustpilot": ["brand_name"]
}
```

### `segment_queries` (Track 2)

```json
{
  "subreddits": ["r/fitness", "r/nutrition"],
  "reddit_searches": ["protein shake alternatives", "meal prep tips"],
  "quora_questions": ["What is the best meal kit service"],
  "tiktok_hashtags": ["#mealprep", "#healthyeating"],
  "forums": ["bodybuilding.com", "myfitnesspal"]
}
```

---

## Example Record

```json
{
  "id": 77,
  "brand_id": 42,
  "status": "completed",
  "started_at": "2026-01-08T04:00:00Z",
  "completed_at": "2026-01-08T04:15:00Z",
  "brand_queries": {
    "reddit": ["goodfood review", "makegoodfood worth it"],
    "trustpilot": ["goodfood"]
  },
  "segment_queries": {
    "subreddits": ["r/MealPrepSunday", "r/EatCheapAndHealthy"],
    "reddit_searches": ["meal kit delivery canada"]
  }
}
```

---

## Lineage

| Producer | Consumer |
|----------|----------|
| `POST /api/research/start` | ResearchOrchestrator |
| `keyword_generator.py` | Scrapers |
| ResearchOrchestrator | Frontend Research.tsx |

---

## Constraints

- `brand_id` must reference existing brand
- `status` must be one of defined values
- `started_at` is set automatically on creation
