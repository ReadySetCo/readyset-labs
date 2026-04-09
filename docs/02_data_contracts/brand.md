# Brand Model Contract

> Schema definition for the Brand entity - the central object being researched.

---

## Table: `brands`

**Purpose:** Stores brand identity information including discovered metadata and Brand DNA.

---

## Schema

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | Integer | No | Primary key, auto-increment |
| `name` | String(255) | No | Brand name (indexed) |
| `website_url` | String(500) | Yes | Brand website URL |
| `description` | Text | Yes | LLM-generated brand description |
| `sector` | String(255) | Yes | Industry sector (e.g., "Healthcare") |
| `vertical` | String(255) | Yes | Market vertical (e.g., "Men's Health") |
| `products` | JSON | Yes | List of product names |
| `target_audience` | Text | Yes | Target audience description |

### Brand DNA Fields (Visual Identity)

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `brand_colors` | JSON | Yes | Array of hex colors `["#002432", "#0070c9"]` |
| `tagline` | String(500) | Yes | Brand slogan/tagline |
| `brand_values` | JSON | Yes | Array of values `["Transparency", "Innovation"]` |
| `brand_aesthetic` | JSON | Yes | Array `["modern", "clean", "digital"]` |
| `tone_of_voice` | JSON | Yes | Array `["Empathetic", "Informative"]` |
| `logo_url` | String(1000) | Yes | URL to brand logo image |
| `fonts` | JSON | Yes | Array of font names |
| `brand_images` | JSON | Yes | Array of representative image URLs |
| `social_media_urls` | JSON | Yes | Object with platform URLs |
| `ad_library_page_id` | String(50) | Yes | Facebook Ad Library page ID |
| `product_descriptions` | JSON | Yes | Array of products with descriptions |

### Timestamps

| Field | Type | Description |
|-------|------|-------------|
| `created_at` | DateTime | Record creation time (UTC) |
| `updated_at` | DateTime | Last update time (UTC) |

---

## Relationships

| Relation | Target | Type | Description |
|----------|--------|------|-------------|
| `research_sessions` | ResearchSession | One-to-Many | All research sessions for this brand |

---

## Indexes

| Column | Type |
|--------|------|
| `id` | Primary Key |
| `name` | Index |

---

## Example Record

```json
{
  "id": 42,
  "name": "GoodFood",
  "website_url": "https://www.makegoodfood.ca",
  "description": "Canadian meal kit delivery service...",
  "sector": "Food & Beverage",
  "vertical": "Meal Kit Delivery",
  "products": ["Meal Kits", "Groceries", "Easy Prep Meals"],
  "target_audience": "Busy Canadian families...",
  "brand_colors": ["#53a318", "#ffffff", "#333333"],
  "tagline": "Make Good Food Together",
  "brand_values": ["Quality", "Convenience", "Health"],
  "brand_aesthetic": ["fresh", "family-friendly", "clean"],
  "tone_of_voice": ["Friendly", "Approachable", "Inspiring"],
  "logo_url": "https://example.com/logo.png",
  "fonts": ["Open Sans", "Montserrat"],
  "social_media_urls": {
    "twitter": "https://twitter.com/makegoodfood",
    "instagram": "https://instagram.com/makegoodfood",
    "facebook": "https://facebook.com/makegoodfoodcanada"
  },
  "ad_library_page_id": "645468212198661",
  "product_descriptions": [
    {"name": "Classic Meal Kit", "description": "Pre-portioned ingredients..."}
  ],
  "created_at": "2025-12-15T10:30:00Z",
  "updated_at": "2026-01-08T04:00:00Z"
}
```

---

## Lineage

| Producer | Consumer |
|----------|----------|
| `brand_discovery.py` | ResearchOrchestrator |
| `brand_dna.py` | Frontend BrandDNAView |
| User input (name, URL) | All research phases |

---

## Constraints

- `name` is required and must be non-empty
- `website_url` should be a valid URL with protocol
- JSON fields should be arrays or objects as specified
