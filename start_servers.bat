@echo off
echo ===============================================
echo   Brand Intelligence Scraper
echo ===============================================
echo.

REM === KILL OLD PROCESSES FIRST ===
echo [1/4] Killing any old processes on ports 8000 and 5173...

REM Find and kill processes on port 8000 (backend)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM Find and kill processes on port 5173 (frontend)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM Also kill any remaining python/node processes from previous runs
taskkill /F /IM "python.exe" /FI "WINDOWTITLE eq Backend*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq Frontend*" >nul 2>&1

echo    Ports cleared!
echo.

REM === WAIT A MOMENT ===
timeout /t 2 /nobreak > nul

REM === START BACKEND ===
echo [2/4] Starting Backend (port 8000)...
start "Backend - Brand Intelligence" cmd /k "cd /d %~dp0backend && .\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

REM Wait for backend to initialize
echo    Waiting for backend to start...
timeout /t 4 /nobreak > nul

REM === START FRONTEND ===
echo [3/4] Starting Frontend (port 5173)...
start "Frontend - Vite" cmd /k "cd /d %~dp0frontend && npm run dev"

timeout /t 3 /nobreak > nul

REM === VERIFY ===
echo.
echo [4/4] Verifying servers...
echo.

REM Check if backend is responding
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:8000/health' -TimeoutSec 5 -UseBasicParsing; Write-Host '   Backend:  OK (http://localhost:8000)' -ForegroundColor Green } catch { Write-Host '   Backend:  Starting... (check Backend window)' -ForegroundColor Yellow }"

REM Check if frontend is responding  
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:5173' -TimeoutSec 5 -UseBasicParsing; Write-Host '   Frontend: OK (http://localhost:5173)' -ForegroundColor Green } catch { Write-Host '   Frontend: Starting... (check Frontend window)' -ForegroundColor Yellow }"

echo.
echo ===============================================
echo   SERVERS RUNNING IN SEPARATE WINDOWS
echo ===============================================
echo.
echo   Backend:  http://localhost:8000 (see Backend window for logs)
echo   Frontend: http://localhost:5173
echo.
echo   Press any key to STOP all servers...
pause > nul

REM === CLEANUP ===
echo.
echo Stopping servers...
taskkill /FI "WINDOWTITLE eq Backend*" /F > nul 2>&1
taskkill /FI "WINDOWTITLE eq Frontend*" /F > nul 2>&1

REM Also kill by port just in case
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo Servers stopped.
