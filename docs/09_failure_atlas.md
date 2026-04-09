# Failure Atlas

> Catalog of known failures, root causes, and resolutions.

---

## Overview

This document catalogs common failures observed in production, along with detection methods, root causes, and fixes.

---

## Scraping Failures

### 1. Firecrawl 429 Rate Limited

**Error signature:**
```
HTTP 429 Too Many Requests
```

**Root cause:** Exceeding Firecrawl's rate limit (3-5 req/sec)

**Detection:** Response status code 429

**Resolution:** 
- Automatic: Exponential backoff (5s, 10s, 15s)
- Manual: Increase `MIN_REQUEST_INTERVAL`

**Owner:** Scraping layer

---

### 2. Firecrawl Timeout

**Error signature:**
```
httpx.TimeoutException: Request timed out after 20s
```

**Root cause:** Slow target site or network issues

**Detection:** Exception type

**Resolution:**
- Skip source and continue pipeline
- Increase `SCRAPE_TIMEOUT` for specific sources

---

### 3. Apify Actor Failed

**Error signature:**
```
Actor run failed with status: FAILED
```

**Root cause:** Actor bug, rate limit, or invalid input

**Detection:** Run status !== "SUCCEEDED"

**Resolution:**
- Check Apify dashboard for actor logs
- Verify input format
- Try different actor or fallback to Firecrawl

---

### 4. Empty Scrape Results

**Error signature:**
```
[Reddit] Found 0 posts for query "brand name"
```

**Root cause:** 
- Brand is new/unknown
- Query too specific
- Platform blocking

**Detection:** Result count = 0

**Resolution:**
- Normal for new brands
- Broaden queries
- Check if platform is accessible

---

## Ad Library Failures

### 5. Ad Library Page Not Found

**Error signature:**
```
Could not find Ad Library URL for brand
```

**Root cause:** 
- Brand doesn't advertise on Meta
- Facebook page ID changed
- Name mismatch

**Detection:** `find_ad_library_url` returns None

**Resolution:**
- Try searching with different brand name variants
- Use `view_all_page_id` directly if known
- Skip Ad Library phase

---

### 6. Video Download Failed

**Error signature:**
```
yt-dlp: ERROR: Unable to download video
```

**Root cause:**
- Video no longer available
- Geo-restriction
- Invalid URL format

**Detection:** yt-dlp exit code != 0

**Resolution:**
- Skip video and continue
- Try alternative download method
- Mark as unavailable

---

### 7. Gemini Video Analysis Timeout

**Error signature:**
```
TimeoutError: Video analysis exceeded 60s
```

**Root cause:** 
- Large video file
- Gemini service slow
- File upload failed

**Detection:** asyncio.TimeoutError

**Resolution:**
- Skip video
- Reduce video quality/size
- Increase timeout for batch processing

---

## LLM Failures

### 8. OpenAI Rate Limited

**Error signature:**
```
openai.RateLimitError: Rate limit exceeded
```

**Root cause:** Too many requests per minute

**Detection:** Exception type

**Resolution:**
- Automatic backoff
- Reduce parallel LLM calls
- Use different model/tier

---

### 9. Invalid JSON Response

**Error signature:**
```
json.JSONDecodeError: Expecting value at position...
```

**Root cause:** LLM returned malformed JSON

**Detection:** JSON parse failure

**Resolution:**
- Retry with stricter prompt
- Extract JSON with regex fallback
- Return empty/default response

---

### 10. LLM Maximum Tokens Exceeded

**Error signature:**
```
Maximum context length exceeded
```

**Root cause:** Input data too large

**Detection:** Token count error

**Resolution:**
- Truncate input data
- Summarize before sending
- Split into multiple calls

---

## Database Failures

### 11. SQLite Database Locked

**Error signature:**
```
sqlite3.OperationalError: database is locked
```

**Root cause:** Multiple concurrent writes

**Detection:** Exception type

**Resolution:**
- Use async session properly
- Implement retry logic
- Consider PostgreSQL for production

---

### 12. Missing Column Error

**Error signature:**
```
OperationalError: no such column: scraped_data.new_field
```

**Root cause:** Schema migration not applied

**Detection:** SQL error

**Resolution:**
- Run migration script
- Or delete database and recreate

---

## Frontend Failures

### 13. Research Results Not Loading

**Error signature:**
```
Failed to fetch /api/research/session/77/full
```

**Root cause:**
- Backend not running
- Session doesn't exist
- Response too large

**Detection:** Network error in console

**Resolution:**
- Verify backend is running
- Check session exists in database
- Paginate large responses

---

### 14. UI Freeze on Large Data

**Error signature:**
Browser becomes unresponsive when loading results

**Root cause:** Too many video/image elements rendering

**Detection:** Frontend performance profile

**Resolution:**
- Implement pagination
- Lazy load media
- Virtualize lists

---

## Pipeline Failures

### 15. Research Session Stuck in "in_progress"

**Error signature:**
Session shows "in_progress" indefinitely

**Root cause:**
- Background task crashed
- Exception not caught
- Timeout hit

**Detection:** Session not completing after 30+ minutes

**Resolution:**
- Check backend logs
- Manually update status to "failed"
- Restart with reprocess endpoint

---

### 16. Insights Generation Returns Empty

**Error signature:**
```
insights.icps = []
insights.pain_points = []
```

**Root cause:**
- No scraped data available
- LLM returned empty/invalid response
- Validation failed

**Detection:** All insight arrays empty

**Resolution:**
- Check scraped_data count
- Use reprocess endpoint
- Check LLM response logs

---

## Integration Failures

### 17. AnythingLLM Connection Failed

**Error signature:**
```
httpx.ConnectError: Failed to connect to localhost:3001
```

**Root cause:** AnythingLLM container not running

**Detection:** Connection refused

**Resolution:**
- Start Docker: `docker-compose up -d anythingllm`
- Check Docker status
- Fallback to simple chat mode

---

### 18. Workspace Not Found

**Error signature:**
```
Workspace "brand-xxx" not found
```

**Root cause:** Workspace not synced for this brand

**Detection:** 404 from AnythingLLM

**Resolution:**
- Call sync endpoint: `POST /api/chat/sync/{session_id}`
- Recreate workspace

---

## Network Failures

### 19. DNS Resolution Failed

**Error signature:**
```
httpx.ConnectError: Name or service not known
```

**Root cause:** Network/DNS issues

**Detection:** Connection exception

**Resolution:**
- Check network connectivity
- Verify DNS settings
- Retry after delay

---

### 20. SSL Certificate Error

**Error signature:**
```
ssl.SSLCertVerificationError
```

**Root cause:** Invalid or expired SSL certificate on target

**Detection:** SSL exception

**Resolution:**
- Skip source
- Use verify=False (not recommended for production)
- Check target site status

---

## Quick Reference

| Error | Quick Fix |
|-------|-----------|
| 429 Rate Limited | Wait and retry automatically |
| Timeout | Skip and continue |
| Empty results | Normal for new brands |
| JSON parse error | Retry with fallback |
| Database locked | Restart backend |
| Session stuck | Use reprocess endpoint |
| AnythingLLM down | Start Docker |
