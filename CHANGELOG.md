# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.0.0] — 2026-04-08

### Added

#### Research Pipeline
- Full research pipeline with 6-phase orchestration
- Brand DNA extraction (colors, fonts, values, tagline, social media, visual aesthetic)
- Dual-track scraping: Track 1 (brand mentions) + Track 2 (market segment)
- Meta Ad Library integration with Gemini Vision frame-by-frame analysis
- RoBERTa-based sentiment analysis with per-source breakdown
- AI chatbot with RAG-powered semantic search via ChromaDB
- Competitor analysis with SWOT matrix and competitive profiles
- TikTok trend analysis (trending sounds, hashtags, content patterns)
- Instagram brand presence analysis (voice, aesthetic, content pillars)
- Proto-ICP clustering (trigger × blocker segmentation)

#### Content Generation
- Ad script generator (UGC, testimonial, educational, problem-solution formats)
- Hooks Library with 30+ categorized hooks and strength scores
- Thumbnail concept suggestions
- A/B test recommendations

#### Platform Features
- Idea Bank for saving creative ideas across research sessions
- Real-time progress tracking with phase-level detail and session logs
- Incremental analysis (add data to existing sessions)
- Reprocess insights (re-run analysis without re-scraping)
- Export to Markdown
- Session cancellation and stuck-session recovery
- API quota pre-flight checks
- API usage metrics tracking

#### Frontend
- React 19 + TypeScript + Vite + TailwindCSS
- Dashboard with brand management
- Live research progress with polling
- Tabbed results view (Insights, Ad Intelligence, Sentiment, TikTok, Instagram, Hooks Library, Data, Generated Content)
- AI Chat panel with suggested questions
- Idea Bank with filtering, favorites, and search

#### Infrastructure
- Docker Compose deployment (Backend + Frontend + AnythingLLM)
- ngrok sharing support (SPA hosted from backend)
- Windows `start_servers.bat` for local development

### Integrations
- OpenAI GPT-4o / Google Gemini 2.5 Flash (configurable via `LLM_PROVIDER`)
- Firecrawl (web scraping and search)
- Apify (TikTok, Twitter, Reddit, Instagram, Amazon, Google Reviews, Trustpilot)
- AnythingLLM (optional RAG chat with document workspaces)
- ChromaDB (local vector store for semantic search)
- Playwright (Ad Library scraping fallback)
