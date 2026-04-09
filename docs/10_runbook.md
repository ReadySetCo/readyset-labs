# Operations Runbook

> Guide for running, debugging, and maintaining the Brand Intelligence Scraper.

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Docker Desktop (for AnythingLLM)
- API keys configured

### Setup from Scratch

```powershell
# 1. Clone repository
git clone <repo-url>
cd SCRAPPER

# 2. Backend setup
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env
# Edit .env with your API keys

# 4. Frontend setup
cd ..\frontend
npm install

# 5. Return to root and start
cd ..
.\start_servers.bat
```

---

## Starting Services

### Option 1: All Services (Recommended)

```powershell
# Starts Docker + AnythingLLM + Backend + Frontend
.\start_all.bat
```

### Option 2: Backend + Frontend Only

```powershell
.\start_servers.bat
```

### Option 3: Manual Start

```powershell
# Terminal 1: Backend
cd backend
.\venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

---

## Verifying Installation

### Check Backend Health

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Expected: `{"status": "healthy", ...}`

### Check API Configuration

```powershell
python diagnose_apis.py
```

### Verify Frontend

Open http://localhost:5173 in browser.

---

## Running a Minimal Test

### 1-Brand, 1-Source Test

```powershell
cd backend
.\venv\Scripts\activate

# Create brand
$body = '{"name": "TestBrand", "website_url": "https://example.com"}'
$brand = Invoke-RestMethod -Uri "http://localhost:8000/api/brands/" -Method POST -Body $body -ContentType "application/json"
$brand.id

# Start research
$body2 = "{`"brand_id`": $($brand.id)}"
$session = Invoke-RestMethod -Uri "http://localhost:8000/api/research/start" -Method POST -Body $body2 -ContentType "application/json"
$session.id

# Check progress
Invoke-RestMethod -Uri "http://localhost:8000/api/research/session/$($session.id)/progress"

# Get results
Invoke-RestMethod -Uri "http://localhost:8000/api/research/session/$($session.id)/full"
```

---

## Common Operations

### Reprocess Insights (Keep Data, Redo Analysis)

```powershell
$sessionId = 77
$body = "{}"
Invoke-RestMethod -Uri "http://localhost:8000/api/research/session/$sessionId/reprocess" -Method POST -Body $body -ContentType "application/json"
```

### Generate More Scripts

```powershell
$sessionId = 77
Invoke-RestMethod -Uri "http://localhost:8000/api/research/session/$sessionId/scripts/more?count=3" -Method POST
```

### Scrape Ad Library Only

```powershell
$sessionId = 77
Invoke-RestMethod -Uri "http://localhost:8000/api/research/session/$sessionId/adlibrary" -Method POST
```

### Sync to AnythingLLM

```powershell
$sessionId = 77
Invoke-RestMethod -Uri "http://localhost:8000/api/chat/sync/$sessionId" -Method POST
```

---

## Debug Mode

### Enable Verbose Logging

Edit `backend/app/config.py`:
```python
DEBUG: bool = True
```

### Run with Debug Output

```powershell
# Show all print statements
$env:PYTHONUNBUFFERED = "1"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Check Session Logs

```powershell
Get-Content backend/logs/research_session_77.jsonl | ConvertFrom-Json | Format-Table
```

---

## Troubleshooting Playbooks

### "Brand Not Found in Ad Library"

1. Check if brand has Facebook page:
   ```python
   print(brand.social_media_urls.get("facebook"))
   ```

2. Search manually:
   ```
   https://www.facebook.com/ads/library/?active_status=all&ad_type=all&q=BrandName
   ```

3. Get page ID directly and set:
   ```sql
   UPDATE brands SET ad_library_page_id = '123456789' WHERE id = 42;
   ```

---

### "Empty Outputs / No Insights"

1. Check scraped data count:
   ```python
   python check_sessions.py
   # SELECT COUNT(*) FROM scraped_data WHERE session_id = 77;
   ```

2. If data exists, reprocess:
   ```powershell
   curl -X POST http://localhost:8000/api/research/session/77/reprocess
   ```

3. If no data, check scraper logs:
   ```powershell
   Get-Content backend/analysis_log.txt | Select-String "error" | Select -Last 20
   ```

---

### "LLM JSON Malformed"

1. Check LLM response in logs
2. Verify API key is valid:
   ```python
   python test_llm.py
   ```
3. Retry with reprocess endpoint

---

### "Session Stuck in progress"

1. Check backend terminal for errors
2. Look at session logs:
   ```powershell
   Get-Content backend/logs/research_session_77.jsonl | Select -Last 50
   ```
3. Manually update status:
   ```python
   # In Python shell
   from app.database import get_db
   session.status = "failed"
   db.commit()
   ```

---

### "Vector Index Inconsistent"

1. Delete and recreate workspace:
   ```powershell
   # In AnythingLLM: Settings > Workspaces > Delete > Recreate
   ```

2. Resync:
   ```powershell
   curl -X POST http://localhost:8000/api/chat/sync/77
   ```

---

## Database Management

### View All Sessions

```python
python check_sessions.py
```

### Delete Old Sessions

```python
from app.database import SessionLocal
from app.models import ResearchSession, ScrapedData

db = SessionLocal()
db.query(ScrapedData).filter(ScrapedData.session_id < 50).delete()
db.query(ResearchSession).filter(ResearchSession.id < 50).delete()
db.commit()
```

### Reset Database Completely

```powershell
cd backend
Remove-Item database.db
# Restart uvicorn to recreate
```

---

## Migrations

### Apply New Columns

```powershell
cd backend
python migrate_add_video_columns.py
python migrate_intake_fields.py
python migrate_proto_icps.py
```

---

## Monitoring Production

### Watch Live Logs

```powershell
Get-Content backend/analysis_log.txt -Wait -Tail 50
```

### Check API Metrics

```
GET http://localhost:8000/api/research/metrics
```

### Queue Status

```
GET http://localhost:8000/api/research/queue-status
```

---

## Backup & Restore

### Backup Database

```powershell
Copy-Item backend/database.db "backups/database_$(Get-Date -Format 'yyyyMMdd').db"
```

### Backup Media

```powershell
Compress-Archive -Path backend/output -DestinationPath "backups/output_$(Get-Date -Format 'yyyyMMdd').zip"
```

---

## Performance Tuning

### Reduce API Costs

Edit `config.py`:
```python
MAX_POSTS_PER_SOURCE = 30  # Reduce from 100
MAX_REVIEWS_PER_SOURCE = 50
```

### Speed Up Scraping

```python
# Increase concurrent requests (careful with rate limits)
_firecrawl_semaphore = asyncio.Semaphore(3)  # From 2
```

### Limit Video Analysis

In `social_media_analyzer.py`:
```python
MAX_VIDEOS_PER_PLATFORM = 10  # From 20
```
