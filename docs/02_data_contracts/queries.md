# Query Schemas Contract

> Schema for generated search queries used by scrapers.

---

## GeneratedQueries

**Purpose:** Contains platform-specific search queries for Track 1 (brand) and Track 2 (segment) scraping.

**Producer:** `keyword_generator.py`
**Consumers:** All scrapers

---

## Schema

```typescript
interface GeneratedQueries {
  brand_queries: BrandQueries;
  segment_queries: SegmentQueries;
}
```

---

## Brand Queries (Track 1)

```json
{
  "reddit": ["brand review", "brand worth it", "brand vs competitor"],
  "twitter": ["@brand_handle", "#brand", "brand experience"],
  "tiktok": ["#brandreview", "#brand", "@brand_official"],
  "instagram": ["#brand", "#brandcommunity"],
  "trustpilot": ["brand_name"],
  "news": ["brand news", "brand announcement"],
  "youtube": ["brand review", "brand unboxing"]
}
```

---

## Segment Queries (Track 2)

```json
{
  "subreddits": ["r/fitness", "r/nutrition", "r/mealprep"],
  "reddit_searches": ["best meal kit", "healthy meal prep", "cooking alternatives"],
  "quora_questions": ["What is the best meal kit service", "Is meal kit delivery worth it"],
  "tiktok_hashtags": ["#mealprep", "#healthyeating", "#cookinghacks"],
  "instagram_hashtags": ["#mealprepsunday", "#healthyrecipes"],
  "twitter_hashtags": ["#mealkit", "#healthyfood"],
  "forums": ["bodybuilding.com", "myfitnesspal community"]
}
```

---

## Generation Rules

| Platform | Query Strategy |
|----------|----------------|
| Reddit | Brand name + modifiers ("review", "vs", "worth it") |
| Twitter | Handle @, hashtag #, pain phrases |
| TikTok | Trending hashtags, brand handle |
| Instagram | Brand hashtag, lifestyle hashtags |
| Trustpilot | Exact brand name |
| Subreddits | Real community names only |
| Quora | Question format only |

---

## Example Generated Queries

For brand "GoodFood" in sector "Meal Kit Delivery":

```json
{
  "brand_queries": {
    "reddit": ["goodfood review", "makegoodfood worth it", "goodfood vs hellofresh"],
    "twitter": ["@makegoodfood", "#goodfood", "goodfood delivery"],
    "tiktok": ["#goodfoodreview", "#makegoodfood"],
    "instagram": ["#goodfood", "#makegoodfood"],
    "trustpilot": ["goodfood", "makegoodfood"]
  },
  "segment_queries": {
    "subreddits": ["r/MealPrepSunday", "r/EatCheapAndHealthy", "r/Cooking"],
    "reddit_searches": ["best meal kit canada", "meal kit worth it", "healthy meal delivery"],
    "quora_questions": ["Is meal kit delivery worth the cost", "Which meal kit service has best variety"],
    "tiktok_hashtags": ["#mealkit", "#mealprep", "#weeknightdinners"]
  }
}
```
