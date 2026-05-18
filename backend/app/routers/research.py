"""
Research router - Endpoints for running brand research.
"""

import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta

from ..database import get_db
from ..models import Brand, ResearchSession, ScrapedData, Insight
from ..schemas import (
    ResearchSessionCreate, 
    ResearchSessionResponse, 
    FullResearchResult,
    InsightResponse,
    ScrapedDataResponse,
    APIResponse,
    ResearchProgress
)
from ..services.research_orchestrator import ResearchOrchestrator
from ..utils.session_logging import add_session_log, get_session_logs, clear_session_logs, get_phase_progress

router = APIRouter()

# =============================================
# CONCURRENCY CONTROL
# Limit to 3 simultaneous research analyses
# =============================================
MAX_CONCURRENT_ANALYSES = 3
_analysis_semaphore = asyncio.Semaphore(MAX_CONCURRENT_ANALYSES)
_active_analyses = 0

def get_queue_status():
    """Get current queue status."""
    global _active_analyses
    return {
        "active": _active_analyses,
        "max": MAX_CONCURRENT_ANALYSES,
        "available": MAX_CONCURRENT_ANALYSES - _active_analyses
    }


@router.post("/start", response_model=ResearchSessionResponse)
async def start_research(
    data: ResearchSessionCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Start a new research session for a brand.
    This will:
    1. Run brand discovery (scrape website, analyze with LLM)
    2. Generate search queries for both tracks
    3. Scrape all sources
    4. Generate insights and Creative Dimensions
    """
    # Check if brand exists
    result = await db.execute(select(Brand).where(Brand.id == data.brand_id))
    brand = result.scalar_one_or_none()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Brand with id {data.brand_id} not found"
        )
    
    # Create research session
    session = ResearchSession(
        brand_id=brand.id,
        status="pending"
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    
    # Run research in background
    background_tasks.add_task(
        run_research_pipeline,
        session.id,
        brand.id
    )
    
    return session


async def run_research_pipeline(session_id: int, brand_id: int):
    """
    Background task to run the full research pipeline.
    Uses semaphore to limit concurrent analyses.
    """
    from ..database import async_session
    
    global _active_analyses
    
    # Acquire semaphore to limit concurrent analyses
    async with _analysis_semaphore:
        _active_analyses += 1
        print(f"[Queue] Analysis started. Active: {_active_analyses}/{MAX_CONCURRENT_ANALYSES}")
        
        try:
            async with async_session() as db:
                try:
                    orchestrator = ResearchOrchestrator(db)
                    await orchestrator.run_full_research(session_id, brand_id)
                except Exception as e:
                    # Update session status on failure
                    result = await db.execute(
                        select(ResearchSession).where(ResearchSession.id == session_id)
                    )
                    session = result.scalar_one_or_none()
                    if session:
                        session.status = "failed"
                        await db.commit()
                    print(f"Research pipeline failed: {e}")
                    raise
        finally:
            _active_analyses -= 1
            print(f"[Queue] Analysis finished. Active: {_active_analyses}/{MAX_CONCURRENT_ANALYSES}")


@router.get("/queue/status")
async def get_analysis_queue_status():
    """
    Get current analysis queue status.
    Returns how many analyses are active and how many slots are available.
    """
    return get_queue_status()


@router.get("/session/{session_id}", response_model=ResearchSessionResponse)
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get research session status."""
    result = await db.execute(
        select(ResearchSession).where(ResearchSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with id {session_id} not found"
        )
    
    return session


@router.post("/reprocess/{session_id}")
async def reprocess_session_insights(
    session_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Reprocess insights for an existing session using already scraped data.
    This is useful when insight generation failed but scraping succeeded.
    Does NOT re-scrape data - uses existing scraped_data from the session.
    """
    # Check if session exists
    result = await db.execute(
        select(ResearchSession).where(ResearchSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with id {session_id} not found"
        )
    
    # Check if we have scraped data
    result = await db.execute(
        select(func.count(ScrapedData.id)).where(ScrapedData.session_id == session_id)
    )
    scraped_count = result.scalar() or 0
    
    if scraped_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No scraped data found for this session. Run full research instead."
        )
    
    # Update session status
    session.status = "reprocessing"
    await db.commit()
    
    # Run reprocessing in background
    background_tasks.add_task(
        run_reprocess_pipeline,
        session_id,
        session.brand_id
    )
    
    return {
        "message": f"Reprocessing started for session {session_id}",
        "session_id": session_id,
        "scraped_data_count": scraped_count
    }


async def run_reprocess_pipeline(session_id: int, brand_id: int):
    """
    Background task to reprocess insights from existing scraped data.
    Skips scraping phase entirely - only runs insight generation.
    """
    from ..database import async_session
    
    global _active_analyses
    
    async with _analysis_semaphore:
        _active_analyses += 1
        print(f"[Reprocess] Started for session {session_id}. Active: {_active_analyses}/{MAX_CONCURRENT_ANALYSES}")
        
        try:
            async with async_session() as db:
                try:
                    orchestrator = ResearchOrchestrator(db)
                    await orchestrator.reprocess_insights(session_id, brand_id)
                except Exception as e:
                    result = await db.execute(
                        select(ResearchSession).where(ResearchSession.id == session_id)
                    )
                    session = result.scalar_one_or_none()
                    if session:
                        session.status = "failed"
                        await db.commit()
                    print(f"Reprocess pipeline failed: {e}")
                    import traceback
                    traceback.print_exc()
                    raise
        finally:
            _active_analyses -= 1
            print(f"[Reprocess] Finished session {session_id}. Active: {_active_analyses}/{MAX_CONCURRENT_ANALYSES}")


@router.post("/incremental/{session_id}")
async def run_incremental_analysis(
    session_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Run INCREMENTAL analysis for an existing session.
    - Skips sources that already have data in DB
    - Scrapes only new/missing sources
    - Re-generates insights with combined data (old + new)
    
    Use this when you want to add more data without re-scraping everything.
    """
    # Check if session exists
    result = await db.execute(
        select(ResearchSession).where(ResearchSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with id {session_id} not found"
        )
    
    # Get existing scraped sources
    result = await db.execute(
        select(ScrapedData.source_type, func.count(ScrapedData.id))
        .where(ScrapedData.session_id == session_id)
        .group_by(ScrapedData.source_type)
    )
    existing_sources = {row[0]: row[1] for row in result.all()}
    
    # Update session status
    session.status = "in_progress"
    await db.commit()
    
    # Run incremental analysis in background
    background_tasks.add_task(
        run_incremental_pipeline,
        session_id,
        session.brand_id,
        list(existing_sources.keys())
    )
    
    return {
        "message": f"Incremental analysis started for session {session_id}",
        "session_id": session_id,
        "existing_sources": existing_sources,
        "sources_to_skip": list(existing_sources.keys())
    }


async def run_incremental_pipeline(session_id: int, brand_id: int, skip_sources: List[str]):
    """
    Background task to run incremental analysis.
    Skips sources that were already scraped, adds new data, regenerates insights.
    """
    from ..database import async_session
    
    global _active_analyses
    
    async with _analysis_semaphore:
        _active_analyses += 1
        print(f"[Incremental] Started for session {session_id}. Skip: {skip_sources}. Active: {_active_analyses}/{MAX_CONCURRENT_ANALYSES}")
        
        try:
            async with async_session() as db:
                try:
                    orchestrator = ResearchOrchestrator(db)
                    await orchestrator.run_incremental_research(session_id, brand_id, skip_sources)
                except Exception as e:
                    result = await db.execute(
                        select(ResearchSession).where(ResearchSession.id == session_id)
                    )
                    session = result.scalar_one_or_none()
                    if session:
                        session.status = "failed"
                        await db.commit()
                    print(f"Incremental pipeline failed: {e}")
                    import traceback
                    traceback.print_exc()
                    raise
        finally:
            _active_analyses -= 1
            print(f"[Incremental] Finished session {session_id}. Active: {_active_analyses}/{MAX_CONCURRENT_ANALYSES}")


@router.post("/scrape-ads/{session_id}")
async def scrape_ad_library_for_session(
    session_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Scrape Facebook Ad Library for an existing session.
    This will find and analyze Meta ads for the brand.
    """
    # Check if session exists
    result = await db.execute(
        select(ResearchSession).where(ResearchSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with id {session_id} not found"
        )
    
    # Get brand info
    result = await db.execute(
        select(Brand).where(Brand.id == session.brand_id)
    )
    brand = result.scalar_one_or_none()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )
    
    # Run Ad Library scraping in background
    background_tasks.add_task(
        run_ad_library_pipeline,
        session_id,
        brand.id,
        brand.name
    )
    
    return {
        "message": f"Ad Library scraping started for {brand.name}",
        "session_id": session_id,
        "brand_name": brand.name
    }


async def run_ad_library_pipeline(session_id: int, brand_id: int, brand_name: str):
    """
    Background task to scrape Ad Library for a brand.
    """
    from ..database import async_session
    from ..services.adlibrary import AdLibraryScraper, AdAnalyzer
    
    global _active_analyses
    
    async with _analysis_semaphore:
        _active_analyses += 1
        print(f"[Ad Library] Started for session {session_id} ({brand_name}). Active: {_active_analyses}/{MAX_CONCURRENT_ANALYSES}")
        
        try:
            async with async_session() as db:
                try:
                    # Initialize scrapers
                    scraper = AdLibraryScraper()
                    analyzer = AdAnalyzer()
                    
                    # Find Facebook URL for Ad Library
                    print(f"    [Ad Library] Searching for {brand_name}'s Facebook page...")
                    facebook_url = None
                    
                    # Try to find Facebook URL via search
                    try:
                        from ..services.scrapers.firecrawl import FirecrawlScraper
                        firecrawl = FirecrawlScraper()
                        results = await firecrawl.search(f"{brand_name} facebook page site:facebook.com", limit=3)
                        for result in results or []:
                            url = result.get("url", "")
                            if "facebook.com/" in url and "/ads/" not in url:
                                facebook_url = url
                                print(f"    [Ad Library] Found Facebook: {facebook_url}")
                                break
                    except Exception as e:
                        print(f"    [!] Error searching Facebook: {e}")
                    
                    if not facebook_url:
                        print(f"    [Ad Library] No Facebook page found for {brand_name}")
                        return
                    
                    # Use Apify to scrape (NOT Firecrawl) - provides direct video URLs
                    from ..config import settings
                    max_ads = settings.AD_LIBRARY_MAX_ADS
                    print(f"    [Apify] Scraping ads via Apify (limit={max_ads})...")
                    
                    brand_ads = await scraper.scrape_ad_library_via_apify(
                        facebook_url,
                        limit=max_ads,
                        brand_name=brand_name
                    )
                    
                    ads_found = len(brand_ads.get("ads", []))
                    print(f"    [Ad Library] Found {ads_found} ads")
                    
                    if ads_found > 0:
                        # Analyze with Gemini - up to 30 videos, 30 images
                        max_analyze = min(30, ads_found)
                        print(f"    [Gemini] Analyzing {ads_found} ads with Gemini ({max_analyze} videos, {max_analyze} images max)...")
                        analyzed_ads = await analyzer.analyze_ads_batch(
                            brand_ads.get("ads", []),
                            max_videos=max_analyze,
                            max_images=max_analyze
                        )
                        
                        # Aggregate patterns
                        patterns = analyzer.aggregate_patterns(analyzed_ads)
                        print(f"    [Ad Library] Analysis complete. Patterns extracted.")
                        
                        # Update insights with ad library data
                        result = await db.execute(
                            select(Insight).where(Insight.session_id == session_id)
                        )
                        insight = result.scalar_one_or_none()
                        
                        if insight:
                            # Update existing insight with ad data
                            insight.ad_library_data = {
                                "total_ads": ads_found,
                                "video_ads_count": len([a for a in analyzed_ads if a.get("media_type") == "video"]),
                                "image_ads_count": len([a for a in analyzed_ads if a.get("media_type") == "image"]),
                                "ads": analyzed_ads[:20]  # Store top 20 for display
                            }
                            insight.ad_creative_patterns = patterns
                            await db.commit()
                            print(f"    [Ad Library] Insights updated with {ads_found} ads")
                        else:
                            print(f"    [Ad Library] No insight record found, creating new one...")
                            # Create minimal insight record with ad data
                            new_insight = Insight(
                                session_id=session_id,
                                brand_summary=f"Ad Library analysis for {brand_name}",
                                ad_library_data={
                                    "total_ads": ads_found,
                                    "video_ads_count": len([a for a in analyzed_ads if a.get("media_type") == "video"]),
                                    "image_ads_count": len([a for a in analyzed_ads if a.get("media_type") == "image"]),
                                    "ads": analyzed_ads[:20]
                                },
                                ad_creative_patterns=patterns
                            )
                            db.add(new_insight)
                            await db.commit()
                    
                    print(f"    [Ad Library] Complete!")
                    
                except Exception as e:
                    print(f"[Ad Library] Failed: {e}")
                    import traceback
                    traceback.print_exc()
                    raise
        finally:
            _active_analyses -= 1
            print(f"[Ad Library] Finished session {session_id}. Active: {_active_analyses}/{MAX_CONCURRENT_ANALYSES}")


@router.get("/session/{session_id}/progress", response_model=ResearchProgress)
async def get_session_progress(
    session_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed progress of a research session."""
    result = await db.execute(
        select(ResearchSession).where(ResearchSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with id {session_id} not found"
        )
    
    # Get brand to check Brand DNA status
    result = await db.execute(
        select(Brand).where(Brand.id == session.brand_id)
    )
    brand = result.scalar_one_or_none()
    
    # Get scraped data count by source
    result = await db.execute(
        select(ScrapedData.source_type, func.count(ScrapedData.id))
        .where(ScrapedData.session_id == session_id)
        .group_by(ScrapedData.source_type)
    )
    sources_completed = [row[0] for row in result.all()]
    
    # Check if insights exist
    result = await db.execute(
        select(Insight).where(Insight.session_id == session_id)
    )
    has_insights = result.scalar_one_or_none() is not None
    
    # All possible sources - updated to match what scraper actually uses
    all_sources = [
        "website", "reddit", "twitter", "tiktok", "instagram", "amazon", "google", "trustpilot",
        "youtube", "youtube_comment", "forum", "quora", "linkedin", "medium", "yelp",
        "app_store", "play_store", "other_review", "brand_website", "competitor_comparison"
    ]
    sources_pending = [s for s in all_sources if s not in sources_completed]
    
    # Get real-time phase progress from orchestrator (if running)
    phase_progress = get_phase_progress(session_id)
    
    # Determine current phase and step based on various signals
    progress = 0
    current_step = phase_progress.get("description", "Initializing...")
    current_phase = phase_progress.get("phase", "pending")
    step_number = phase_progress.get("step", 0)
    total_steps = phase_progress.get("total_steps", 0)
    estimated_time = None
    
    if session.status == "completed":
        progress = 100
        current_step = "Research complete!"
        current_phase = "completed"
        estimated_time = 0
        # Clear pending sources when completed - they were either skipped or not applicable
        sources_pending = []
    elif session.status == "failed":
        progress = 0
        current_step = "Research failed"
        current_phase = "failed"
    elif session.status == "in_progress":
        # PRIORITY 1: Use real-time phase progress from orchestrator if available
        if phase_progress.get("updated_at") is not None:
            # We have live progress data from _update_progress calls
            current_step = phase_progress.get("description", "Processing...")
            current_phase = phase_progress.get("phase", "processing")
            step_number = phase_progress.get("step", 0)
            total_steps = phase_progress.get("total_steps", 0)
            
            # Calculate progress based on phase — weights reflect real durations
            # Real observed: Brand DNA+Discovery ~2min, Scraping ~12min, Ad Library ~12min, Rest ~4min
            phase_progress_map = {
                "brand_dna": 3,
                "discovery": 7,
                "keywords": 10,
                "scraping": 45,     # Scraping is ~40% of total time
                "ad_library": 75,   # Ad Library is another ~40%
                "competitors": 85,
                "insights": 93,
            }
            progress = phase_progress_map.get(current_phase, 50)

            # Adjust within phase based on step
            if total_steps > 0:
                # Get the range for current phase to next phase
                phase_keys = list(phase_progress_map.keys())
                current_idx = phase_keys.index(current_phase) if current_phase in phase_keys else -1
                if current_idx >= 0 and current_idx < len(phase_keys) - 1:
                    next_phase_progress = phase_progress_map[phase_keys[current_idx + 1]]
                    phase_range = next_phase_progress - progress
                else:
                    phase_range = 7
                phase_increment = phase_range * (step_number / total_steps)
                progress = min(progress + phase_increment, 99)

            # Estimate remaining time based on elapsed time and progress
            elapsed_seconds = 0
            if session.started_at:
                from datetime import datetime, timezone
                now = datetime.now()
                started = session.started_at
                if started.tzinfo:
                    now = datetime.now(timezone.utc)
                elapsed_seconds = (now - started).total_seconds()

            if progress > 5 and elapsed_seconds > 30:
                # Extrapolate: if we're X% done in Y seconds, total = Y / (X/100)
                total_estimated = elapsed_seconds / (progress / 100)
                estimated_time = max(30, total_estimated - elapsed_seconds)
            else:
                # Early phase — use fixed estimate of ~25 min total
                estimated_time = max(60, 1500 - elapsed_seconds)
        else:
            # FALLBACK: Use DB state to estimate progress
            has_brand_dna = brand and brand.brand_colors and len(brand.brand_colors) > 0
            has_description = brand and brand.description
            has_queries = session.brand_queries is not None
            has_scraped_data = len(sources_completed) > 0
            
            if not has_brand_dna:
                current_phase = "brand_dna"
                progress = 5
                current_step = "Extracting Brand DNA..."
                estimated_time = 540
            elif not has_description:
                current_phase = "discovery"
                progress = 15
                current_step = "Analyzing your brand identity..."
                estimated_time = 480
            elif not has_queries:
                current_phase = "keywords"
                progress = 20
                current_step = "Generating search queries..."
                estimated_time = 420
            elif not has_scraped_data:
                current_phase = "scraping"
                progress = 25
                current_step = "Starting to scrape sources..."
                estimated_time = 360
            elif len(sources_completed) < 3:
                current_phase = "scraping"
                progress = 25 + int((len(sources_completed) / len(all_sources)) * 35)
                current_step = f"Scraping {sources_pending[0] if sources_pending else 'sources'}..."
                estimated_time = 300 - (len(sources_completed) * 30)
            elif not has_insights:
                scrape_progress = len(sources_completed) / len(all_sources)
                if scrape_progress < 0.8:
                    current_phase = "ad_library"
                    progress = 60
                    current_step = "Analyzing ad library..."
                    estimated_time = 180
                elif scrape_progress < 1.0:
                    current_phase = "competitors"
                    progress = 75
                    current_step = "Analyzing competitors..."
                    estimated_time = 120
                else:
                    current_phase = "insights"
                    progress = 90
                    current_step = "Generating insights..."
                    estimated_time = 60
            else:
                current_phase = "completed"
                progress = 100
                current_step = "Finalizing..."
                estimated_time = 10
    
    
    return ResearchProgress(
        session_id=session_id,
        status=session.status,
        current_step=current_step,
        current_phase=current_phase,
        progress_percent=int(progress),
        sources_completed=sources_completed,
        sources_pending=sources_pending,
        estimated_time_remaining=int(estimated_time) if estimated_time is not None else None
    )


@router.get("/session/{session_id}/data", response_model=List[ScrapedDataResponse])
async def get_session_data(
    session_id: int,
    source_type: Optional[str] = None,
    track: Optional[int] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get scraped data for a session."""
    query = select(ScrapedData).where(ScrapedData.session_id == session_id)
    
    if source_type:
        query = query.where(ScrapedData.source_type == source_type)
    if track:
        query = query.where(ScrapedData.track == track)
    
    query = query.limit(limit)
    
    result = await db.execute(query)
    data = result.scalars().all()
    
    return data


@router.get("/session/{session_id}/insights", response_model=InsightResponse)
async def get_session_insights(
    session_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get generated insights for a session."""
    result = await db.execute(
        select(Insight).where(Insight.session_id == session_id)
    )
    insight = result.scalar_one_or_none()
    
    if not insight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No insights found for session {session_id}"
        )
    
    return insight


class RegenerateCTPRequest(BaseModel):
    ctp_id: str


@router.post("/session/{session_id}/regenerate-ctp")
async def regenerate_single_ctp(
    session_id: int,
    payload: RegenerateCTPRequest,
    db: AsyncSession = Depends(get_db),
):
    """Re-run ONLY the deep enrichment step for a single CTP.

    Reuses the existing CTP's representative_snippets + general_stance + name
    as the seed (skipping discovery). The LLM is given the same brand context
    and a fresh chance to refine the deep fields. The CTP slot is replaced
    in-place at its current position in insight.ctp_data.
    """
    from .. import models  # local import to avoid circulars
    from ..services.brand_context import (
        build_brand_context,
        render_context_block,
        render_snippets_block,
    )
    from ..services.ctp_builder import CTPBuilder

    insight = (await db.execute(
        select(Insight).where(Insight.session_id == session_id)
    )).scalar_one_or_none()
    if not insight:
        raise HTTPException(404, f"No insights for session {session_id}")

    ctps = list(insight.ctp_data or [])
    target_idx = next((i for i, c in enumerate(ctps) if c.get("ctp_id") == payload.ctp_id), None)
    if target_idx is None:
        raise HTTPException(404, f"CTP {payload.ctp_id} not found in session {session_id}")

    ctp = ctps[target_idx]
    rep_snippets = ctp.get("representative_snippets") or []
    if not rep_snippets:
        raise HTTPException(400, f"CTP {payload.ctp_id} has no representative_snippets to regenerate from")

    # Resolve brand
    rs = (await db.execute(
        select(ResearchSession).where(ResearchSession.id == session_id)
    )).scalar_one_or_none()
    if not rs:
        raise HTTPException(404, f"Session {session_id} not found")
    brand = (await db.execute(
        select(models.Brand).where(models.Brand.id == rs.brand_id)
    )).scalar_one_or_none()
    if not brand:
        raise HTTPException(404, f"Brand for session {session_id} not found")

    # Re-build the brand_context_block (same shape the orchestrator uses)
    insights_so_far = {
        "market_pain_points": insight.market_pain_points or [],
        "value_props": insight.value_props or [],
        "customer_desires": insight.customer_desires or [],
        "purchase_triggers": insight.purchase_triggers or [],
        "objections": insight.objections or [],
        "decision_factors": insight.decision_factors or [],
        "messaging_angles": insight.messaging_angles or [],
        "verbatim_quotes": insight.verbatim_quotes or [],
        "customer_language": insight.customer_language or [],
        "tone_emotions": insight.tone_emotions or [],
        "trending_topics": insight.trending_topics or [],
        "competitor_analysis": insight.competitor_analysis,
        "competitors_mentioned": insight.competitors_mentioned or [],
        "recommended_hooks": insight.recommended_hooks or [],
        "hooks_library": insight.hooks_library,
    }
    ctx = build_brand_context(
        brand=brand,
        insights_so_far=insights_so_far,
        snippets=rep_snippets,  # at minimum, use the CTP's snippets — keeps prompt focused
        ad_library_data=insight.ad_library_data,
        ad_creative_patterns=insight.ad_creative_patterns,
    )
    brand_block = render_context_block(ctx)

    # Build the archetype seed dict from the saved CTP fields. Preserve
    # evidence_quotes from the original discovery — they're trail back to
    # the source data and we don't want to lose them on regeneration.
    archetype = {
        "name": ctp.get("ctp_name") or "",
        "psychology": ctp.get("archetype_psychology") or ctp.get("core_insight_general") or "",
        "behavioral_markers": ctp.get("behavioral_markers") or [],
        "counter_segment": ctp.get("counter_segment") or "",
        "what_makes_them_unique": ctp.get("what_makes_them_unique") or "",
        "stance_tags": ctp.get("stance_tags") or ([ctp.get("general_stance")] if ctp.get("general_stance") else []),
        "evidence_quotes": ctp.get("evidence_quotes") or [],
    }

    # Hook + value-prop pools
    hook_pool: List[str] = []
    for v in (insight.recommended_hooks or []):
        if v and str(v) not in hook_pool:
            hook_pool.append(str(v))
    hl = insight.hooks_library
    if isinstance(hl, list):
        for v in hl:
            if v and str(v) not in hook_pool:
                hook_pool.append(str(v))
    elif isinstance(hl, dict):
        for v in (hl.get("hooks") or []):
            if v and str(v) not in hook_pool:
                hook_pool.append(str(v))
    value_props_pool = [str(v) for v in (insight.value_props or []) if v]

    builder = CTPBuilder()
    builder._current_brand_name = brand.name

    deep = await builder.deep_enrich_archetype(
        archetype=archetype,
        attributed_snippets=rep_snippets,
        brand_name=brand.name,
        brand_block=brand_block,
        ads_for_archetype_block="(ads not re-aligned for single-CTP regeneration)",
        hook_pool=hook_pool,
        value_props_pool=value_props_pool,
    )
    if not deep:
        raise HTTPException(502, "Deep enrichment LLM call failed")

    # Re-assemble. The original total_snippets is unknown here — preserve the
    # existing review_percentage/weight so we don't accidentally renormalize.
    fake_total = max(1, ctp.get("snippet_count") or 1)
    rebuilt = builder._assemble_ctp_from_discovery(
        ctp_num=int(ctp.get("ctp_id", "CTP-01").replace("CTP-", "")) or (target_idx + 1),
        archetype=archetype,
        deep=deep,
        attributed_snippets=rep_snippets,
        total_snippets=fake_total,
    )
    rebuilt_dict = rebuilt.to_dict()
    # Preserve metrics that were valid at original-discovery time
    rebuilt_dict["weight"] = ctp.get("weight", rebuilt_dict.get("weight"))
    rebuilt_dict["review_percentage"] = ctp.get("review_percentage", rebuilt_dict.get("review_percentage"))
    rebuilt_dict["snippet_count"] = ctp.get("snippet_count", rebuilt_dict.get("snippet_count"))
    rebuilt_dict["ctp_id"] = ctp.get("ctp_id")
    # If the LLM kept the same name, keep the original; if it refined, accept the refinement
    if not rebuilt_dict.get("ctp_name"):
        rebuilt_dict["ctp_name"] = ctp.get("ctp_name")

    ctps[target_idx] = rebuilt_dict
    insight.ctp_data = ctps
    await db.commit()

    return {"ok": True, "ctp_id": payload.ctp_id, "ctp_name": rebuilt_dict.get("ctp_name")}


@router.get("/session/{session_id}/full", response_model=FullResearchResult)
async def get_full_research_result(
    session_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get complete research results including brand, data, and insights."""
    # Get session
    result = await db.execute(
        select(ResearchSession).where(ResearchSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with id {session_id} not found"
        )
    
    # Get brand
    result = await db.execute(
        select(Brand).where(Brand.id == session.brand_id)
    )
    brand = result.scalar_one_or_none()
    
    # Get scraped data count
    result = await db.execute(
        select(func.count(ScrapedData.id))
        .where(ScrapedData.session_id == session_id)
    )
    total_count = result.scalar()
    
    # Get count by source
    result = await db.execute(
        select(ScrapedData.source_type, func.count(ScrapedData.id))
        .where(ScrapedData.session_id == session_id)
        .group_by(ScrapedData.source_type)
    )
    by_source = {row[0]: row[1] for row in result.all()}
    
    # Get insights
    result = await db.execute(
        select(Insight).where(Insight.session_id == session_id)
    )
    insight = result.scalar_one_or_none()
    
    return FullResearchResult(
        brand=brand,
        session=session,
        scraped_data_count=total_count,
        scraped_data_by_source=by_source,
        insights=insight
    )


@router.get("/sessions")
async def list_all_sessions(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """List all research sessions with brand info, most recent first."""
    from ..models import Brand
    
    result = await db.execute(
        select(ResearchSession, Brand.name)
        .join(Brand, ResearchSession.brand_id == Brand.id)
        .order_by(ResearchSession.started_at.desc())
        .limit(limit)
    )
    rows = result.all()
    
    sessions = []
    for session, brand_name in rows:
        sessions.append({
            "id": session.id,
            "brand_id": session.brand_id,
            "brand_name": brand_name,
            "status": session.status,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None
        })
    
    return sessions


@router.get("/brand/{brand_id}/sessions", response_model=List[ResearchSessionResponse])
async def list_brand_sessions(
    brand_id: int,
    db: AsyncSession = Depends(get_db)
):
    """List all research sessions for a brand."""
    result = await db.execute(
        select(ResearchSession)
        .where(ResearchSession.brand_id == brand_id)
        .order_by(ResearchSession.started_at.desc())
    )
    sessions = result.scalars().all()
    return sessions


@router.get("/session/{session_id}/logs")
async def get_logs_for_session(
    session_id: int,
    since: Optional[str] = Query(None, description="ISO timestamp to get logs since"),
    limit: int = Query(100, ge=1, le=500)
):
    """
    Get real-time logs for a research session.
    Used by frontend LogsPanel for live progress updates.
    """
    logs = get_session_logs(session_id)
    
    # Filter by timestamp if 'since' is provided
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            logs = [log for log in logs if datetime.fromisoformat(log["timestamp"]) > since_dt]
        except (ValueError, TypeError):
            pass  # Ignore invalid timestamp format
    
    # Return most recent logs up to limit
    return {
        "session_id": session_id,
        "logs": logs[-limit:],
        "total_count": len(get_session_logs(session_id))
    }


# =============================================
# SENTIMENT ANALYSIS ENDPOINT
# =============================================

@router.get("/session/{session_id}/sentiment")
async def get_sentiment_analysis(
    session_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregated sentiment analysis by source for a session.
    Returns per-source breakdown with RoBERTa scores + top verbatims.
    """
    from collections import defaultdict
    
    result = await db.execute(
        select(ScrapedData)
        .where(ScrapedData.session_id == session_id)
    )
    items = result.scalars().all()
    
    if not items:
        return {"session_id": session_id, "total": 0, "by_source": {}, "top_positive": [], "top_negative": []}
    
    by_source = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0, "total": 0, "avg_score": 0.0, "sum_score": 0.0})
    overall = {"positive": 0, "negative": 0, "neutral": 0}
    all_items_scored = []
    
    for item in items:
        src = item.source_type or "unknown"
        sentiment = item.sentiment or "neutral"
        score = item.sentiment_score or 0.0
        
        if sentiment in overall:
            overall[sentiment] += 1
        by_source[src][sentiment] += 1
        by_source[src]["total"] += 1
        by_source[src]["sum_score"] += score
        
        if item.content and len(item.content.strip()) > 20:
            all_items_scored.append({
                "content": item.content[:300],
                "source": src,
                "sentiment": sentiment,
                "score": score,
                "author": item.author,
                "title": item.title,
            })
    
    # Calculate averages
    source_data = {}
    for src, stats in by_source.items():
        stats["avg_score"] = round(stats["sum_score"] / max(stats["total"], 1), 3)
        del stats["sum_score"]
        source_data[src] = dict(stats)
    
    # Top positive and negative verbatims
    sorted_positive = sorted([i for i in all_items_scored if i["score"] > 0], key=lambda x: -x["score"])
    sorted_negative = sorted([i for i in all_items_scored if i["score"] < 0], key=lambda x: x["score"])
    
    # Detect which sentiment model is actually available
    try:
        from ..services.sentiment import is_roberta_available
        model_used = "roberta" if is_roberta_available() else "keyword"
    except Exception:
        model_used = "unknown"
    
    total = sum(overall.values())
    return {
        "session_id": session_id,
        "total": total,
        "overall": overall,
        "overall_pct": {k: round(v / max(total, 1) * 100, 1) for k, v in overall.items()},
        "by_source": source_data,
        "top_positive": sorted_positive[:10],
        "top_negative": sorted_negative[:10],
        "model": model_used
    }


# =============================================
# GENERATE MORE SCRIPTS ENDPOINT
# =============================================

@router.post("/session/{session_id}/generate-scripts")
async def generate_more_scripts(
    session_id: int,
    count: int = Query(3, ge=1, le=10, description="Number of scripts to generate"),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate additional ad scripts for an existing session.
    New scripts are APPENDED to the existing scripts list.
    """
    # Get session and insight
    result = await db.execute(
        select(ResearchSession).where(ResearchSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with id {session_id} not found"
        )
    
    result = await db.execute(
        select(Insight).where(Insight.session_id == session_id)
    )
    insight = result.scalar_one_or_none()
    
    if not insight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No insights found for this session"
        )
    
    # Get brand info
    result = await db.execute(
        select(Brand).where(Brand.id == session.brand_id)
    )
    brand = result.scalar_one_or_none()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )
    
    # Prepare brand info for script generator
    brand_info = {
        "name": brand.name,
        "sector": brand.sector,
        "vertical": brand.vertical,
        "products": brand.products or [],
        "target_audience": brand.target_audience or "",
        "value_propositions": [],
        "brand_values": brand.brand_values or [],
        "tone_of_voice": brand.tone_of_voice or []
    }
    
    # Get ad patterns from insight
    ad_patterns = insight.ad_creative_patterns or {}
    
    # Prepare insights dict from insight record - FULL DATA for rich scripts
    insights_dict = {
        # Core Creative Dimensions
        "icps": insight.icps or [],
        "pain_points": insight.pain_points or [],
        "value_props": insight.value_props or [],
        "messaging_angles": insight.messaging_angles or [],
        "verbatim_quotes": insight.verbatim_quotes or [],
        "objections": insight.objections or [],
        "purchase_triggers": insight.purchase_triggers or [],
        "recommended_hooks": insight.recommended_hooks or [],
        
        # Customer Language & Desires (from Track 2 segment research)
        "customer_language": insight.customer_language or [],
        "customer_desires": insight.customer_desires or [],
        
        # TikTok Analysis (trending patterns + segment analysis)
        "tiktok_trends": insight.tiktok_trends or {},
        
        # Instagram Brand Presence (voice, aesthetic, pillars)
        "instagram_brand_presence": insight.instagram_brand_presence or {},
        
        # Hooks Library (structured hooks for creative briefs)
        "hooks_library": insight.hooks_library or {},
        
        # Top Quotes & Data Summary
        "top_quotes": insight.top_quotes or [],
        "data_by_topic": insight.data_by_topic or {},
        
        # Proto-ICPs (clustered ICP candidates)
        "proto_icps": insight.proto_icps or [],
        "proto_icp_recommendations": insight.proto_icp_recommendations or [],
    }
    
    # Generate new scripts
    from ..services.generators import ScriptGenerator
    script_generator = ScriptGenerator()
    
    try:
        new_scripts = await script_generator.generate_scripts(
            brand_info=brand_info,
            ad_patterns=ad_patterns,
            insights=insights_dict,
            num_scripts=count
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate scripts: {str(e)}"
        )
    
    # Append to existing scripts
    existing_scripts = insight.generated_scripts or []
    updated_scripts = existing_scripts + new_scripts
    insight.generated_scripts = updated_scripts
    
    await db.commit()
    
    return {
        "message": f"Generated {len(new_scripts)} new scripts",
        "session_id": session_id,
        "new_scripts_count": len(new_scripts),
        "total_scripts_count": len(updated_scripts),
        "new_scripts": new_scripts
    }


# =============================================
# API METRICS AND HEALTH CHECK ENDPOINTS
# =============================================

@router.get("/metrics")
async def get_api_metrics():
    """
    Get API usage metrics for the current/last session.
    Shows Gemini Vision, Firecrawl, Apify usage and estimated costs.
    """
    from ..utils.api_metrics import get_summary, get_metrics
    
    return {
        "summary": get_summary(),
        "details": get_metrics()
    }


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    System health check - verifies all services are accessible.
    """
    from ..config import settings
    
    health = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {}
    }
    
    # Check database
    try:
        result = await db.execute(select(func.count()).select_from(Brand))
        count = result.scalar()
        health["services"]["database"] = {"status": "ok", "brands_count": count}
    except Exception as e:
        health["services"]["database"] = {"status": "error", "error": str(e)[:100]}
        health["status"] = "degraded"
    
    # Check Gemini API key
    if settings.GEMINI_API_KEY:
        health["services"]["gemini"] = {"status": "configured", "key_present": True}
    else:
        health["services"]["gemini"] = {"status": "missing", "key_present": False}
        health["status"] = "degraded"
    
    # Check Firecrawl API key
    if settings.FIRECRAWL_API_KEY:
        health["services"]["firecrawl"] = {"status": "configured", "key_present": True}
    else:
        health["services"]["firecrawl"] = {"status": "missing", "key_present": False}
        health["status"] = "degraded"
    
    # Check Apify API key
    if settings.APIFY_API_KEY:
        health["services"]["apify"] = {"status": "configured", "key_present": True}
    else:
        health["services"]["apify"] = {"status": "missing", "key_present": False}
    
    # Queue status
    health["queue"] = get_queue_status()
    
    return health


# =============================================
# EXPORT ENDPOINT
# =============================================

@router.get("/session/{session_id}/export")
async def export_session_report(
    session_id: int,
    format: str = "full",
    db: AsyncSession = Depends(get_db)
):
    """
    Export brand intelligence report as markdown.

    Query params:
        format: "full" (default 21-section report), "raw_reviews" (Output 1),
                "ctp" (Output 2: CTP structures), "hypothesis" (Output 3: ad strategy)
    """
    from fastapi.responses import Response
    from ..services.brand_export import build_export
    from ..services.ctp_export import build_raw_reviews_export, build_ctp_export, build_hypothesis_export
    from ..services.excel_database_export import build_rsw_database_export

    # Get session with insights
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(ResearchSession)
        .options(selectinload(ResearchSession.insights))
        .where(ResearchSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    # Get brand
    result = await db.execute(
        select(Brand).where(Brand.id == session.brand_id)
    )
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    # Get insight (not needed for raw_reviews but needed for ctp/hypothesis/full)
    insight = None
    if session.insights:
        insight = session.insights[-1] if isinstance(session.insights, list) else session.insights

    if format not in ("raw_reviews", "rsw_database") and not insight:
        raise HTTPException(status_code=404, detail="No insights for this session")

    # Get scraped data
    scraped_result = await db.execute(
        select(ScrapedData)
        .where(ScrapedData.session_id == session_id)
        .order_by(ScrapedData.relevance_score.desc().nullslast(), ScrapedData.scraped_at.desc())
    )
    scraped_data = list(scraped_result.scalars().all())

    safe_name = brand.name.lower().replace(' ', '-')

    # Route to the appropriate export renderer
    if format == "raw_reviews":
        md = build_raw_reviews_export(brand, scraped_data)
        filename = f"{safe_name}-raw-reviews.md"
    elif format == "ctp":
        md = build_ctp_export(brand, insight, scraped_data)
        filename = f"{safe_name}-ctp-personas.md"
    elif format == "hypothesis":
        md = build_hypothesis_export(brand, insight, scraped_data)
        filename = f"{safe_name}-hypothesis-layer.md"
    elif format == "rsw_database":
        xlsx_bytes = build_rsw_database_export(brand, insight, scraped_data)
        filename = f"{safe_name}-rsw-database.xlsx"
        return Response(
            content=xlsx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    else:  # "full" or any other value
        md = build_export(brand, insight, scraped_data)
        filename = f"{safe_name}-research-export.md"

    return Response(
        content=md,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


# =============================================
# VIDEO SERVING ENDPOINT
# =============================================

@router.get("/videos/{video_path:path}")
async def serve_video(video_path: str):
    """
    Serve downloaded videos from the output directory.
    Used by frontend video player.
    """
    from fastapi.responses import FileResponse
    from pathlib import Path
    
    # Security: only allow serving from output directory
    base_dir = Path("output").resolve()
    
    try:
        full_path = (base_dir / video_path).resolve()
        
        # Security: strict path traversal check (case-insensitive safe)
        try:
            full_path.relative_to(base_dir)
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied")
        
        if not full_path.exists():
            raise HTTPException(status_code=404, detail="Video not found")
        
        return FileResponse(
            path=str(full_path),
            media_type="video/mp4",
            filename=full_path.name
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Video not found: {e}")


# =============================================
# IMAGE PROXY ENDPOINT (for Ad Library thumbnails)
# =============================================

# Allowed domains for image proxying (SSRF protection)
_ALLOWED_IMAGE_DOMAINS = {
    "scontent.fbcdn.net", "scontent-eze1-1.xx.fbcdn.net",
    "external.fbcdn.net", "platform-lookaside.fbcdn.net",
    "scontent.cdninstagram.com", "instagram.fbcdn.net",
    "p16-sign.tiktokcdn.com", "p16-sign-sg.tiktokcdn.com",
    "p77-sign.tiktokcdn.com",
    "pbs.twimg.com", "abs.twimg.com",
    "i.redd.it", "preview.redd.it",
    "m.media-amazon.com", "images-na.ssl-images-amazon.com",
}

def _is_allowed_image_url(url: str) -> bool:
    """Check if URL is from an allowed domain (SSRF protection)."""
    from urllib.parse import urlparse
    import ipaddress
    
    try:
        parsed = urlparse(url)
        
        # Must be HTTPS or HTTP
        if parsed.scheme not in ("http", "https"):
            return False
        
        hostname = parsed.hostname or ""
        
        # Block private/internal IPs
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                return False
        except ValueError:
            pass  # Not an IP, it's a hostname — check domain
        
        # Check against allowed domains (exact or subdomain match)
        for domain in _ALLOWED_IMAGE_DOMAINS:
            if hostname == domain or hostname.endswith("." + domain):
                return True
        
        # Also allow any *.fbcdn.net or *.tiktokcdn.com subdomain
        if hostname.endswith(".fbcdn.net") or hostname.endswith(".tiktokcdn.com"):
            return True
        
        return False
    except Exception:
        return False


@router.get("/proxy-image")
async def proxy_image(url: str = Query(..., description="URL of image to proxy")):
    """
    Proxy external images to avoid CORS issues and cache locally.
    Used for Ad Library thumbnails from Facebook.
    Only allows requests to whitelisted image CDN domains.
    """
    import httpx
    import hashlib
    from fastapi.responses import Response
    from pathlib import Path
    
    # SSRF protection: validate URL against whitelist
    if not _is_allowed_image_url(url):
        raise HTTPException(
            status_code=403, 
            detail="URL domain not allowed. Only supported image CDN domains are accepted."
        )
    
    # Create cache directory
    cache_dir = Path("output/image_cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Create hash of URL for filename (SHA-256 instead of MD5)
    url_hash = hashlib.sha256(url.encode()).hexdigest()[:32]
    
    # Check common extensions or default to jpg
    ext = ".jpg"
    if ".png" in url.lower():
        ext = ".png"
    elif ".gif" in url.lower():
        ext = ".gif"
    elif ".webp" in url.lower():
        ext = ".webp"
    
    cache_path = cache_dir / f"{url_hash}{ext}"
    
    # Check cache first
    if cache_path.exists():
        with open(cache_path, "rb") as f:
            content = f.read()
        media_type = f"image/{ext[1:]}" if ext != ".jpg" else "image/jpeg"
        return Response(content=content, media_type=media_type)
    
    # Otherwise fetch and cache
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            
            if response.status_code == 200:
                # Save to cache
                with open(cache_path, "wb") as f:
                    f.write(response.content)
                
                content_type = response.headers.get("content-type", "image/jpeg")
                return Response(content=response.content, media_type=content_type)
            else:
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch image")
    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(status_code=408, detail="Image request timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to proxy image: {str(e)}")


# =============================================
# INTAKE ENGINE ENDPOINTS (per brief)
# =============================================

@router.post("/classify-snippets/{session_id}")
async def classify_snippets(
    session_id: int,
    max_snippets: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Classify unclassified snippets for a session.
    Adds: primary_trigger, blocker_type, desired_outcome_level, proof_type_trusted.
    """
    from ..services.snippet_classifier import classify_session_snippets
    
    try:
        classified_count = await classify_session_snippets(session_id, db)
        return {
            "status": "success",
            "session_id": session_id,
            "snippets_classified": classified_count
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/proto-icps/{session_id}")
async def get_proto_icps(
    session_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get Proto-ICP clusters for a session.
    Groups snippets by Trigger × Blocker and recommends top 3 ICPs.
    """
    from ..services.proto_icp_clusterer import generate_proto_icp_report
    
    # Get classified snippets
    result = await db.execute(
        select(ScrapedData)
        .where(ScrapedData.session_id == session_id)
        .where(ScrapedData.primary_trigger.isnot(None))
    )
    snippets = result.scalars().all()
    
    # Convert to dicts
    snippet_dicts = [
        {
            "id": s.id,
            "content": s.content,
            "source_type": s.source_type,
            "source_url": s.source_url,
            "primary_trigger": s.primary_trigger,
            "blocker_type": s.blocker_type,
            "desired_outcome_level": s.desired_outcome_level,
            "proof_type_trusted": s.proof_type_trusted,
            "language_cues": s.language_cues,
            "language": s.language,
            "classification_confidence": s.classification_confidence
        }
        for s in snippets
    ]
    
    report = generate_proto_icp_report(snippet_dicts)
    report["session_id"] = session_id
    
    return report


@router.get("/intake-report/{session_id}")
async def get_intake_report(
    session_id: int,
    format: str = "json",
    db: AsyncSession = Depends(get_db)
):
    """
    Generate full Intake Report per brief.
    Includes: Brand Intake Record, Evidence Snippets, Proto-ICP Clusters, Recommendations.
    
    Args:
        format: 'json' or 'markdown'
    """
    from ..services.proto_icp_clusterer import generate_proto_icp_report
    
    # Get session with brand
    result = await db.execute(
        select(ResearchSession).where(ResearchSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get brand
    result = await db.execute(
        select(Brand).where(Brand.id == session.brand_id)
    )
    brand = result.scalar_one_or_none()
    
    # Get all snippets
    result = await db.execute(
        select(ScrapedData).where(ScrapedData.session_id == session_id)
    )
    all_snippets = result.scalars().all()
    
    # Get classified snippets
    classified_snippets = [s for s in all_snippets if s.primary_trigger]
    
    # Build snippet dicts for clustering
    snippet_dicts = [
        {
            "id": s.id,
            "content": s.content,
            "source_type": s.source_type,
            "source_url": s.source_url,
            "primary_trigger": s.primary_trigger,
            "blocker_type": s.blocker_type,
            "desired_outcome_level": s.desired_outcome_level,
            "proof_type_trusted": s.proof_type_trusted,
            "language_cues": s.language_cues,
            "language": s.language,
            "classification_confidence": s.classification_confidence,
            "title": s.title,
            "posted_at": s.posted_at.isoformat() if s.posted_at else None
        }
        for s in classified_snippets
    ]
    
    # Generate Proto-ICP report
    proto_icp_report = generate_proto_icp_report(snippet_dicts)
    
    # Build full report
    report = {
        "output_a_brand_intake": {
            "brand_name": brand.name if brand else "Unknown",
            "website_url": brand.website_url if brand else None,
            "brand_identity": {
                "colors": brand.brand_colors if brand else None,
                "fonts": brand.fonts if brand else None,
                "logo_url": brand.logo_url if brand else None
            },
            "tone_of_voice": brand.tone_of_voice if brand else None,
            "product_list": brand.products if brand else None,
            "competitors": brand.description if brand else None,  # TODO: extract from scraped data
            "validation_level": 1  # Scraped
        },
        "output_b_evidence_snippets": {
            "total_snippets": len(all_snippets),
            "classified_snippets": len(classified_snippets),
            "classification_coverage_pct": round(len(classified_snippets) / len(all_snippets) * 100, 1) if all_snippets else 0,
            "by_source": {},
            "by_trigger": {},
            "by_blocker": {}
        },
        "output_c_proto_icp_clusters": proto_icp_report.get("cluster_summary", {}),
        "output_d_recommended_icps": proto_icp_report.get("recommended_icps", [])
    }
    
    # Count by source
    for s in all_snippets:
        source = s.source_type or "unknown"
        report["output_b_evidence_snippets"]["by_source"][source] = \
            report["output_b_evidence_snippets"]["by_source"].get(source, 0) + 1
    
    # Count by trigger/blocker
    for s in classified_snippets:
        trigger = s.primary_trigger or "unknown"
        blocker = s.blocker_type or "none"
        report["output_b_evidence_snippets"]["by_trigger"][trigger] = \
            report["output_b_evidence_snippets"]["by_trigger"].get(trigger, 0) + 1
        report["output_b_evidence_snippets"]["by_blocker"][blocker] = \
            report["output_b_evidence_snippets"]["by_blocker"].get(blocker, 0) + 1
    
    if format == "markdown":
        return {"markdown": _generate_markdown_report(report)}
    
    return report


def _generate_markdown_report(report: Dict[str, Any]) -> str:
    """Generate Markdown version of intake report."""
    md = []
    
    # Header
    brand = report["output_a_brand_intake"]
    md.append(f"# Intake Report: {brand['brand_name']}")
    md.append(f"\n**Website:** {brand['website_url'] or 'N/A'}")
    md.append(f"\n**Validation Level:** 1 (Scraped)")
    md.append("\n---\n")
    
    # Output A
    md.append("## Output A: Brand Intake Record\n")
    if brand["tone_of_voice"]:
        md.append(f"**Tone of Voice:** {', '.join(brand['tone_of_voice']) if isinstance(brand['tone_of_voice'], list) else brand['tone_of_voice']}\n")
    if brand["product_list"]:
        md.append("**Products:**")
        for p in brand["product_list"][:5]:
            if isinstance(p, dict):
                md.append(f"- {p.get('name', 'Unknown')}: {p.get('description', '')[:100]}")
            else:
                md.append(f"- {p}")
    md.append("\n---\n")
    
    # Output B
    snippets = report["output_b_evidence_snippets"]
    md.append("## Output B: Evidence Snippets\n")
    md.append(f"**Total Snippets:** {snippets['total_snippets']}")
    md.append(f"\n**Classified:** {snippets['classified_snippets']} ({snippets['classification_coverage_pct']}%)\n")
    md.append("\n### By Source:")
    for source, count in sorted(snippets["by_source"].items(), key=lambda x: x[1], reverse=True):
        md.append(f"- {source}: {count}")
    md.append("\n### By Trigger:")
    for trigger, count in sorted(snippets["by_trigger"].items(), key=lambda x: x[1], reverse=True)[:10]:
        md.append(f"- {trigger}: {count}")
    md.append("\n---\n")
    
    # Output C
    clusters = report["output_c_proto_icp_clusters"]
    md.append("## Output C: Proto-ICP Clusters\n")
    md.append(f"**Total Clusters:** {clusters.get('total_clusters', 0)}\n")
    for cluster in clusters.get("clusters", [])[:5]:
        md.append(f"\n### {cluster['cluster_id']}: {cluster['trigger_label']} × {cluster['blocker_label']}")
        md.append(f"- Snippets: {cluster['snippet_count']}")
        md.append(f"- Top phrases: {', '.join(cluster['top_language_cues'][:3])}")
    md.append("\n---\n")
    
    # Output D
    icps = report["output_d_recommended_icps"]
    md.append("## Output D: Recommended ICPs\n")
    for icp in icps:
        md.append(f"\n### #{icp['rank']}: {icp['trigger']} × {icp['blocker']}")
        md.append(f"**Score:** {icp['score']}")
        md.append(f"\n**Rationale:** {icp['rationale']}")
        md.append(f"\n**Risks:** {', '.join(icp['risks'])}")
        md.append(f"\n**Top Phrases:** {', '.join(icp['top_phrases'][:3])}")
    
    return "\n".join(md)


# =============================================
# SESSION MANAGEMENT ENDPOINTS
# =============================================

@router.post("/cancel/{session_id}")
async def cancel_session(
    session_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel a stuck research session and mark it as 'cancelled'.
    Use this when a session is stuck in 'in_progress' but there's no active worker.
    """
    result = await db.execute(
        select(ResearchSession).where(ResearchSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with id {session_id} not found"
        )
    
    if session.status in ["completed", "cancelled"]:
        return {
            "message": f"Session already in {session.status} state",
            "session_id": session_id,
            "status": session.status
        }
    
    old_status = session.status
    session.status = "cancelled"
    await db.commit()
    
    # Clear any lingering session logs
    clear_session_logs(session_id)
    
    return {
        "message": f"Session cancelled successfully",
        "session_id": session_id,
        "old_status": old_status,
        "new_status": "cancelled"
    }


@router.post("/cancel-all-stuck")
async def cancel_all_stuck_sessions(
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel all sessions that have been 'in_progress' for more than 30 minutes.
    These are likely stuck due to server restart or worker failure.
    """
    from datetime import timedelta
    
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=30)
    
    result = await db.execute(
        select(ResearchSession).where(
            ResearchSession.status == "in_progress",
            ResearchSession.started_at < cutoff
        )
    )
    stuck_sessions = result.scalars().all()
    
    cancelled_ids = []
    for session in stuck_sessions:
        session.status = "cancelled"
        cancelled_ids.append(session.id)
        clear_session_logs(session.id)
    
    await db.commit()
    
    return {
        "message": f"Cancelled {len(cancelled_ids)} stuck sessions",
        "cancelled_session_ids": cancelled_ids
    }
