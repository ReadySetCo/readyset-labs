# Environment Variables & Secrets

> Complete catalog of environment configuration, secrets management, and external service credentials.

---

## Environment File Location

```
backend/.env
```

**Source of truth:** `backend/app/config.py` (Pydantic Settings)

---

## Required Variables

### LLM Configuration

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `LLM_PROVIDER` | Default LLM provider | `openai` or `gemini` | Yes |
| `OPENAI_API_KEY` | OpenAI API key | `sk-proj-xxxx` | Yes (if using OpenAI) |
| `GEMINI_API_KEY` | Google Gemini API key | `AIzaSy...` | Yes (for video analysis) |
| `OPENAI_MODEL` | OpenAI model to use | `gpt-4o` | No (default: gpt-4o) |
| `GEMINI_MODEL` | Gemini model to use | `gemini-2.0-flash` | No (default) |

### Scraping APIs

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `FIRECRAWL_API_KEY` | Firecrawl web scraping | `fc-xxxxxx` | Yes |
| `FIRECRAWL_BASE_URL` | Firecrawl API base | `https://api.firecrawl.dev/v1` | No (default) |
| `APIFY_API_TOKEN` | Apify cloud scraping | `apify_api_xxxx` | Yes |

### Database

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | SQLite connection string | `sqlite+aiosqlite:///./database.db` | No (default) |

### RAG Integration

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `ANYTHINGLLM_API_KEY` | AnythingLLM API | `xxx-xxxxxx-xxxxxxx-xxxxxx` | Optional |

### Optional Credentials

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `FB_EMAIL` | Facebook login email | `user@example.com` | Optional |
| `FB_PASSWORD` | Facebook login password | `password` | Optional |
| `INSTAGRAM_USERNAME` | Instagram username | `brand_account` | Optional |
| `INSTAGRAM_PASSWORD` | Instagram password | `password` | Optional |

---

## Application Settings

| Variable | Description | Default | Notes |
|----------|-------------|---------|-------|
| `APP_NAME` | Application name | `Brand Intelligence Scraper` | Display only |
| `DEBUG` | Debug mode | `True` | Enables verbose logging |
| `MAX_POSTS_PER_SOURCE` | Max items per scrape source | `100` | Limits data volume |
| `MAX_REVIEWS_PER_SOURCE` | Max reviews per source | `100` | Cost control |
| `SCRAPE_TIMEOUT` | Request timeout (seconds) | `20` | Prevents hanging |

---

## Example `.env` File

```env
# LLM Configuration
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE
GEMINI_API_KEY=AIzaSyYOUR_KEY_HERE

# Scraping APIs  
FIRECRAWL_API_KEY=fc-YOUR_KEY_HERE
APIFY_API_TOKEN=apify_api_YOUR_KEY_HERE

# Database
DATABASE_URL=sqlite+aiosqlite:///./database.db

# Limits
MAX_POSTS_PER_SOURCE=50
MAX_REVIEWS_PER_SOURCE=100

# RAG (optional)
ANYTHINGLLM_API_KEY=YOUR_KEY_HERE

# Facebook (optional - for cookie refresh)
FB_EMAIL=your@email.com
FB_PASSWORD=yourpassword
```

---

## Secret Injection Methods

### Local Development
- `.env` file in `backend/` directory
- Automatically loaded by Pydantic Settings

### Docker Deployment
- Environment variables in `docker-compose.yml`
- Or mounted `.env` file

### Production
- Environment variables set in hosting platform
- Never commit `.env` to version control

---

## Secret Rotation

### API Keys
| Service | Rotation Frequency | Notes |
|---------|-------------------|-------|
| OpenAI | As needed | Service account keys |
| Gemini | As needed | Google Cloud credentials |
| Firecrawl | As needed | Subscription-based |
| Apify | As needed | Token in dashboard |

### Credentials
| Credential | Rotation | Notes |
|------------|----------|-------|
| Facebook cookies | Every 2-4 weeks | Auto-refresh script available |
| Instagram session | Monthly | Instaloader session file |

---

## Service Credentials Reference

### OpenAI
- **Dashboard:** https://platform.openai.com/api-keys
- **Key format:** `sk-proj-...` or `sk-svcacct-...`
- **Used by:** LLM client, insights, generators

### Google Gemini
- **Dashboard:** https://aistudio.google.com/apikey
- **Key format:** `AIzaSy...`
- **Used by:** Video analysis, vision tasks

### Firecrawl
- **Dashboard:** https://www.firecrawl.dev/app/api-keys
- **Key format:** `fc-...`
- **Used by:** Web scraping, Reddit, Trustpilot

### Apify
- **Dashboard:** https://console.apify.com/account/integrations
- **Key format:** `apify_api_...`
- **Used by:** Twitter, TikTok, Instagram, Facebook scraping

### AnythingLLM
- **Dashboard:** http://localhost:3001/settings/api-keys
- **Key format:** `XXX-XXXXXXX-XXXXXXX-XXXXXXX`
- **Used by:** RAG chat, document embedding

---

## Validation

To verify all required environment variables are set:

```python
from app.config import settings

# Check required keys
assert settings.OPENAI_API_KEY, "OPENAI_API_KEY not set"
assert settings.FIRECRAWL_API_KEY, "FIRECRAWL_API_KEY not set"
assert settings.APIFY_API_TOKEN, "APIFY_API_TOKEN not set"
assert settings.GEMINI_API_KEY, "GEMINI_API_KEY not set"
```

Or use the diagnostic script:

```powershell
python diagnose_apis.py
```

---

## Security Notes

> [!CAUTION]
> Never commit `.env` files or API keys to version control.

- `.env` is listed in `.gitignore`
- Use environment variables in CI/CD pipelines
- Rotate keys immediately if exposed
- Use service accounts instead of personal API keys when available
