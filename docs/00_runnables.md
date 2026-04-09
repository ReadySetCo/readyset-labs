# Runnables Registry

> Complete list of all executable entry points, CLI commands, API endpoints, and background tasks.

---

## Startup Scripts

### `start_all.bat` - Full Stack Startup
**Location:** Project root

Starts all services in sequence:
1. Docker Desktop (if not running)
2. AnythingLLM container (port 3001)
3. Backend API (port 8000)
4. Frontend dev server (port 5173)

```batch
# Usage
start_all.bat
```

**Side effects:** Opens 2 terminal windows, starts Docker container

---

### `start_servers.bat` - Backend + Frontend Only
**Location:** Project root

Starts backend and frontend without Docker/AnythingLLM:
1. Kills existing processes on ports 8000 and 5173
2. Starts backend with uvicorn
3. Starts frontend with Vite

```batch
# Usage
start_servers.bat
```

**Side effects:** Kills existing processes, opens 2 terminal windows

---

## Backend Startup

### Uvicorn Server
**Location:** `backend/`

```powershell
# Activate virtual environment
cd C:\Users\Lauta\Documents\SCRAPPER\backend
.\venv\Scripts\activate

# Start with hot reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Environment required:** `.env` file with API keys
**Port:** 8000
**Health check:** `GET /health`

---

## Frontend Startup

### Vite Dev Server
**Location:** `frontend/`

```powershell
cd C:\Users\Lauta\Documents\SCRAPPER\frontend
npm run dev
```

**Port:** 5173
**Endpoints:**
- `/` - Dashboard (brand list)
- `/research/{id}` - Research progress
- `/results/{id}` - Results view

---

## Docker Services

### `docker-compose.yml`

```yaml
# AnythingLLM RAG service
docker-compose up -d anythingllm
```

**Services:**
| Service | Port | Purpose |
|---------|------|---------|
| anythingllm | 3001 | RAG vector store and chat |

---

## API Endpoints

### Brand Endpoints (`/api/brands/`)

| Method | Endpoint | Purpose | Request Body |
|--------|----------|---------|--------------|
| `POST` | `/api/brands/` | Create brand | `{ "name": "...", "website_url": "..." }` |
| `GET` | `/api/brands/` | List all brands | - |
| `GET` | `/api/brands/{id}` | Get brand by ID | - |
| `DELETE` | `/api/brands/{id}` | Delete brand | - |

---

### Research Endpoints (`/api/research/`)

| Method | Endpoint | Purpose | Notes |
|--------|----------|---------|-------|
| `POST` | `/api/research/start` | Start research | `{ "brand_id": int }` |
| `GET` | `/api/research/session/{id}` | Get session status | - |
| `GET` | `/api/research/session/{id}/progress` | Get detailed progress | - |
| `GET` | `/api/research/session/{id}/data` | Get scraped data | Query: `source_type`, `track`, `limit` |
| `GET` | `/api/research/session/{id}/insights` | Get insights | - |
| `GET` | `/api/research/session/{id}/full` | Get complete results | Brand + Data + Insights |
| `POST` | `/api/research/session/{id}/reprocess` | Reprocess insights | Uses existing data |
| `POST` | `/api/research/session/{id}/incremental` | Incremental analysis | Adds missing sources |
| `POST` | `/api/research/session/{id}/adlibrary` | Scrape Ad Library | - |
| `POST` | `/api/research/session/{id}/scripts/more` | Generate more scripts | Query: `count` |
| `GET` | `/api/research/sessions` | List all sessions | Query: `limit` |
| `GET` | `/api/research/brand/{brand_id}/sessions` | List brand sessions | - |
| `GET` | `/api/research/session/{id}/logs` | Get session logs | Query: `since`, `limit` |
| `GET` | `/api/research/queue-status` | Get queue status | - |
| `GET` | `/api/research/metrics` | Get API metrics | - |

---

### Chat Endpoints (`/api/chat/`)

| Method | Endpoint | Purpose | Notes |
|--------|----------|---------|-------|
| `POST` | `/api/chat/` | Send chat message | `{ "message": "...", "session_id": int }` |
| `POST` | `/api/chat/simple` | Simple chat (no RAG) | - |
| `GET` | `/api/chat/workspaces` | List AnythingLLM workspaces | - |
| `POST` | `/api/chat/sync/{session_id}` | Sync session to AnythingLLM | - |

---

### Media Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/research/video/{session_id}/{filename}` | Serve downloaded video |
| `GET` | `/api/research/image/{session_id}/{filename}` | Serve downloaded image |

---

## Background Tasks

These are triggered by API endpoints and run asynchronously:

| Task | Trigger | Function |
|------|---------|----------|
| Full Research Pipeline | `POST /research/start` | `run_research_pipeline()` |
| Reprocess Insights | `POST /research/session/{id}/reprocess` | `run_reprocess_pipeline()` |
| Incremental Analysis | `POST /research/session/{id}/incremental` | `run_incremental_pipeline()` |
| Ad Library Scrape | `POST /research/session/{id}/adlibrary` | `run_ad_library_pipeline()` |

**Concurrency control:** `MAX_CONCURRENT_ANALYSES = 3`

---

## Utility Scripts

### Database Management

| Script | Purpose | Usage |
|--------|---------|-------|
| `migrate_*.py` | Database migrations | `python migrate_add_video_columns.py` |
| `find_db.py` | Find database files | `python find_db.py` |
| `check_sessions.py` | List sessions | `python check_sessions.py` |

### Debugging

| Script | Purpose | Usage |
|--------|---------|-------|
| `debug_adlib_pipeline.py` | Debug Ad Library | `python debug_adlib_pipeline.py` |
| `debug_analyzers.py` | Debug analyzers | `python debug_analyzers.py` |
| `debug_firecrawl.py` | Debug Firecrawl | `python debug_firecrawl.py` |
| `diagnose_apis.py` | Check all APIs | `python diagnose_apis.py` |

### Testing

| Script | Purpose |
|--------|---------|
| `test_full_research.py` | End-to-end test |
| `test_phase*.py` | Phase-specific tests |
| `test_adlib_*.py` | Ad Library tests |
| `test_apify_*.py` | Apify tests |
| `test_generators.py` | Generator tests |

### Export/Sync

| Script | Purpose |
|--------|---------|
| `export_knowledge.py` | Export knowledge base |
| `sync_anythingllm.py` | Sync to AnythingLLM |
| `index_rag.py` | Index RAG documents |

---

## Environment Configuration

Required for all runnables:

```
backend/.env required keys:
- LLM_PROVIDER
- OPENAI_API_KEY
- FIRECRAWL_API_KEY
- APIFY_API_TOKEN
- GEMINI_API_KEY
- DATABASE_URL
- ANYTHINGLLM_API_KEY (optional)
```

See `00_env_and_secrets.md` for complete environment documentation.
