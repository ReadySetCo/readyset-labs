# Contributing to Brand Intelligence Scraper

Thank you for considering contributing! This document outlines the development workflow and guidelines.

## Development Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- Git

### Initial Setup

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/brand-intelligence-scraper.git
cd brand-intelligence-scraper

# Backend
cd backend
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
playwright install chromium
cp .env.example .env  # Fill in your API keys

# Frontend
cd ../frontend
npm install
```

### Running in Development

```bash
# Terminal 1 — Backend
cd backend && .\venv\Scripts\activate
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm run dev
```

The backend runs on http://localhost:8000, frontend on http://localhost:5173.

---

## Code Style

### Backend (Python)

- **Type hints** on all function signatures
- **`async/await`** for all I/O operations
- **Wrap external API calls** in `try/except` — never let a scraper crash the pipeline
- **Use the `LLMClient` abstraction** (`services/llm/client.py`) — never call OpenAI/Gemini directly
- **Log via** `self._log()` in the orchestrator or `add_session_log()` in services
- **Pydantic** schemas for all API request/response types

### Frontend (TypeScript/React)

- Functional components only (no class components except ErrorBoundary)
- Use **TanStack React Query** for server state management
- Use **TailwindCSS** for styling
- Export TypeScript interfaces for all API response types in `api/client.ts`
- Keep components focused — one component per view/tab

---

## Git Workflow

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes
3. Test locally (both backend and frontend)
4. Commit with descriptive messages
5. Push and create a Pull Request against `main`

### Commit Convention

```
feat: Add TikTok segment analysis
fix: Handle timeout in Gemini LLM client
docs: Update API reference
refactor: Split orchestrator into phase modules
chore: Update dependencies
```

---

## Architecture Notes

### Research Pipeline

All research logic flows through `ResearchOrchestrator.run_full_research()` in a 6-phase pipeline:

1. **Phase 1** — Brand DNA + Discovery (parallel)
2. **Phase 2** — Query Generation
3. **Phase 3** — Track 1 + Track 2 Scraping (parallel)
4. **Phase 4** — Ad Library Analysis (started in Phase 1, awaited here)
5. **Phase 5** — Competitor Analysis
6. **Phase 6** — Insight Generation + Content Generation

### Key Principles

- **Dual-track scraping:** Track 1 = brand mentions, Track 2 = market segment
- **Graceful degradation:** Individual scraper failures never crash the pipeline
- **Background tasks:** Long-running research uses FastAPI's `BackgroundTasks`
- **Concurrency control:** Semaphore limits concurrent analyses to 3

### Adding a New Scraper

1. Create a new method in the orchestrator or a new service in `services/`
2. Wrap it in `try/except` that returns empty data on failure
3. Add the source type to `SourceType` enum in `schemas.py`
4. Save results as `ScrapedData` records with the correct `track` value
5. The `InsightsGeneratorService` will automatically include the new data

---

## Reporting Issues

- Use GitHub Issues with descriptive titles
- Include:
  - Steps to reproduce
  - Expected vs actual behavior
  - Backend error logs (from terminal or `/api/research/session/{id}/logs`)
  - Brand name and which source failed (for scraping issues)
- Use the bug report template when available

---

## Security

See [SECURITY.md](SECURITY.md) for vulnerability reporting guidelines.

**Never commit API keys** — Always use `.env` files (excluded via `.gitignore`).
