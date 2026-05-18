"""
Brand Intelligence & Creative Research Tool
FastAPI main entry point.
"""
import sys
import os
# Ensure UTF-8 output on Windows to prevent UnicodeEncodeError with emojis in ad copy
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from pathlib import Path

from .config import settings
from .database import init_db
from .routers import brands, research, chat, idea_bank


# Path to built frontend
FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print(f"[*] Starting {settings.APP_NAME}...")
    await init_db()
    print("[+] Database initialized")
    if FRONTEND_DIST.exists():
        print(f"[+] Serving frontend from {FRONTEND_DIST}")
    else:
        print(f"[!] Frontend not built - run 'npx vite build' in frontend/")
    yield
    # Shutdown
    print("[*] Shutting down...")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Scrape brands, analyze markets, generate Creative Dimensions",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)

# Mount output directory for serving ad videos and thumbnails
OUTPUT_DIR = Path(__file__).parent.parent / "output"
if OUTPUT_DIR.exists():
    app.mount("/api/research/videos", StaticFiles(directory=str(OUTPUT_DIR)), name="research-videos")
    print(f"[+] Serving research videos from {OUTPUT_DIR}")

# Include routers
app.include_router(brands.router, prefix="/api/brands", tags=["Brands"])
app.include_router(research.router, prefix="/api/research", tags=["Research"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(idea_bank.router, prefix="/api", tags=["Idea Bank"])


# Serve built frontend (for ngrok/production sharing)
if FRONTEND_DIST.exists():
    # Mount static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="frontend-assets")
    
    # SPA catch-all: any non-API route returns index.html
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the SPA frontend for any non-API route."""
        # Never intercept API routes
        if full_path.startswith("api/"):
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        # Check if specific file exists in dist
        file_path = FRONTEND_DIST / full_path
        if full_path and file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        # Otherwise return index.html (SPA routing)
        return FileResponse(FRONTEND_DIST / "index.html")
else:
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "name": settings.APP_NAME,
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs",
            "note": "Frontend not built. Run 'npx vite build' in frontend/ to enable UI."
        }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


