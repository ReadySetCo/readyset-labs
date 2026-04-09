@echo off
REM ============================================================
REM Brand Intelligence Scraper - Full Stack Startup
REM Starts Docker (AnythingLLM) + Backend + Frontend
REM ============================================================

echo [1/4] Starting Docker Desktop if not running...
powershell -Command "if (!(Get-Process 'Docker Desktop' -ErrorAction SilentlyContinue)) { Start-Process 'C:\Program Files\Docker\Docker\Docker Desktop.exe' }"
timeout /t 5 /nobreak >nul

echo [2/4] Starting AnythingLLM container...
cd /d "%~dp0"
docker-compose up -d anythingllm
if errorlevel 1 (
    echo [WARNING] Docker not ready yet, waiting 30 seconds...
    timeout /t 30 /nobreak
    docker-compose up -d anythingllm
)

echo Waiting for AnythingLLM to be healthy...
:wait_anythingllm
timeout /t 3 /nobreak >nul
curl -s http://localhost:3001/api/ping >nul 2>&1
if errorlevel 1 (
    echo   Still waiting...
    goto wait_anythingllm
)
echo [OK] AnythingLLM is running on http://localhost:3001

echo [3/4] Starting Backend...
start "Backend" cmd /k "cd /d %~dp0backend && .\venv\Scripts\python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
timeout /t 3 /nobreak >nul

echo [4/4] Starting Frontend...
start "Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ============================================================
echo All services starting:
echo   - AnythingLLM: http://localhost:3001
echo   - Backend API: http://localhost:8000
echo   - Frontend:    http://localhost:5173
echo ============================================================
echo.
pause
