# Observability & Monitoring

> Logging, metrics, and tracing for the Brand Intelligence Scraper.

---

## Overview

The system uses structured logging and file-based persistence for debugging and monitoring research sessions.

---

## Session Logging

### Log Files

```
backend/logs/
├── research_session_1.jsonl
├── research_session_2.jsonl
├── research_session_77.jsonl
└── ...
```

### Log Format (JSON Lines)

```json
{"timestamp": "2026-01-08T04:05:23.456", "level": "info", "message": "Starting Phase 1: Brand Analysis", "source": "orchestrator"}
{"timestamp": "2026-01-08T04:05:24.123", "level": "info", "message": "Brand DNA extraction started", "source": "brand_dna"}
{"timestamp": "2026-01-08T04:05:45.789", "level": "info", "message": "Found 5 brand colors", "source": "brand_dna"}
```

### Log Levels

| Level | Usage |
|-------|-------|
| `info` | Normal operations, phase transitions |
| `warning` | Recoverable issues, empty results |
| `error` | Failures, exceptions |
| `debug` | Verbose details (disabled in production) |

---

## Logging Service

**File:** `services/logging_service.py`

```python
def get_logger(session_id: int):
    """Get session-specific logger."""
    return SessionLogger(session_id)

def log_research_start(session_id: int, brand_name: str):
    """Log research session start."""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "event": "research_start",
        "brand_name": brand_name,
        "session_id": session_id
    }
    append_to_log(session_id, log_entry)

def log_scrape_result(session_id: int, source: str, count: int, success: bool):
    """Log scraping results."""
    ...

def log_error(session_id: int, error: str, source: str):
    """Log errors with context."""
    ...
```

---

## Run ID & Tracing

### Session-based Tracing

Every research run is identified by:

| ID | Type | Purpose |
|----|------|---------|
| `session_id` | Integer | Primary run identifier |
| `brand_id` | Integer | Brand being researched |
| `timestamp` | ISO 8601 | Execution time |

### Log Entry Format

```python
{
    "timestamp": "2026-01-08T04:05:23.456Z",
    "session_id": 77,
    "level": "info",
    "source": "firecrawl",  # Component name
    "message": "Scraped 45 Reddit posts",
    "data": {  # Optional structured data
        "query": "goodfood review",
        "result_count": 45,
        "duration_ms": 2340
    }
}
```

---

## Console Logging

All operations print to console with timestamps:

```
[2026-01-08T04:05:23] [Phase 1] Starting Brand Analysis...
[2026-01-08T04:05:24] [BrandDNA] Extracting brand identity...
[2026-01-08T04:05:45] [BrandDNA] Found 5 colors, 3 values
[2026-01-08T04:05:46] [Discovery] Sector: Meal Kit Delivery
[2026-01-08T04:06:00] [!] Firecrawl rate limited, retrying...
[2026-01-08T04:06:05] [Reddit] Found 45 posts
```

---

## API Metrics

### Tracked Metrics

| Metric | Location | Purpose |
|--------|----------|---------|
| Scrape counts | Per session log | Data volume |
| API calls | Session stats | Cost tracking |
| Error counts | Session stats | Reliability |
| Duration | Per phase | Performance |

### API Usage Endpoint

```
GET /api/research/metrics
```

Returns:
```json
{
  "session_id": 77,
  "api_calls": {
    "firecrawl": 23,
    "apify": 8,
    "openai": 4,
    "gemini": 12
  },
  "errors": {
    "firecrawl": 2,
    "apify": 0
  },
  "estimated_cost_usd": 1.23
}
```

---

## Database Metrics

### Session Progress

Stored in `research_sessions` table:

```python
{
    "progress_percent": 65,
    "current_phase": "Phase 3: Scraping",
    "phase_details": {
        "track1_complete": true,
        "track2_sources": ["reddit", "quora"],
        "track2_pending": ["amazon", "google"]
    }
}
```

### Data Counts

```sql
SELECT source_type, COUNT(*) as count
FROM scraped_data
WHERE session_id = 77
GROUP BY source_type;
```

---

## Real-time Logs Endpoint

```
GET /api/research/session/{id}/logs?since=2026-01-08T04:00:00Z&limit=100
```

Used by frontend LogsPanel for live updates.

---

## Performance Monitoring

### Phase Duration Tracking

```python
def _log_phase_start(self, phase_name):
    self.phase_start_time = time.time()
    self._log(f"Starting {phase_name}")

def _log_phase_end(self, phase_name, result_summary):
    duration = time.time() - self.phase_start_time
    self._log(f"Completed {phase_name} in {duration:.1f}s: {result_summary}")
```

### Typical Durations

| Phase | Expected Duration |
|-------|-------------------|
| Phase 1: Brand Analysis | 30-60 seconds |
| Phase 2: Query Generation | 5-10 seconds |
| Phase 3: Scraping | 3-5 minutes |
| Phase 4: Ad Library | 2-4 minutes |
| Phase 5: Analysis | 1-2 minutes |
| Phase 6: Insights | 30-60 seconds |
| Phase 7: Generation | 1-2 minutes |

---

## Cost Tracking

### Estimated Costs per Run

| Service | Cost/Run |
|---------|----------|
| OpenAI (GPT-4o) | $0.30-0.80 |
| Gemini (video analysis) | $0.10-0.30 |
| Firecrawl | API credits |
| Apify | ~$0.50-2.00 |

### Token Counting (Not Yet Implemented)

Future enhancement to track actual token usage per LLM call.

---

## Health Checks

### Backend Health

```
GET /health
```

Returns:
```json
{
  "status": "healthy",
  "database": "connected",
  "services": {
    "firecrawl": "configured",
    "apify": "configured",
    "openai": "configured",
    "gemini": "configured"
  }
}
```

---

## Alerts (Future)

Currently not implemented. Planned:
- Slack alerts for failed sessions
- Email alerts for quota warnings
- Dashboard for real-time monitoring
