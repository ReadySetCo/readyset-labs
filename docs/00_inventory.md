# System Inventory - Repository Map

> Complete catalog of all components, files, and their roles in the Brand Intelligence Scraper system.

---

## Repository Structure Overview

```
SCRAPPER/
├── backend/                    # Python FastAPI backend
│   ├── app/                    # Main application code
│   │   ├── routers/            # API endpoints
│   │   ├── services/           # Business logic
│   │   │   ├── scrapers/       # Data collection
│   │   │   ├── processors/     # Data normalization
│   │   │   ├── generators/     # Content generation
│   │   │   ├── adlibrary/      # Ad Library scraping
│   │   │   ├── competitors/    # Competitor analysis
│   │   │   ├── landing_pages/  # Landing page analysis
│   │   │   ├── llm/            # LLM client & prompts
│   │   │   └── rag/            # RAG embeddings & vector store
│   │   └── utils/              # Utility functions
│   ├── logs/                   # Session log files
│   ├── output/                 # Downloaded media (videos/images)
│   ├── knowledge_base/         # Exported knowledge documents
│   ├── knowledge_base_rag/     # RAG-processed knowledge
│   └── vector_db/              # Vector database files
├── frontend/                   # React TypeScript frontend
│   └── src/
│       ├── pages/              # Main views
│       ├── components/         # Reusable components
│       └── api/                # API client
├── docs/                       # Documentation (this folder)
└── *.md                        # Root documentation files
```

---

## Backend Application (`backend/app/`)

### Core Files

| File | Lines | Role |
|------|-------|------|
| `main.py` | ~50 | FastAPI app initialization, CORS, routers |
| `config.py` | ~60 | Settings from environment (API keys, limits) |
| `database.py` | ~40 | SQLAlchemy async session factory |
| `models.py` | ~213 | SQLAlchemy ORM models (Brand, Session, Data, Insight) |
| `schemas.py` | ~348 | Pydantic request/response schemas |

### Routers (`routers/`)

| File | Role | Key Endpoints |
|------|------|---------------|
| `brands.py` | Brand CRUD | `POST /api/brands/`, `GET /api/brands/` |
| `research.py` | Research pipeline | `POST /api/research/start`, `GET /api/research/session/{id}/full` |
| `chat.py` | Chat/RAG interface | `POST /api/chat/`, WebSocket support |

### Services - Core (`services/`)

| File | Lines | Role |
|------|-------|------|
| `research_orchestrator.py` | 3,489 | **Main pipeline coordinator** - orchestrates all 7 phases |
| `brand_discovery.py` | ~120 | Extracts sector, vertical, products from website |
| `brand_dna.py` | ~1,400 | Extracts brand identity (colors, values, tone) |
| `brand_extractor.py` | ~450 | Deep brand analysis with LLM |
| `keyword_generator.py` | ~200 | Generates search queries for Track 1 & 2 |
| `insights.py` | ~450 | Generates creative dimensions (ICPs, pain points) |
| `knowledge_synthesizer.py` | ~1,000 | Synthesizes knowledge from multiple sources |
| `chatbot.py` | ~300 | Chat response generation |
| `anythingllm.py` | ~350 | AnythingLLM API integration |

### Services - Scrapers (`services/scrapers/`)

| File | Lines | Role |
|------|-------|------|
| `firecrawl.py` | ~1,200 | Web scraping via Firecrawl API (Reddit, Trustpilot, News) |
| `apify.py` | ~1,200 | Social media scraping (Twitter, TikTok, Instagram, Facebook) |
| `social_free.py` | ~300 | Free scrapers (legacy, mostly non-functional) |

### Services - Ad Library (`services/adlibrary/`)

| File | Lines | Role |
|------|-------|------|
| `scraper.py` | ~1,700 | Facebook Ad Library scraping, video/image download |
| `analyzer.py` | ~750 | Video analysis with Gemini Vision |
| `apify_facebook.py` | ~300 | Apify-based Facebook ad scraping |
| `playwright_search.py` | ~400 | Browser automation for ad discovery |
| `taxonomies.py` | ~300 | Ad creative taxonomies (hooks, frameworks, styles) |

### Services - Generators (`services/generators/`)

| File | Lines | Role |
|------|-------|------|
| `scripts.py` | ~450 | Ad script generation from insights |
| `thumbnails.py` | ~150 | Thumbnail concept suggestions |
| `ab_tests.py` | ~170 | A/B test recommendations |

### Services - Processors (`services/processors/`)

Data normalization layer - transforms raw scraped data into standardized format.

| File | Role |
|------|------|
| `base.py` | Base processor class with common methods |
| `adlibrary_processor.py` | Ad Library data normalization |
| `article_processor.py` | News/blog article processing |
| `brand_processor.py` | Brand mention processing |
| `competitive_processor.py` | Competitor data processing |
| `discussion_processor.py` | Forum/discussion processing |
| `review_processor.py` | Review data processing |
| `social_processor.py` | Social media post processing |
| `video_processor.py` | Video content processing |

### Services - Analyzers (`services/`)

| File | Lines | Role |
|------|-------|------|
| `social_media_analyzer.py` | ~600 | TikTok/Instagram video analysis |
| `social_video_analyzer.py` | ~300 | Video download and analysis coordination |
| `youtube_analyzer.py` | ~600 | YouTube content analysis |
| `twitter_analyzer.py` | ~450 | Twitter/X content analysis |
| `reddit_analyzer.py` | ~400 | Reddit post/comment analysis |
| `review_analyzer.py` | ~400 | Review sentiment analysis |
| `sentiment.py` | ~300 | Sentiment classification |
| `cross_source_analyzer.py` | ~500 | Cross-source pattern detection |
| `snippet_classifier.py` | ~470 | Content type classification |

### Services - RAG (`services/rag/`)

| File | Lines | Role |
|------|-------|------|
| `embeddings.py` | ~100 | Text embedding generation |
| `vector_store.py` | ~280 | Vector database operations |

### Services - LLM (`services/llm/`)

| File | Lines | Role |
|------|-------|------|
| `client.py` | ~250 | Unified OpenAI/Gemini client |
| `prompts.py` | ~650 | All LLM prompt templates |

### Services - Other

| File | Lines | Role |
|------|-------|------|
| `competitors/analyzer.py` | ~400 | Competitor profile building, SWOT |
| `landing_pages/analyzer.py` | ~400 | Landing page analysis |
| `unified_data_layer.py` | ~450 | Unified data access layer |
| `proto_icp_builder.py` | ~400 | Proto-ICP generation |
| `proto_icp_clusterer.py` | ~340 | ICP clustering |
| `quality_auditor.py` | ~450 | Output quality validation |
| `kb_exporter.py` | ~400 | Knowledge base export |
| `rag_exporter.py` | ~330 | RAG document export |
| `logging_service.py` | ~170 | Persistent file logging |

---

## Frontend Application (`frontend/src/`)

### Pages

| File | Lines | Role |
|------|-------|------|
| `Dashboard.tsx` | ~270 | Brand list, create new brand, recent brands |
| `Research.tsx` | ~580 | Research progress tracking, source grid |
| `Results.tsx` | ~4,200 | Results display with tabs (Brand DNA, Insights, Ads, Scripts) |

### Components

| File | Role |
|------|------|
| `Layout.tsx` | Main layout wrapper with navigation |
| `ChatPanel.tsx` | RAG chat interface |

### API

| File | Role |
|------|------|
| `api/client.ts` | Axios client for backend API |

---

## Backend Root Files

### Configuration

| File | Role |
|------|------|
| `.env` | Environment variables (API keys, database URL) |
| `requirements.txt` | Python dependencies |
| `Dockerfile` | Container configuration |

### Database

| File | Role |
|------|------|
| `database.db` | Main SQLite database (205 MB) |

### Debug/Test Scripts (50+ files)

Notable test files:
- `test_full_research.py` - End-to-end pipeline test
- `test_phase*.py` - Phase-specific tests
- `test_adlib_*.py` - Ad Library testing
- `test_apify_*.py` - Apify integration tests
- `debug_*.py` - Debugging utilities

### Migration Scripts

| File | Role |
|------|------|
| `migrate_add_adlib_page_id.py` | Add adlib_page_id column |
| `migrate_add_video_columns.py` | Add video analysis columns |
| `migrate_intake_fields.py` | Add intake brief fields |
| `migrate_proto_icps.py` | Add proto-ICP support |
| `migrate_scraped_data_columns.py` | Extend scraped_data columns |

### Utility Scripts

| File | Role |
|------|------|
| `export_knowledge.py` | Export knowledge base |
| `sync_anythingllm.py` | Sync with AnythingLLM |
| `audit_scrapers.py` | Audit scraper functionality |

---

## Root Directory Files

### Documentation

| File | Lines | Role |
|------|-------|------|
| `ARCHITECTURE.md` | ~338 | System architecture overview |
| `PROJECT_CONTEXT.md` | ~300 | Project history and context |
| `SCRAPERS_REFERENCE.md` | ~267 | Scraper documentation |
| `BRAND_DNA_PLAN.md` | ~280 | Brand DNA feature plan |
| `CORE_PRINCIPLES.md` | ~420 | Design principles |
| `CONVERSATION_MEMORY.md` | ~120 | Conversation context |
| `FUTURE_ROADMAP.md` | ~160 | Roadmap |
| `ANYTHINGLLM_CONFIG.md` | ~70 | AnythingLLM setup |
| `README.md` | ~120 | Project readme |

### Execution Scripts

| File | Role |
|------|------|
| `start_all.bat` | Start all services |
| `start_servers.bat` | Start backend + frontend |
| `setup_chat.bat` | Setup chat dependencies |
| `docker-compose.yml` | Docker orchestration |

---

## Output Directories

### `backend/output/`
Downloaded media files organized by type:
- `adlibrary/{brand}/` - Ad videos and images
- `social_media/{platform}/` - TikTok/Instagram videos

### `backend/logs/`
Session log files: `research_session_{id}.jsonl`

### `backend/knowledge_base/`
Exported knowledge documents per brand

### `backend/vector_db/`
Chroma vector database files

---

## Statistics

| Category | Count |
|----------|-------|
| Backend App Files | 74 |
| Backend Root Scripts | 127 |
| Frontend Source Files | 10 |
| Database Models | 4 |
| Pydantic Schemas | 34+ |
| Service Modules | 36+ |
| Test Files | 50+ |
| Total Python Lines (est.) | 15,000+ |
