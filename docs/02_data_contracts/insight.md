# Insight Model Contract

> Schema for generated insights, creative dimensions, and generated content.

---

## Table: `insights`

**Purpose:** Stores all AI-generated analysis results from a research session.

---

## Schema

### Core

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | Integer | No | Primary key |
| `session_id` | Integer | No | FK → research_sessions.id |
| `created_at` | DateTime | No | Creation timestamp (UTC) |

### Brand Summary

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `brand_summary` | Text | Yes | Overall brand perception |
| `sentiment_score` | Float | Yes | -1.0 to 1.0 aggregate |
| `total_mentions` | Integer | Yes | Total scraped items |

### Track 1: Brand Insights

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `top_positives` | JSON | Yes | Array of positive themes |
| `top_negatives` | JSON | Yes | Array of negative themes |
| `competitors_mentioned` | JSON | Yes | Competitors found |

### Track 2: Market Insights

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `market_pain_points` | JSON | Yes | Industry pain points |
| `customer_language` | JSON | Yes | Verbatim phrases |
| `customer_desires` | JSON | Yes | What customers want |
| `trending_topics` | JSON | Yes | Trending themes |

### Creative Dimensions

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `icps` | JSON | Yes | Ideal Customer Profiles |
| `pain_points` | JSON | Yes | Customer pain points |
| `value_props` | JSON | Yes | Value propositions |
| `messaging_angles` | JSON | Yes | Ad messaging angles |
| `tone_emotions` | JSON | Yes | Emotional themes |
| `content_insights` | JSON | Yes | From video analysis |

### Enhanced Insights

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `competitor_analysis` | JSON | Yes | Detailed comparison |
| `purchase_triggers` | JSON | Yes | What drives purchase |
| `objections` | JSON | Yes | Common objections |
| `decision_factors` | JSON | Yes | Key decision factors |
| `verbatim_quotes` | JSON | Yes | Real quotes for ads |
| `content_opportunities` | JSON | Yes | Content gaps |
| `recommended_hooks` | JSON | Yes | Suggested ad hooks |
| `price_sensitivity` | JSON | Yes | Price insights |
| `feature_requests` | JSON | Yes | Requested features |

### Ad Intelligence

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `ad_library_data` | JSON | Yes | Brand's ads data |
| `competitor_ads_data` | JSON | Yes | Competitor ads |
| `ad_creative_patterns` | JSON | Yes | Aggregated patterns |
| `landing_page_analysis` | JSON | Yes | LP analysis |

### Generated Content

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `generated_scripts` | JSON | Yes | AI ad scripts |
| `thumbnail_suggestions` | JSON | Yes | First frame ideas |
| `ab_test_suggestions` | JSON | Yes | Test recommendations |

### Competitive Intelligence

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `competitor_profiles` | JSON | Yes | Competitor details |
| `competitive_matrix` | JSON | Yes | Comparison matrix |
| `swot_analysis` | JSON | Yes | SWOT analysis |

### Data Summary

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `data_summary` | JSON | Yes | Stats by source |
| `top_quotes` | JSON | Yes | Best quotes |
| `data_by_topic` | JSON | Yes | Topic categorization |
| `cross_source_insights` | JSON | Yes | Cross-source patterns |

### Proto-ICPs

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `proto_icps` | JSON | Yes | Clustered ICP candidates |
| `proto_icp_recommendations` | JSON | Yes | Top 3 recommended |
| `proto_icp_stats` | JSON | Yes | Summary stats |

### Report

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `full_report` | Text | Yes | Markdown report |

---

## JSON Schema Examples

### `icps` (Ideal Customer Profiles)
```json
[
  {
    "name": "Busy Professional Parent",
    "description": "Working parents who...",
    "demographics": "30-45, dual income",
    "pain_points": ["no time to cook", "kids are picky"],
    "motivations": ["healthy family meals"],
    "objections": ["too expensive"]
  }
]
```

### `generated_scripts`
```json
[
  {
    "title": "The 6PM Panic",
    "hook": "It's 6PM. The kids are hungry. You have nothing planned.",
    "framework": "PAS",
    "scenes": [
      {"time": "0:00-0:03", "visual": "Clock showing 6PM", "audio": "..."}
    ],
    "cta": "Get 50% off your first box"
  }
]
```

### `ad_creative_patterns`
```json
{
  "common_hooks": ["Did you know...", "Stop scrolling if..."],
  "dominant_frameworks": ["PAS", "AIDA"],
  "avg_duration_seconds": 28,
  "style_breakdown": {"ugc": 60, "professional": 40},
  "cta_patterns": ["Shop now", "Try risk-free"]
}
```

---

## Example Record (Abbreviated)

```json
{
  "id": 77,
  "session_id": 77,
  "brand_summary": "GoodFood is perceived as...",
  "sentiment_score": 0.65,
  "total_mentions": 347,
  "icps": [...],
  "pain_points": [...],
  "generated_scripts": [...],
  "full_report": "# Brand Intelligence Report\n\n...",
  "created_at": "2026-01-08T04:15:00Z"
}
```

---

## Lineage

| Producer | Consumer |
|----------|----------|
| `insights.py` | Frontend InsightsView |
| `generators/scripts.py` | Frontend GeneratedContentView |
| `competitors/analyzer.py` | Frontend CompetitorView |
| All generators | RAG chat context |
