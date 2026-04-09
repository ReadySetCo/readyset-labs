# Brand Intelligence Scraper - Handoff Guide

> Complete package for running brand intelligence research and scraping.

---

## What This Does

A web scraping and AI analysis tool that discovers:
- **Customer Insights** from Reddit, Twitter/X, TikTok, Instagram
- **Product Reviews** from Amazon, Trustpilot, Google Reviews
- **Ad Intelligence** from Meta Ad Library
- **Creative Dimensions**: ICPs, pain points, value props, messaging angles

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.10+ |
| Node.js | 18+ |
| Docker Desktop | Latest (optional, for RAG) |

### API Keys Required

| Service | Purpose | Get Here |
|---------|---------|----------|
| OpenAI | LLM analysis | https://platform.openai.com/api-keys |
| Gemini | Video analysis | https://aistudio.google.com/apikey |
| Firecrawl | Web scraping | https://www.firecrawl.dev/app/api-keys |
| Apify | Social scraping | https://console.apify.com/account/integrations |

---

## Quick Setup (10 minutes)

### 1. Backend Setup

```powershell
cd backend

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (for some scrapers)
playwright install chromium
```

### 2. Configure Environment

```powershell
# Copy template
copy .env.example .env

# Edit with your API keys
notepad .env
```

**Required in .env:**
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-YOUR_KEY
GEMINI_API_KEY=AIzaSy-YOUR_KEY
FIRECRAWL_API_KEY=fc-YOUR_KEY
APIFY_API_TOKEN=apify_api_YOUR_TOKEN
```

### 3. Frontend Setup

```powershell
cd frontend
npm install
```

### 4. Start Application

```powershell
# From project root
.\start_servers.bat
```

Or manually:
```powershell
# Terminal 1 - Backend
cd backend
.\venv\Scripts\activate
uvicorn app.main:app --reload --port 8000

# Terminal 2 - Frontend
cd frontend
npm run dev
```

### 5. Access

- **Frontend**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs

---

## Usage

1. Open http://localhost:5173
2. Enter brand name (e.g., "Allbirds") and website URL
3. Click **Start Research**
4. Wait 5-15 minutes for scraping + analysis
5. View results in tabs: Overview, Insights, Scripts, Ads

---

## Directory Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI entry point
│   │   ├── routers/         # API endpoints
│   │   ├── services/        # Core logic
│   │   │   ├── scrapers/    # Firecrawl, Apify integrations
│   │   │   ├── adlibrary/   # Ad Library scraper
│   │   │   ├── generators/  # Script/content generators
│   │   │   └── research_orchestrator.py  # Main pipeline
│   │   └── models.py        # Database models
│   └── requirements.txt
│
├── frontend/
│   └── src/                 # React components
│
├── docs/                    # Detailed documentation
│   ├── 00_env_and_secrets.md
│   ├── 01_architecture.md
│   ├── 10_runbook.md        # Operations guide
│   └── ...
│
└── SCRAPERS_REFERENCE.md    # All scrapers documented
```

---

## Documentation Map

| File | Purpose |
|------|---------|
| `docs/00_env_and_secrets.md` | All environment variables |
| `docs/01_architecture.md` | System design |
| `docs/10_runbook.md` | Operations & troubleshooting |
| `SCRAPERS_REFERENCE.md` | Scraper details & API limits |
| `ARCHITECTURE.md` | High-level overview |
| `CORE_PRINCIPLES.md` | Development guidelines |

---

## Troubleshooting

### Backend won't start
```powershell
# Check Python version
python --version  # Need 3.10+

# Verify dependencies
pip install -r requirements.txt --force-reinstall
```

### API errors
```powershell
# Test all APIs
python diagnose_apis.py
```

### No data returned
- Check terminal for scraper errors
- Verify API keys in `.env`
- See `docs/09_failure_atlas.md` for common issues

### Port already in use
```powershell
# Kill process on port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

---

## Costs

| Service | Approx Cost per Research |
|---------|-------------------------|
| OpenAI | $0.05-0.20 |
| Gemini | Free tier often sufficient |
| Firecrawl | ~$0.01-0.05 per source |
| Apify | ~$0.10-0.50 per platform |

**Tip:** Reduce costs by lowering `MAX_POSTS_PER_SOURCE` in `backend/app/config.py`

---

## Support

- Check `docs/` folder for detailed guides
- Review `docs/10_runbook.md` for operations
- See `docs/09_failure_atlas.md` for error solutions

---

*Package created: January 2026*
