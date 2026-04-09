# System Architecture

> High-level architecture of the Brand Intelligence Scraper system with data flow diagrams and component relationships.

---

## System Overview

The Brand Intelligence Scraper is a multi-source data collection and analysis platform that:

1. **Discovers** brand identity from websites
2. **Scrapes** mentions and reviews from 15+ platforms
3. **Analyzes** content with AI (text + video)
4. **Generates** creative assets (scripts, thumbnails, insights)
5. **Provides** RAG-powered chat interface

---

## High-Level Architecture

```mermaid
graph TB
    subgraph Frontend["Frontend (React)"]
        UI[Dashboard/Research/Results]
        Chat[ChatPanel]
    end
    
    subgraph API["FastAPI Backend"]
        Routers[API Routers]
        Orchestrator[Research Orchestrator]
    end
    
    subgraph Services["Core Services"]
        Discovery[Brand Discovery]
        DNA[Brand DNA]
        KeyGen[Query Generator]
        Scrapers[Scrapers Layer]
        Analyzers[Analyzers Layer]
        Generators[Generators Layer]
        Insights[Insights Engine]
    end
    
    subgraph External["External APIs"]
        OpenAI[OpenAI GPT]
        Gemini[Gemini Vision]
        Firecrawl[Firecrawl API]
        Apify[Apify Cloud]
        ALLM[AnythingLLM]
    end
    
    subgraph Storage["Data Storage"]
        SQLite[(SQLite DB)]
        VectorDB[(Vector DB)]
        Files[Output Files]
    end
    
    UI --> Routers
    Chat --> Routers
    Routers --> Orchestrator
    Orchestrator --> Discovery
    Orchestrator --> DNA
    Orchestrator --> KeyGen
    Orchestrator --> Scrapers
    Orchestrator --> Analyzers
    Orchestrator --> Generators
    Orchestrator --> Insights
    
    Discovery --> Firecrawl
    Scrapers --> Firecrawl
    Scrapers --> Apify
    Analyzers --> Gemini
    Insights --> OpenAI
    Generators --> OpenAI
    Chat --> ALLM
    
    Services --> SQLite
    Services --> VectorDB
    Scrapers --> Files
```

---

## Research Pipeline Flow

The main research pipeline runs in 7 phases:

```mermaid
flowchart TD
    Start([Start Research]) --> P1

    subgraph P1["Phase 1: Brand Analysis (Parallel)"]
        DNA[Brand DNA Extraction]
        Disc[Brand Discovery]
        AdLib[Ad Library Background]
    end
    
    P1 --> P2["Phase 2: Query Generation"]
    
    P2 --> P3
    subgraph P3["Phase 3: Scraping (Sequential)"]
        T1[Track 1: Brand Mentions]
        T2[Track 2: Segment Research]
        T1 --> T2
    end
    
    P3 --> P4["Phase 4: Wait for Ad Library"]
    
    P4 --> P5
    subgraph P5["Phase 5: Analysis (Parallel)"]
        VA[Video Analysis]
        CA[Competitor Analysis]
        SA[Sentiment Analysis]
    end
    
    P5 --> P6["Phase 6: Insights Generation"]
    
    P6 --> P7
    subgraph P7["Phase 7: Content Generation (Parallel)"]
        Scripts[Script Generator]
        Thumbnails[Thumbnail Suggester]
        ABTests[A/B Test Suggester]
    end
    
    P7 --> End([Complete])
```

---

## Data Flow Diagram

```mermaid
flowchart LR
    subgraph Input["Input"]
        Brand[Brand Name + URL]
    end
    
    subgraph Collection["Data Collection"]
        Web[Website Scrape]
        Social[Social Media]
        Reviews[Reviews/Forums]
        Ads[Ad Library]
    end
    
    subgraph Processing["Processing"]
        Norm[Normalize]
        Classify[Classify]
        Sentiment[Sentiment]
        Video[Video Analysis]
    end
    
    subgraph Analysis["Analysis"]
        Insights[Insights Engine]
        Cross[Cross-Source]
        Proto[Proto-ICP]
    end
    
    subgraph Output["Output"]
        DB[(Database)]
        Scripts[Scripts]
        Report[Full Report]
        RAG[(RAG Index)]
    end
    
    Brand --> Web
    Brand --> Social
    Brand --> Reviews
    Brand --> Ads
    
    Web --> Norm
    Social --> Norm
    Reviews --> Norm
    Ads --> Video
    
    Norm --> Classify
    Classify --> Sentiment
    Video --> Insights
    
    Sentiment --> Insights
    Insights --> Cross
    Cross --> Proto
    
    Proto --> DB
    Proto --> Scripts
    Proto --> Report
    DB --> RAG
```

---

## Scraping Architecture

```mermaid
flowchart TB
    subgraph Track1["Track 1: Brand Mentions"]
        R1[Reddit Brand]
        TP[Trustpilot]
        News[News/Blogs]
        TW[Twitter/X]
        IG[Instagram]
        TT[TikTok]
        FB[Facebook]
        YT[YouTube]
        QR[Quora]
    end
    
    subgraph Track2["Track 2: Segment Research"]
        SUB[Subreddits]
        PROB[Problem Searches]
        FOR[Forums]
        QQ[Quora Questions]
        HASH[Hashtag Searches]
        AMZ[Amazon Reviews]
        GOOG[Google Reviews]
    end
    
    subgraph Scrapers["Scraper Layer"]
        FC[Firecrawl Scraper]
        AP[Apify Scraper]
        SF[Social Free - Legacy]
    end
    
    R1 --> FC
    TP --> FC
    News --> FC
    QR --> FC
    SUB --> FC
    PROB --> FC
    FOR --> FC
    QQ --> FC
    
    TW --> AP
    IG --> AP
    TT --> AP
    FB --> AP
    AMZ --> AP
    GOOG --> AP
    HASH --> AP
```

---

## RAG Chat Architecture

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend
    participant AnythingLLM
    participant VectorDB
    
    User->>Frontend: Send message
    Frontend->>Backend: POST /api/chat/
    Backend->>AnythingLLM: Query workspace
    AnythingLLM->>VectorDB: Retrieve docs
    VectorDB-->>AnythingLLM: Relevant chunks
    AnythingLLM->>AnythingLLM: Generate response
    AnythingLLM-->>Backend: Response + citations
    Backend-->>Frontend: JSON response
    Frontend-->>User: Display answer
```

---

## Sources of Truth

### Canonical Storage

| Data Type | Storage | Location |
|-----------|---------|----------|
| Raw scraped data | SQLite | `scraped_data` table |
| Cleaned/enriched data | SQLite | `scraped_data.raw_data` JSON |
| Brand metadata | SQLite | `brands` table |
| Session state | SQLite | `research_sessions` table |
| Insights/ICPs | SQLite | `insights` table |
| Video files | Filesystem | `output/adlibrary/`, `output/social_media/` |
| Embeddings | ChromaDB | `vector_db/` |
| RAG documents | AnythingLLM | Per-workspace storage |
| Session logs | Filesystem | `logs/research_session_*.jsonl` |

### Primary Key System

| Entity | Primary Key | Format | Example |
|--------|-------------|--------|---------|
| Brand | `brand_id` | Auto-increment | `42` |
| Session | `session_id` | Auto-increment | `77` |
| Scraped Item | `id` | Auto-increment | `12345` |
| Insight | `id` | ForeignKey(session_id) | `77` |
| Video file | URL hash | `{brand}/video_{idx}.mp4` | `goodfood/video_001.mp4` |

### Linking Keys

| Relationship | Key | Notes |
|--------------|-----|-------|
| Brand → Sessions | `brand_id` | One-to-many |
| Session → Data | `session_id` | One-to-many |
| Session → Insights | `session_id` | One-to-one |
| Data → Source | `source_type` | Enum (reddit, twitter, etc.) |
| Data → Track | `track` | 1 = Brand, 2 = Segment |

---

## Component Dependencies

```mermaid
graph TD
    subgraph Core["Core"]
        Orch[research_orchestrator]
        Config[config]
        DB[database]
        Models[models]
    end
    
    subgraph Discovery["Discovery"]
        BDisc[brand_discovery]
        BDNA[brand_dna]
        BExt[brand_extractor]
    end
    
    subgraph Scrape["Scraping"]
        FC[firecrawl]
        AP[apify]
        AdLib[adlibrary]
    end
    
    subgraph Analyze["Analysis"]
        SMA[social_media_analyzer]
        Sent[sentiment]
        Cross[cross_source_analyzer]
        Snip[snippet_classifier]
    end
    
    subgraph Generate["Generation"]
        Ins[insights]
        Scr[scripts]
        Thumb[thumbnails]
        AB[ab_tests]
    end
    
    subgraph LLM["LLM Layer"]
        Client[llm/client]
        Prompts[llm/prompts]
    end
    
    Orch --> Discovery
    Orch --> Scrape
    Orch --> Analyze
    Orch --> Generate
    
    Discovery --> LLM
    Analyze --> LLM
    Generate --> LLM
    
    Scrape --> Config
    LLM --> Config
```

---

## Error Handling Flow

```mermaid
flowchart TD
    Task[Task Execution] --> Try{Try}
    Try -->|Success| Log[Log Success]
    Try -->|Error| Catch[Catch Exception]
    
    Catch --> Type{Error Type}
    
    Type -->|429 Rate Limit| Retry[Exponential Backoff]
    Type -->|Timeout| Skip[Skip + Log Warning]
    Type -->|API Error| Fallback[Try Fallback]
    Type -->|Parse Error| Default[Return Empty + Log]
    
    Retry -->|Max Retries| Skip
    Retry -->|Success| Log
    Fallback -->|Success| Log
    Fallback -->|Fail| Skip
    
    Log --> Continue[Continue Pipeline]
    Skip --> Continue
    Default --> Continue
```

---

## Technology Stack Summary

| Layer | Technology | Purpose |
|-------|------------|---------|
| Frontend | React + TypeScript | UI |
| Styling | Tailwind CSS | Design |
| API | FastAPI | Backend |
| ORM | SQLAlchemy (async) | Database |
| Database | SQLite | Storage |
| Vector DB | ChromaDB | Embeddings |
| LLM | OpenAI GPT-4o | Text generation |
| Vision | Gemini 2.0 Flash | Video analysis |
| Web Scraping | Firecrawl | General web |
| Social Scraping | Apify | Social platforms |
| Video Download | yt-dlp | Media download |
| Browser Automation | Playwright | Ad Library |
| RAG | AnythingLLM | Chat + retrieval |
