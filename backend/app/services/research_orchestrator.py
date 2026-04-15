"""
Research Orchestrator - Coordinates the full research pipeline.
Enhanced with Ad Library Intelligence, Competitor Analysis, and Generators.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime, date, timezone
from typing import Dict, List, Any, Optional
import asyncio
import httpx
import json

from ..models import Brand, ResearchSession, ScrapedData, Insight
from .brand_discovery import BrandDiscoveryService
from .brand_dna import BrandDNAExtractor
from .keyword_generator import KeywordGeneratorService
from .scrapers.firecrawl import FirecrawlScraper
from .scrapers.apify import ApifyScraper
from .scrapers.social_free import SocialFreeScraper
from .insights import InsightsGeneratorService
from .adlibrary import AdLibraryScraper, AdAnalyzer
from .adlibrary.scraper import extract_ig_handle, extract_fb_handle
from .landing_pages import LandingPageAnalyzer
from .competitors import CompetitorAnalyzer
from .generators import ScriptGenerator, ThumbnailSuggester, ABTestSuggester
from .social_media_analyzer import SocialMediaAnalyzer
from .youtube_analyzer import YouTubeAnalyzer
from .twitter_analyzer import TwitterAnalyzer
from .reddit_analyzer import RedditAnalyzer
from .review_analyzer import ReviewAnalyzer
from .cross_source_analyzer import CrossSourceAnalyzer
from .social_video_analyzer import SocialVideoAnalyzer
from .sentiment import classify_sentiment, get_sentiment_analyzer
from .snippet_classifier import SnippetClassifier
from .proto_icp_builder import ProtoICPBuilder, build_proto_icps
from .stance_classifier import StanceClassifier
from .ctp_builder import build_ctps
from .kb_exporter import get_kb_exporter
from .anythingllm import sync_brand_to_workspace
from .knowledge_synthesizer import get_knowledge_synthesizer
from .brand_extractor import BrandExtractor, get_brand_extractor
from .tiktok_trends import get_tiktok_trends_service
from .tiktok_segment_analyzer import get_tiktok_segment_analyzer
from .instagram_brand_analyzer import get_instagram_brand_analyzer
from .hooks_library import get_hooks_library_service
from ..config import settings

# Import session logging from utils (not routers to avoid circular import)
from ..utils.session_logging import add_session_log, set_phase_progress

# Import persistent file logging
from .logging_service import (
    get_logger, log_research_start, log_scrape_result, 
    log_analysis_result, log_error, log_ad_library_result,
    log_video_analysis, log_session_complete
)


def _sanitize_for_json(obj: Any) -> Any:
    """
    Recursively convert datetime objects to ISO strings for JSON serialization.
    This fixes the 'Object of type datetime is not JSON serializable' error.
    """
    if obj is None:
        return None
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(item) for item in obj]
    if isinstance(obj, tuple):
        return tuple(_sanitize_for_json(item) for item in obj)
    return obj


# Valid fields for ScrapedData model
SCRAPED_DATA_FIELDS = {
    'session_id', 'source_type', 'source_url', 'track', 'title', 'content',
    'author', 'posted_at', 'likes', 'comments_count', 'shares', 'rating',
    'mention_type', 'sentiment', 'sentiment_score', 'relevance_score',
    'detected_topics', 'video_analysis', 'video_file', 'raw_data'
}


def filter_scraped_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Filter data dict to only include valid ScrapedData fields."""
    return {k: v for k, v in data.items() if k in SCRAPED_DATA_FIELDS}


class ResearchOrchestrator:
    """Orchestrates the complete research pipeline."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.brand_dna_extractor = BrandDNAExtractor()
        self.brand_discovery = BrandDiscoveryService()
        self.keyword_generator = KeywordGeneratorService()
        self.firecrawl = FirecrawlScraper()
        self.apify = ApifyScraper()
        self.insights_generator = InsightsGeneratorService()
        
        # Free social media scraper (simplified, handles failures gracefully)
        self.social_free = SocialFreeScraper()
        
        # New modules
        self.adlib_scraper = AdLibraryScraper()
        self.ad_analyzer = AdAnalyzer()
        self.lp_analyzer = LandingPageAnalyzer()
        self.competitor_analyzer = CompetitorAnalyzer()
        self.script_generator = ScriptGenerator()
        self.thumbnail_suggester = ThumbnailSuggester()
        self.ab_test_suggester = ABTestSuggester()
        self.social_analyzer = SocialMediaAnalyzer()
        self.youtube_analyzer = YouTubeAnalyzer()
        self.twitter_analyzer = TwitterAnalyzer()
        self.reddit_analyzer = RedditAnalyzer()
        self.review_analyzer = ReviewAnalyzer()
        self.cross_source_analyzer = CrossSourceAnalyzer()
        self.social_video_analyzer = SocialVideoAnalyzer()
        self.snippet_classifier = SnippetClassifier()
        self.proto_icp_builder = ProtoICPBuilder()
        self.stance_classifier = StanceClassifier()
        self.brand_extractor = BrandExtractor()
        
        # Progress tracking
        self.current_step = ""
        self.current_phase = ""
        self._session_id = None  # For logging
        self._phase_timers = {}  # Track phase durations
    
    def _log(self, message: str, level: str = "info", source: str = None):
        """Log to both console and session logs with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        # Handle Windows console encoding issues with emojis
        try:
            print(log_message)
        except UnicodeEncodeError:
            # Fallback: remove emojis for Windows console
            safe_msg = log_message.encode('ascii', 'replace').decode('ascii')
            print(safe_msg)
        if self._session_id:
            # Clean message for API (remove ANSI codes, brackets)
            clean_msg = message.replace("[", "").replace("]", "").replace("->", "->").strip()
            add_session_log(self._session_id, clean_msg, level=level, source=source)
    
    def _log_phase_start(self, phase_name: str, description: str = ""):
        """Log start of a phase and start timer."""
        self._phase_timers[phase_name] = datetime.now()
        emoji = self._get_phase_emoji(phase_name)
        msg = f"{emoji} STARTING: {phase_name}"
        if description:
            msg += f" - {description}"
        self._log(msg, level="info", source=phase_name)
    
    def _log_phase_end(self, phase_name: str, result_summary: str = ""):
        """Log end of a phase with duration."""
        duration = 0
        if phase_name in self._phase_timers:
            duration = (datetime.now() - self._phase_timers[phase_name]).total_seconds()
            del self._phase_timers[phase_name]
        emoji = "[OK]" if "error" not in result_summary.lower() else "[ERR]"
        msg = f"{emoji} COMPLETED: {phase_name} ({duration:.1f}s)"
        if result_summary:
            msg += f" - {result_summary}"
        self._log(msg, level="info", source=phase_name)
    
    def _get_phase_emoji(self, phase: str) -> str:
        """Get emoji for phase type."""
        emojis = {
            "brand_dna": "🧬",
            "discovery": "🔍",
            "keywords": "🔑",
            "scraping": "🕷️",
            "ad_library": "📺",
            "competitors": "🆚",
            "insights": "💡",
            "generators": "✨",
            "track1": "1️⃣",
            "track2": "2️⃣",
            "gemini": "🤖",
            "tiktok": "📱",
            "twitter": "🐦",
            "reddit": "[R]",
            "trustpilot": "⭐",
            "youtube": "📹",
            "news": "📰",
        }
        return emojis.get(phase.lower(), "📋")
    
    def _update_progress(self, phase: str, step: int, total_steps: int, description: str):
        """Update progress for the current phase and log it."""
        if self._session_id:
            set_phase_progress(self._session_id, phase, step, total_steps, description)
        self.current_phase = phase
        emoji = self._get_phase_emoji(phase)
        self._log(f"{emoji} [{phase.upper()}] Step {step}/{total_steps}: {description}", level="info", source="progress")
    
    async def run_full_research(self, session_id: int, brand_id: int):
        """
        Run the complete research pipeline with AGGRESSIVE PARALLELIZATION:
        
        Phase 1 (Parallel): Brand DNA + Discovery + Ad Library (background)
        Phase 2: Query Generation
        Phase 3 (Parallel): All scrapers run simultaneously
        Phase 4: Wait for Ad Library
        Phase 5 (Parallel): Competitor Analysis + Insights + Generators
        """
        import asyncio
        
        # Set session ID for logging
        self._session_id = session_id
        
        # Get session and brand
        session = await self._get_session(session_id)
        brand = await self._get_brand(brand_id)
        
        # Update status to in_progress
        session.status = "in_progress"
        await self.db.commit()
        
        # Initial log
        self._log(f"Starting research for {brand.name}", level="info", source="orchestrator")
        
        # =========================================================================
        # CHECK API QUOTAS BEFORE STARTING
        # =========================================================================
        from ..utils.api_quota_tracker import check_all_quotas, get_quota_tracker
        
        self._log("Checking API quotas...", level="info", source="orchestrator")
        quota_status = await check_all_quotas()
        
        for api_name, status in quota_status.items():
            if status.get("status") == "exhausted":
                self._log(f"WARNING: {api_name.upper()} quota exhausted!", level="warning", source="quota")
            elif status.get("status") == "ok":
                extra = ""
                if api_name == "apify" and status.get("remaining_usd"):
                    extra = f" (${status['remaining_usd']:.2f} remaining)"
                self._log(f"{api_name}: OK{extra}", level="info", source="quota")
        
        # Placeholders
        ad_library_results = {"brand_ads": None, "competitor_ads": [], "patterns": {}, "landing_pages": [], "total_ads_analyzed": 0}
        discovery_result = {}
        brand_dna = {}
        
        try:
            # =============================================
            # PHASE 1: PARALLEL - Brand DNA + Discovery
            # Plus start Ad Library in background
            # =============================================
            self._log_phase_start("Phase 1: Brand DNA + Discovery", f"Analyzing {brand.name}")
            self._update_progress("brand_dna", 1, 3, "Extracting Brand DNA from website...")
            
            async def extract_brand_dna_safe():
                """Wrapper for brand DNA extraction with error handling and timeout."""
                try:
                    if brand.website_url:
                        return await asyncio.wait_for(
                            self.brand_dna_extractor.extract_brand_dna(
                                website_url=brand.website_url,
                                brand_name=brand.name
                            ),
                            timeout=180.0  # 180 second timeout (needs 5+ network calls)
                        )
                except asyncio.TimeoutError:
                    print(f"    [!] Brand DNA TIMEOUT after 180s")
                except Exception as e:
                    print(f"    [!] Brand DNA error: {str(e)[:80]}")
                return {}
            
            async def discover_brand_safe():
                """Wrapper for brand discovery with error handling and timeout."""
                try:
                    return await asyncio.wait_for(
                        self.brand_discovery.discover(
                            brand_name=brand.name,
                            website_url=brand.website_url
                        ),
                        timeout=60.0  # 60 second timeout
                    )
                except asyncio.TimeoutError:
                    print(f"    [!] Discovery TIMEOUT after 60s")
                except Exception as e:
                    print(f"    [!] Discovery error: {str(e)[:80]}")
                return {}
            
            # Run Brand DNA and Discovery in parallel with individual timeouts
            self._update_progress("brand_dna", 2, 3, "Discovering brand info and competitors...")
            brand_dna, discovery_result = await asyncio.gather(
                extract_brand_dna_safe(),
                discover_brand_safe(),
                return_exceptions=False
            )
            
            # Update brand with DNA
            if brand_dna:
                brand.brand_colors = brand_dna.get("brand_colors", [])
                brand.tagline = brand_dna.get("tagline")
                brand.brand_values = brand_dna.get("brand_values", [])
                brand.brand_aesthetic = brand_dna.get("brand_aesthetic", [])
                brand.tone_of_voice = brand_dna.get("tone_of_voice", [])
                
                # logo_url should be a string, not a list
                logo_url = brand_dna.get("logo_url")
                if isinstance(logo_url, list):
                    brand.logo_url = logo_url[0] if logo_url else None
                else:
                    brand.logo_url = logo_url
                
                brand.fonts = brand_dna.get("fonts", [])
                
                # brand_images should be a flat list of strings, not nested lists
                raw_images = brand_dna.get("brand_images", [])
                flat_images = []
                for img in raw_images:
                    if isinstance(img, list):
                        flat_images.extend(img)
                    elif isinstance(img, str):
                        flat_images.append(img)
                brand.brand_images = flat_images
                
                brand.social_media_urls = brand_dna.get("social_media_urls", {})
                brand.product_descriptions = brand_dna.get("product_descriptions", [])
                if not brand.description and brand_dna.get("business_overview"):
                    brand.description = brand_dna["business_overview"]
                print(f"    [+] Brand DNA: {len(brand.brand_colors or [])} colors, {len(brand.brand_values or [])} values")
            
            # Update brand with discovery info
            if discovery_result:
                if not brand.description:
                    brand.description = discovery_result.get("description")
                brand.sector = discovery_result.get("sector")
                brand.vertical = discovery_result.get("vertical")
                brand.products = discovery_result.get("products", [])
                brand.target_audience = discovery_result.get("target_audience")
                print(f"    [+] Discovery: sector={brand.sector}, {len(discovery_result.get('competitors', []))} competitors found")
            
            await self.db.commit()
            self._log_phase_end("Phase 1: Brand DNA + Discovery", f"Colors: {len(brand.brand_colors or [])}, Competitors: {len(discovery_result.get('competitors', []))}")
            
            # =============================================
            # FALLBACK: If Brand DNA failed to get social media URLs,
            # try two approaches:
            # 1. Quick Firecrawl scrape of website links
            # 2. Google search for social handles (works even when site has no social links)
            # This is CRITICAL for Ad Library to work
            # =============================================
            if not brand.social_media_urls or not brand.social_media_urls.get("instagram"):
                self._log("Brand DNA missing social URLs, attempting fallback extraction...", level="warning", source="BrandExtractor")
                import httpx
                import re as _re
                social_urls = brand.social_media_urls or {}
                
                try:
                    async with httpx.AsyncClient(timeout=30.0) as http_client:
                        firecrawl_headers = {
                            "Authorization": f"Bearer {settings.FIRECRAWL_API_KEY}",
                            "Content-Type": "application/json"
                        }
                        
                        # ATTEMPT 1: Scrape website links directly
                        resp = await http_client.post(
                            f"{settings.FIRECRAWL_BASE_URL}/scrape",
                            headers=firecrawl_headers,
                            json={"url": brand.website_url, "formats": ["links"]}
                        )
                        if resp.status_code == 200:
                            all_links = resp.json().get("data", {}).get("links", [])
                            for link in all_links:
                                url = link if isinstance(link, str) else link.get("url", "")
                                url_lower = url.lower()
                                if "instagram.com" in url_lower and "instagram" not in social_urls:
                                    social_urls["instagram"] = url
                                elif "facebook.com" in url_lower and "facebook" not in social_urls:
                                    social_urls["facebook"] = url
                                elif "tiktok.com" in url_lower and "tiktok" not in social_urls:
                                    social_urls["tiktok"] = url
                                elif ("twitter.com" in url_lower or "x.com" in url_lower) and "twitter" not in social_urls:
                                    social_urls["twitter"] = url
                        
                        # ATTEMPT 2: If still no Instagram/Facebook, use Google search
                        # Use the domain name (e.g., 'joinfound' from joinfound.com) as it's more
                        # specific than the brand name (e.g., 'Found' is too generic)
                        from urllib.parse import urlparse
                        domain_slug = urlparse(brand.website_url).netloc.replace('www.', '').split('.')[0]
                        search_name = domain_slug if len(domain_slug) > 2 else brand.name
                        
                        if "instagram" not in social_urls:
                            self._log(f"No IG on website, searching Google for Instagram handle (query={search_name})...", source="BrandExtractor")
                            try:
                                search_resp = await http_client.post(
                                    f"{settings.FIRECRAWL_BASE_URL}/search",
                                    headers=firecrawl_headers,
                                    json={"query": f'"{search_name}" site:instagram.com', "limit": 3}
                                )
                                if search_resp.status_code == 200:
                                    for result in search_resp.json().get("data", []):
                                        url = result.get("url", "")
                                        if "instagram.com" in url.lower():
                                            social_urls["instagram"] = url
                                            self._log(f"Found IG via Google: {url}", source="BrandExtractor")
                                            break
                            except Exception:
                                pass
                        
                        if "facebook" not in social_urls:
                            self._log(f"No FB on website, searching Google for Facebook page (query={search_name})...", source="BrandExtractor")
                            try:
                                search_resp = await http_client.post(
                                    f"{settings.FIRECRAWL_BASE_URL}/search",
                                    headers=firecrawl_headers,
                                    json={"query": f'"{search_name}" site:facebook.com', "limit": 3}
                                )
                                if search_resp.status_code == 200:
                                    for result in search_resp.json().get("data", []):
                                        url = result.get("url", "")
                                        if "facebook.com" in url.lower():
                                            social_urls["facebook"] = url
                                            self._log(f"Found FB via Google: {url}", source="BrandExtractor")
                                            break
                            except Exception:
                                pass
                        
                        if social_urls:
                            brand.social_media_urls = social_urls
                            await self.db.commit()
                            self._log(f"Fallback social extraction result: {list(social_urls.keys())}", source="BrandExtractor")
                        else:
                            self._log("Could not find any social media URLs for this brand", level="warning", source="BrandExtractor")
                            
                except Exception as social_err:
                    self._log(f"Fallback social extraction failed: {str(social_err)[:80]}", level="warning", source="BrandExtractor")
            
            # Save website content to scraped_data (this was previously lost!)
            if brand_dna and brand_dna.get("website_content"):
                wc = brand_dna["website_content"]
                website_data_record = ScrapedData(
                    session_id=session.id,
                    source_type="brand_website",
                    source_url=brand.website_url,
                    track=1,
                    title=wc.get("title", f"{brand.name} Website"),
                    content=wc.get("markdown", "")[:20000],  # Limit content size
                    mention_type="direct_brand",
                    raw_data=json.dumps({
                        "description": wc.get("description", ""),
                        "social_media_urls": brand_dna.get("social_media_urls", {}),
                        "business_overview": brand_dna.get("business_overview", "")
                    })
                )
                self.db.add(website_data_record)
                await self.db.commit()
                print(f"    [+] Saved website content to scraped_data (source_type=brand_website)")
            
            # Extract competitors
            initial_competitors = discovery_result.get("competitors", [])
            
            # =============================================
            # BRAND NAME VALIDATION via Ad Library
            # Uses FB/IG usernames to validate and get page_id
            # =============================================
            validated_brand_name = brand.name
            validated_page_id = getattr(brand, 'ad_library_page_id', None)
            
            if brand.social_media_urls:
                self._log("Validating brand name via FB/IG in Ad Library...", source="BrandExtractor")
                try:
                    brand_result = await asyncio.wait_for(
                        self.brand_extractor.get_brand_name(
                            social_media_urls=brand.social_media_urls,
                            fallback_name=brand.name
                        ),
                        timeout=60.0
                    )
                    
                    # Use validated brand name if confidence is high enough
                    if brand_result.confidence >= 0.7:
                        validated_brand_name = brand_result.brand_name
                        if brand_result.page_id:
                            validated_page_id = brand_result.page_id
                            brand.ad_library_page_id = brand_result.page_id
                            await self.db.commit()
                        
                        self._log(
                            f"Brand validated: '{validated_brand_name}' (confidence={brand_result.confidence}, source={brand_result.source})",
                            source="BrandExtractor"
                        )
                        if brand_result.validation_passed:
                            self._log("[OK] FB/IG cross-validation PASSED", source="BrandExtractor")
                    else:
                        self._log(
                            f"Low confidence ({brand_result.confidence}), using original name: '{brand.name}'",
                            source="BrandExtractor"
                        )
                        
                except asyncio.TimeoutError:
                    self._log("Brand validation timeout (60s), using original name", level="warning", source="BrandExtractor")
                except Exception as e:
                    self._log(f"Brand validation error: {str(e)[:80]}", level="warning", source="BrandExtractor")
            
            # =============================================
            # START AD LIBRARY IN BACKGROUND (async - runs during scraping)
            # This is a heavy operation, so we start it early
            # =============================================
            print("    -> Starting Ad Library in background (async)...")
            # Extract Facebook and Instagram URLs from brand's social media for accurate Ad Library lookup
            facebook_url = None
            instagram_url = None
            if brand.social_media_urls:
                facebook_url = brand.social_media_urls.get("facebook")
                instagram_url = brand.social_media_urls.get("instagram")
            ad_library_task = asyncio.create_task(
                self._run_ad_library_analysis(
                    brand.name,  # ALWAYS use real brand name for keyword search (NOT validated_brand_name which may be garbage like "Ad Library - Facebook")
                    brand.website_url,
                    initial_competitors,
                    facebook_url=facebook_url,
                    instagram_url=instagram_url,
                    ad_library_page_id=validated_page_id  # Use validated page_id for post-filtering
                )
            )
            
            # =============================================
            # PHASE 2: Query Generation (quick, sequential)
            # =============================================
            self._log_phase_start("Phase 2: Keywords", "Generating search queries")
            self._update_progress("keywords", 1, 2, "Generating search queries...")
            queries = await self.keyword_generator.generate(
                brand_name=brand.name,
                sector=brand.sector,
                vertical=brand.vertical,
                products=brand.products or [],
                target_audience=brand.target_audience
            )
            
            session.brand_queries = queries.get("brand_queries", {})
            session.segment_queries = queries.get("segment_queries", {})
            await self.db.commit()
            self._log_phase_end("Phase 2: Keywords", f"Brand: {len(session.brand_queries)} queries, Segment: {len(session.segment_queries)} queries")
            
            # =============================================
            # PHASE 3: PARALLEL SCRAPING - All scrapers at once!
            # =============================================
            self._log_phase_start("Phase 3: Scraping", "Collecting data from all sources")
            self._update_progress("scraping", 1, 3, "Scraping brand-specific sources (Track 1)...")
            
            # Run Track 1 THEN Track 2 (sequential to avoid Firecrawl rate limits)
            all_scraped_data = []
            
            try:
                self._log("Track 1: Scraping brand-specific sources (Website, Reddit, Twitter, Reviews, etc.)...", source="Track 1")
                track1_data = await self._scrape_track1_parallel(
                    session_id, 
                    brand.name, 
                    brand.sector, 
                    queries, 
                    initial_competitors,
                    social_media_urls=brand.social_media_urls
                )
                if isinstance(track1_data, list):
                    all_scraped_data.extend(track1_data)
                    self._log(f"Track 1 complete: {len(track1_data)} items scraped", source="Track 1")
            except Exception as e:
                self._log(f"Track 1 ERROR: {str(e)[:100]}", level="error", source="Track 1")
                import traceback
                self._log(f"Track 1 traceback: {traceback.format_exc()[:200]}", level="error", source="Track 1")
                track1_data = []
            
            self._update_progress("scraping", 2, 3, "Scraping segment sources (Track 2)...")
            try:
                self._log("Track 2: Scraping segment sources (Forums, Quora, Industry News, TikTok, etc.)...", source="Track 2")
                track2_data = await self._scrape_track2_parallel(session_id, brand.sector, queries)
                if isinstance(track2_data, list):
                    all_scraped_data.extend(track2_data)
                    self._log(f"Track 2 complete: {len(track2_data)} items scraped", source="Track 2")
            except Exception as e:
                self._log(f"Track 2 ERROR: {str(e)[:100]}", level="error", source="Track 2")
                import traceback
                self._log(f"Track 2 traceback: {traceback.format_exc()[:200]}", level="error", source="Track 2")
                track2_data = []
            
            # === TIKTOK DATA RECOVERY ===
            # TikTok Apify actor may finish successfully but the in-memory await times out,
            # losing the data from all_scraped_data. Recover from DB if needed.
            tiktok_in_memory = [d for d in all_scraped_data if d.get("source_type") == "tiktok"]
            if not tiktok_in_memory:
                try:
                    from sqlalchemy import select
                    result = await self.db.execute(
                        select(ScrapedData).where(
                            ScrapedData.session_id == session_id,
                            ScrapedData.source_type == "tiktok"
                        )
                    )
                    tiktok_from_db = result.scalars().all()
                    if tiktok_from_db:
                        for tt in tiktok_from_db:
                            all_scraped_data.append({
                                "source_type": "tiktok",
                                "url": tt.source_url or "",
                                "title": tt.title or "",
                                "content": tt.content or "",
                                "author": tt.author or "",
                                "likes": tt.likes,
                                "comments_count": tt.comments_count,
                                "shares": tt.shares,
                                "posted_at": str(tt.posted_at) if tt.posted_at else None,
                                "video_analysis": tt.video_analysis,
                                "raw_data": tt.raw_data,
                                "track": tt.track or 1
                            })
                        self._log(f"TikTok recovery: loaded {len(tiktok_from_db)} items from DB", source="scraping")
                except Exception as e:
                    self._log(f"TikTok recovery failed: {str(e)[:80]}", level="warning", source="scraping")
            
            self._log(f"Total scraped: {len(all_scraped_data)} items from all sources", source="scraping")
            
            # Deduplicate scraped data before saving
            seen_urls = set()
            seen_content_hashes = set()
            deduplicated_data = []
            
            for data in all_scraped_data:
                # Get URL and content for dedup check
                url = data.get("url", "") or ""
                content = data.get("content", "") or data.get("summary", "") or ""
                
                # Create content hash (first 200 chars normalized)
                content_normalized = content.lower().strip()[:200].replace(" ", "")
                
                # Skip if we've seen this URL (and URL is not empty)
                if url and url in seen_urls:
                    continue
                    
                # Skip if we've seen similar content (same first 200 chars)
                if content_normalized and content_normalized in seen_content_hashes:
                    continue
                
                # Add to seen sets
                if url:
                    seen_urls.add(url)
                if content_normalized:
                    seen_content_hashes.add(content_normalized)
                    
                deduplicated_data.append(data)
            
            removed_duplicates = len(all_scraped_data) - len(deduplicated_data)
            if removed_duplicates > 0:
                self._log(f"Removed {removed_duplicates} duplicates ({len(deduplicated_data)} unique items)", source="scraping")
            
            # Analyze sentiment BEFORE saving so data is atomic (sentiment + content in same commit)
            # This also ensures RAG indexing gets proper sentiment for filtered searches
            try:
                from .sentiment import classify_sentiment, is_roberta_available
                _sentiment_model = "roberta" if is_roberta_available() else "keyword"
                _sentiment_count = 0
                for data in deduplicated_data:
                    content = data.get("content") or data.get("title") or ""
                    if content and len(content.strip()) > 10 and not data.get("sentiment"):
                        try:
                            _sent, _score = classify_sentiment(content)
                            data["sentiment"] = _sent
                            data["sentiment_score"] = _score
                            _sentiment_count += 1
                        except Exception:
                            data["sentiment"] = "neutral"
                            data["sentiment_score"] = 0.0
                self._log(f"Sentiment analyzed: {_sentiment_count}/{len(deduplicated_data)} items ({_sentiment_model})", source="sentiment")
            except Exception as _se:
                self._log(f"Pre-save sentiment failed (non-blocking): {str(_se)[:80]}", level="warning", source="sentiment")

            # Save all scraped data (now with sentiment already set)
            self._log(f"Saving {len(deduplicated_data)} items to database...", source="scraping")
            for data in deduplicated_data:
                filtered_data = filter_scraped_data(data)
                data_obj = ScrapedData(**filtered_data)
                self.db.add(data_obj)
            await self.db.commit()
            self._log_phase_end("Phase 3: Scraping", f"{len(deduplicated_data)} data points collected")
            
            # =============================================
            # INDEX SCRAPED DATA INTO RAG VECTOR STORE
            # This enables semantic search in chat
            # =============================================
            try:
                from .rag import get_vector_store
                vector_store = get_vector_store()
                
                # Prepare documents for indexing
                rag_documents = []
                for data in deduplicated_data:
                    content = data.get("content", "") or data.get("summary", "")
                    if content and len(content) > 50:  # Skip very short content
                        rag_documents.append({
                            "content": content,
                            "source_type": data.get("source_type", "unknown"),
                            "source_url": data.get("source_url", data.get("url", "")),
                            "sentiment": data.get("sentiment", ""),
                            "author": data.get("author", "")
                        })
                
                if rag_documents:
                    index_result = vector_store.index_session(session_id, rag_documents)
                    self._log(f"RAG indexed: {index_result.get('total_chunks', 0)} chunks from {len(rag_documents)} documents", source="RAG")
                else:
                    self._log("No documents to index for RAG", level="warning", source="RAG")
            except Exception as rag_err:
                self._log(f"RAG indexing failed (chat will use fallback): {str(rag_err)[:100]}", level="warning", source="RAG")
            
            # =============================================
            # PHASE 4: Wait for Ad Library (started in Phase 1)
            # =============================================
            self._log_phase_start("Phase 4: Ad Library", "Waiting for Ad Library analysis")
            self._update_progress("ad_library", 1, 1, "Analyzing Ad Library results...")
            try:
                # Await the task started in Phase 1
                ad_library_results = await ad_library_task
                # Ensure ad_library_results is not None before accessing
                if not ad_library_results:
                    ad_library_results = {"brand_ads": None, "competitor_ads": [], "patterns": {}, "landing_pages": [], "total_ads_analyzed": 0}
                print(f"    [+] Ad Library complete: {ad_library_results.get('total_ads_analyzed', 0)} ads analyzed")
                
                # Update brand with Ad Library thumbnails
                if ad_library_results.get("brand_ads"):
                    ad_thumbnails = self.brand_dna_extractor._extract_ad_thumbnails(
                        ad_library_results.get("brand_ads", {})
                    )
                    if ad_thumbnails:
                        brand.brand_images = (brand.brand_images or []) + [
                            t.get("url") for t in ad_thumbnails[:10] if t.get("url")
                        ]
                        print(f"    [+] Added {len(ad_thumbnails)} ad thumbnails to brand images")
                        await self.db.commit()
                
                # Index ad summaries into RAG for chat search
                try:
                    from .rag import get_vector_store
                    vector_store = get_vector_store()
                    
                    ad_rag_docs = []
                    # Index brand ads
                    if ad_library_results.get("brand_ads", {}).get("ads"):
                        for ad in ad_library_results["brand_ads"]["ads"]:
                            analysis = ad.get("creative_analysis", {})
                            ad_summary = analysis.get("ad_summary") or analysis.get("high_fidelity_description", "")
                            if ad_summary and len(ad_summary) > 50:
                                ad_rag_docs.append({
                                    "content": f"[AD CREATIVE] {ad_summary}\n\nFramework: {analysis.get('framework', 'N/A')}\nHook: {analysis.get('hook', ad.get('ad_copy', '')[:100])}\nTranscription: {analysis.get('transcription', 'N/A')[:500]}",
                                    "source_type": "ad_library",
                                    "source_url": ad.get("ad_library_url", ""),
                                    "sentiment": "neutral",
                                    "author": brand.name
                                })
                    
                    # Index competitor ads
                    for comp_data in ad_library_results.get("competitor_ads", []):
                        comp_name = comp_data.get("competitor_name", "Competitor")
                        for ad in comp_data.get("ads", []):
                            analysis = ad.get("creative_analysis", {})
                            ad_summary = analysis.get("ad_summary") or analysis.get("high_fidelity_description", "")
                            if ad_summary and len(ad_summary) > 50:
                                ad_rag_docs.append({
                                    "content": f"[COMPETITOR AD - {comp_name}] {ad_summary}\n\nFramework: {analysis.get('framework', 'N/A')}\nHook: {analysis.get('hook', ad.get('ad_copy', '')[:100])}",
                                    "source_type": "competitor_ad",
                                    "source_url": ad.get("ad_library_url", ""),
                                    "sentiment": "neutral",
                                    "author": comp_name
                                })
                    
                    if ad_rag_docs:
                        index_result = vector_store.index_session(session_id, ad_rag_docs)
                        print(f"    [RAG] Indexed {len(ad_rag_docs)} ad summaries for chat search")
                except Exception as rag_err:
                    print(f"    [!] Ad RAG indexing error: {str(rag_err)[:80]}")
                        
            except Exception as e:
                print(f"    [!] Ad Library error: {str(e)[:100]}")
                ad_library_results = {"brand_ads": None, "competitor_ads": [], "patterns": {}, "landing_pages": [], "total_ads_analyzed": 0}
            self._log_phase_end("Phase 4: Ad Library", f"{ad_library_results.get('total_ads_analyzed', 0)} ads analyzed")
            
            # Phase 5: Deep Competitor Analysis
            self._log_phase_start("Phase 5: Competitors", "Analyzing competitor brands")
            self._update_progress("competitors", 1, 2, "Analyzing competitor brands...")
            competitor_results = await self._run_competitor_analysis(
                brand.name,
                brand.sector,
                brand.vertical,
                discovery_result,
                initial_competitors,
                ad_library_results.get("competitor_ads", []) if ad_library_results else []
            )
            # Ensure competitor_results is not None
            if not competitor_results:
                competitor_results = {"profiles": [], "matrix": None, "swot": None}
            self._log_phase_end("Phase 5: Competitors", f"{len(competitor_results.get('profiles', []))} competitors profiled")
            
            # Phase 6: Generate Insights + Content  
            self._log_phase_start("Phase 6: Insights", "Generating insights and content")
            self._update_progress("insights", 1, 5, "Generating base insights (ICPs, pain points)...")
            
            # Generate base insights
            insights = await self.insights_generator.generate(
                brand_name=brand.name,
                brand_info=discovery_result,
                scraped_data=all_scraped_data
            )
            
            # Add raw data summary
            data_summary = self._create_data_summary(all_scraped_data)
            insights["data_summary"] = data_summary
            insights["top_quotes"] = self._extract_top_quotes(all_scraped_data)
            insights["data_by_topic"] = self._categorize_by_topic(all_scraped_data)

            # Safety net: update any items that missed pre-save sentiment
            await self._update_db_sentiment(session_id)

            # Add cross-source insights
            self._update_progress("insights", 2, 5, "Analyzing patterns across sources...")
            ad_patterns = ad_library_results.get("patterns", {}) if ad_library_results else {}
            cross_source = self._create_cross_source_insights(all_scraped_data, ad_patterns)
            
            # Enrich with LLM-powered CrossSourceAnalyzer validation
            collected_insights = cross_source.get("collected_source_insights", {})
            if collected_insights:
                try:
                    print("    [Cross-Source] Running AI validation of insights...")
                    validated_insights = await self.cross_source_analyzer.analyze_cross_source(
                        collected_insights,
                        brand_name=brand.name
                    )
                    
                    # Merge validated insights
                    cross_source["ai_validated_pain_points"] = validated_insights.get("validated_pain_points", [])
                    cross_source["key_opportunities"] = validated_insights.get("key_opportunities", [])
                    cross_source["strategic_recommendations"] = validated_insights.get("strategic_recommendations", [])
                    cross_source["ad_angle_suggestions"] = validated_insights.get("ad_angle_suggestions", [])
                    cross_source["cross_source_sentiment"] = validated_insights.get("cross_source_sentiment", {})
                    
                    print(f"    [+] {len(validated_insights.get('validated_pain_points', []))} AI-validated pain points")
                except Exception as e:
                    print(f"    [!] Cross-source AI analysis error: {str(e)[:80]}")
            
            insights["cross_source_insights"] = cross_source
            print(f"    [+] {len(cross_source.get('universal_themes', []))} validated themes across sources")
            
            # Generate Proto-ICPs from VoC data
            self._update_progress("insights", 2, 5, "Building Proto-ICPs from customer voice...")
            try:
                proto_icp_result = await asyncio.wait_for(
                    self.generate_proto_icps(session_id, brand.name),
                    timeout=600.0  # 10 minute max for Proto-ICP generation (13 batches × ~60s each)
                )
                insights["proto_icps"] = proto_icp_result.get("clusters", [])
                insights["proto_icp_recommendations"] = proto_icp_result.get("recommendations", [])
                insights["proto_icp_stats"] = proto_icp_result.get("stats", {})
                print(f"    [+] {len(proto_icp_result.get('clusters', []))} Proto-ICP clusters generated")
            except asyncio.TimeoutError:
                print("    [!] Proto-ICP generation timeout (180s), using empty clusters")
                insights["proto_icps"] = []
            except Exception as e:
                print(f"    [!] Proto-ICP generation error: {str(e)[:80]}")
                insights["proto_icps"] = []

            # Generate Creative Target Personas (CTP) from stance-based clustering
            self._update_progress("insights", 3, 5, "Building Creative Target Personas...")
            try:
                ctp_result = await asyncio.wait_for(
                    self.generate_ctps(
                        session_id=session_id,
                        brand_name=brand.name,
                        sector=brand.sector or "",
                        vertical=brand.vertical or "",
                        existing_pain_points=insights.get("market_pain_points", []),
                        ad_library_data=ad_library_results.get("brand_ads") if ad_library_results else None,
                        ad_creative_patterns=ad_library_results.get("patterns") if ad_library_results else None
                    ),
                    timeout=600.0  # 10 min max for CTP generation
                )
                insights["ctp_data"] = ctp_result.get("ctps", [])
                insights["ctp_hypothesis"] = ctp_result.get("hypothesis", [])
                insights["ctp_stats"] = ctp_result.get("stats", {})
                print(f"    [+] {len(ctp_result.get('ctps', []))} Creative Target Personas generated")
            except asyncio.TimeoutError:
                print("    [!] CTP generation timeout, skipping")
                insights["ctp_data"] = []
                insights["ctp_hypothesis"] = []
                insights["ctp_stats"] = {}
            except Exception as e:
                print(f"    [!] CTP generation error: {str(e)[:80]}")
                insights["ctp_data"] = []
                insights["ctp_hypothesis"] = []
                insights["ctp_stats"] = {}

            # Add Ad Library insights (with None checks)
            insights["ad_library_data"] = ad_library_results.get("brand_ads") if ad_library_results else None
            insights["competitor_ads_data"] = ad_library_results.get("competitor_ads") if ad_library_results else None
            insights["ad_creative_patterns"] = ad_library_results.get("patterns") if ad_library_results else None
            insights["landing_page_analysis"] = ad_library_results.get("landing_pages") if ad_library_results else None
            
            # === TikTok Trends Analysis ===
            # Surface trending sounds, hashtags, and content patterns
            try:
                tiktok_trends_service = get_tiktok_trends_service()
                tiktok_items = [d for d in deduplicated_data if d.get("source_type") == "tiktok"]
                
                if tiktok_items:
                    print(f"    [TikTok Trends] Analyzing {len(tiktok_items)} TikTok videos for trends...")
                    tiktok_trends = tiktok_trends_service.analyze_trends(
                        tiktok_data=tiktok_items,
                        brand_name=brand.name,
                        niche=brand.sector or brand.vertical or ""
                    )
                    insights["tiktok_trends"] = tiktok_trends
                    
                    # Log summary
                    sounds_count = len(tiktok_trends.get("trending_sounds", []))
                    hashtags_count = len(tiktok_trends.get("trending_hashtags", []))
                    print(f"    [+] TikTok Trends: {sounds_count} sounds, {hashtags_count} hashtags surfaced")
                else:
                    insights["tiktok_trends"] = {"status": "no_tiktok_data"}
            except Exception as e:
                print(f"    [!] TikTok Trends analysis error: {str(e)[:80]}")
                insights["tiktok_trends"] = {"status": "error", "error": str(e)[:100]}
            
            # === TikTok Segment LLM Analysis ===
            # Deep LLM analysis for customer language, pain points, and content patterns
            try:
                tiktok_items = [d for d in deduplicated_data if d.get("source_type") == "tiktok"]
                
                if tiktok_items and len(tiktok_items) >= 3:
                    print(f"    [TikTok Segment] LLM analysis of {len(tiktok_items)} TikTok videos...")
                    segment_analyzer = get_tiktok_segment_analyzer()
                    
                    # Run full analysis (individual + aggregated)
                    segment_result = await segment_analyzer.full_analysis(
                        videos=tiktok_items,
                        niche=brand.sector or brand.vertical or "",
                        max_analyze=20  # Limit for cost control
                    )
                    
                    # Store in tiktok_trends for downstream use
                    if insights.get("tiktok_trends"):
                        insights["tiktok_trends"]["segment_analysis"] = segment_result.get("aggregated_insights")
                        insights["tiktok_trends"]["individual_analyses"] = segment_result.get("individual_analyses", [])[:10]  # Limit storage
                    else:
                        insights["tiktok_segment_analysis"] = segment_result
                    
                    individual_count = len(segment_result.get("individual_analyses", []))
                    has_aggregated = "Yes" if segment_result.get("aggregated_insights") else "No"
                    print(f"    [+] TikTok Segment: {individual_count} videos analyzed, aggregated={has_aggregated}")
                else:
                    print(f"    [TikTok Segment] Skipped - need >= 3 videos (have {len(tiktok_items if tiktok_items else [])})")
            except Exception as e:
                print(f"    [!] TikTok Segment analysis error: {str(e)[:80]}")
            
            # === Instagram Brand Presence LLM Analysis ===
            # Analyze brand's Instagram for voice, tone, visual aesthetic, content pillars
            try:
                # Get Instagram profile posts (marked as instagram_profile source_type)
                ig_posts = [d for d in deduplicated_data if d.get("source_type") == "instagram_profile"]
                
                if ig_posts and len(ig_posts) >= 5:
                    print(f"    [Instagram Brand] Analyzing {len(ig_posts)} posts for brand presence...")
                    ig_analyzer = get_instagram_brand_analyzer()
                    
                    brand_presence = await ig_analyzer.analyze_brand_presence(
                        posts=ig_posts[:40],  # Last 40 posts
                        brand_name=brand.name
                    )
                    
                    if brand_presence:
                        insights["instagram_brand_presence"] = brand_presence
                        voice = brand_presence.get("brand_voice", "N/A")[:50]
                        archetype = brand_presence.get("brand_archetype", "N/A")
                        print(f"    [+] Instagram Brand: Voice='{voice}', Archetype={archetype}")
                    else:
                        print(f"    [Instagram Brand] Analysis returned no results")
                else:
                    print(f"    [Instagram Brand] Skipped - need >= 5 profile posts (have {len(ig_posts if ig_posts else [])})")
            except Exception as e:
                print(f"    [!] Instagram Brand analysis error: {str(e)[:80]}")
            
            # Add competitor analysis (with None checks)
            insights["competitor_profiles"] = competitor_results.get("profiles") if competitor_results else None
            insights["competitive_matrix"] = competitor_results.get("matrix") if competitor_results else None
            insights["swot_analysis"] = competitor_results.get("swot") if competitor_results else None
            
            # Generate content with Generators - IN PARALLEL
            self._update_progress("insights", 3, 5, "Generating creative content (scripts, thumbnails)...")
            brand_info = {
                "name": brand.name,
                "sector": brand.sector,
                "vertical": brand.vertical,
                "products": brand.products,
                "target_audience": brand.target_audience,
                "value_propositions": discovery_result.get("value_propositions", []) if discovery_result else []
            }
            
            ad_patterns = ad_library_results.get("patterns", {}) if ad_library_results else {}
            
            # =============================================
            # EXTRACT AD EXAMPLES for generators (not just aggregates)
            # This provides real examples of hooks, transcriptions, summaries
            # =============================================
            ad_examples = {
                "brand_ads": [],
                "competitor_ads": [],
                "best_hooks": [],
                "best_transcriptions": [],
                "frameworks_with_examples": {}
            }
            
            # Extract brand ad examples
            if ad_library_results and (ad_library_results.get("brand_ads") or {}).get("ads"):
                for ad in ad_library_results["brand_ads"]["ads"][:15]:  # Top 15 brand ads
                    analysis = ad.get("creative_analysis", {})
                    if analysis:
                        ad_example = {
                            "ad_summary": analysis.get("ad_summary", ""),
                            "transcription": analysis.get("transcription", ""),
                            "hook": analysis.get("hook") or analysis.get("opening_copy", ""),
                            "framework": analysis.get("framework", ""),
                            "hook_strength": analysis.get("hook_strength", 0),
                            "effectiveness": analysis.get("effectiveness", 0),
                            "cta": analysis.get("cta_all", ""),
                            "emotion": analysis.get("emotion", ""),
                            "tone": analysis.get("tone", ""),
                            "visual_type": analysis.get("visual_type", ""),
                            "media_type": ad.get("media_type", "unknown"),
                            "ad_copy": ad.get("ad_copy", "")
                        }
                        ad_examples["brand_ads"].append(ad_example)
                        
                        # Track best hooks
                        if ad_example["hook"] and ad_example.get("hook_strength", 0) >= 3:
                            ad_examples["best_hooks"].append({
                                "hook": ad_example["hook"],
                                "strength": ad_example["hook_strength"],
                                "framework": ad_example["framework"],
                                "source": "brand"
                            })
                        
                        # Track framework examples
                        fw = ad_example["framework"]
                        if fw:
                            if fw not in ad_examples["frameworks_with_examples"]:
                                ad_examples["frameworks_with_examples"][fw] = []
                            if len(ad_examples["frameworks_with_examples"][fw]) < 2:
                                ad_examples["frameworks_with_examples"][fw].append(ad_example)
            
            # Extract competitor ad examples
            for comp_data in (ad_library_results.get("competitor_ads", []) if ad_library_results else []):
                comp_name = comp_data.get("competitor_name", "Competitor")
                for ad in comp_data.get("ads", [])[:10]:  # Top 10 per competitor
                    analysis = ad.get("creative_analysis", {})
                    if analysis:
                        ad_example = {
                            "competitor": comp_name,
                            "ad_summary": analysis.get("ad_summary", ""),
                            "transcription": analysis.get("transcription", ""),
                            "hook": analysis.get("hook") or analysis.get("opening_copy", ""),
                            "framework": analysis.get("framework", ""),
                            "hook_strength": analysis.get("hook_strength", 0),
                            "effectiveness": analysis.get("effectiveness", 0),
                            "cta": analysis.get("cta_all", ""),
                            "emotion": analysis.get("emotion", ""),
                            "ad_copy": ad.get("ad_copy", "")
                        }
                        ad_examples["competitor_ads"].append(ad_example)
                        
                        # Track competitor hooks
                        if ad_example["hook"] and ad_example.get("hook_strength", 0) >= 3:
                            ad_examples["best_hooks"].append({
                                "hook": ad_example["hook"],
                                "strength": ad_example["hook_strength"],
                                "framework": ad_example["framework"],
                                "source": f"competitor:{comp_name}"
                            })
            
            # Sort best hooks by strength
            ad_examples["best_hooks"] = sorted(
                ad_examples["best_hooks"], 
                key=lambda x: x.get("strength", 0), 
                reverse=True
            )[:20]  # Top 20 hooks
            
            print(f"    [Ad Examples] {len(ad_examples['brand_ads'])} brand ads, {len(ad_examples['competitor_ads'])} competitor ads, {len(ad_examples['best_hooks'])} top hooks")
            
            # =============================================
            # FALLBACK: Provide default ad patterns if Ad Library failed
            # This ensures generators always have context to work with
            # =============================================
            if not ad_patterns or not ad_patterns.get("frameworks"):
                self._log("Ad Library returned empty patterns, using intelligent fallbacks", level="warning", source="Generators")
                ad_patterns = {
                    "frameworks": {"Problem-Solution": 3, "Testimonial": 2, "How-To": 2, "Before-After": 1, "Listicle": 1},
                    "hook_types": {"Question": 3, "Statement": 2, "Statistic": 1, "Testimonial Quote": 1},
                    "emotions": {"Relief": 2, "Curiosity": 2, "Hope": 1, "Trust": 1},
                    "top_transcriptions": [],
                    "avg_hook_strength": 3.5,
                    "visual_types": {"talking_head": 2, "product_demo": 2, "lifestyle": 1},
                    "competitor_hooks": []
                }
            
            # Add ad_examples to ad_patterns so generators can access them
            ad_patterns["ad_examples"] = ad_examples
            
            # === DEBUG: Log ad_patterns content for script generation ===
            print(f"    [DEBUG] ad_patterns keys: {list(ad_patterns.keys())}")
            print(f"    [DEBUG] frameworks: {list(ad_patterns.get('frameworks', {}).keys())[:5]}")
            print(f"    [DEBUG] hook_types: {list(ad_patterns.get('hook_types', {}).keys())[:5]}")
            print(f"    [DEBUG] top_transcriptions count: {len(ad_patterns.get('top_transcriptions', []))}")
            if ad_patterns.get('top_transcriptions'):
                first_trans = ad_patterns['top_transcriptions'][0] if ad_patterns['top_transcriptions'] else {}
                print(f"    [DEBUG] First transcription sample: {str(first_trans.get('text', ''))[:100]}...")
            print(f"    [DEBUG] competitor_hooks: {ad_patterns.get('competitor_hooks', [])[:3]}")
            # === END DEBUG ===
            
            # Run all 3 generators in parallel
            async def gen_scripts():
                try:
                    return await self.script_generator.generate_scripts(
                        brand_info=brand_info, ad_patterns=ad_patterns, insights=insights, num_scripts=5
                    )
                except Exception as e:
                    print(f"       [!] Scripts error: {e}")
                    return []
            
            async def gen_thumbnails():
                try:
                    return await self.thumbnail_suggester.suggest_thumbnails(
                        brand_info=brand_info, ad_patterns=ad_patterns, insights=insights, num_suggestions=5
                    )
                except Exception as e:
                    print(f"       [!] Thumbnails error: {e}")
                    return []
            
            async def gen_ab_tests():
                try:
                    return await self.ab_test_suggester.suggest_tests(
                        brand_info=brand_info, ad_patterns=ad_patterns, insights=insights,
                        competitor_data=competitor_results, num_tests=5
                    )
                except Exception as e:
                    print(f"       [!] A/B tests error: {e}")
                    return []
            
            # Run all 3 generators in parallel with global timeout
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(
                        gen_scripts(), gen_thumbnails(), gen_ab_tests(),
                        return_exceptions=True
                    ),
                    timeout=180.0  # 3 minute max for all generators combined
                )
                
                # Handle results - could be values or exceptions
                scripts = results[0] if isinstance(results[0], list) else []
                thumbnails = results[1] if isinstance(results[1], list) else []
                ab_tests = results[2] if isinstance(results[2], list) else []
                
                # Log any exceptions
                for i, r in enumerate(results):
                    if isinstance(r, Exception):
                        names = ["Scripts", "Thumbnails", "A/B Tests"]
                        print(f"       [!] {names[i]} failed: {str(r)[:50]}")
                        
            except asyncio.TimeoutError:
                print("       [!] Generators global timeout (180s) - using fallbacks")
                scripts, thumbnails, ab_tests = [], [], []
            
            insights["generated_scripts"] = scripts if isinstance(scripts, list) else []
            insights["thumbnail_suggestions"] = thumbnails if isinstance(thumbnails, list) else []
            insights["ab_test_suggestions"] = ab_tests if isinstance(ab_tests, list) else []
            print(f"       -> {len(scripts)} scripts, {len(thumbnails)} thumbnails, {len(ab_tests)} A/B tests")
            
            # Generate Hooks Library (structured hooks for creative briefs)
            try:
                hooks_service = get_hooks_library_service()
                hooks_library = await asyncio.wait_for(
                    hooks_service.generate_hooks_library(
                        brand_info=brand_info,
                        insights=insights,
                        num_hooks=20
                    ),
                    timeout=180.0
                )
                insights["hooks_library"] = hooks_library
                print(f"       -> {hooks_library.get('total_hooks', 0)} hooks in library")
            except asyncio.TimeoutError:
                print(f"       [!] Hooks Library timeout, skipping")
                insights["hooks_library"] = {"status": "timeout"}
            except Exception as e:
                print(f"       [!] Hooks Library error: {str(e)[:80]}")
                insights["hooks_library"] = {"status": "error", "error": str(e)[:100]}
            
            # Generate full report
            insights["full_report"] = self._generate_full_report(
                brand, insights, ad_library_results, competitor_results
            )
            
            # CRITICAL: Sanitize insights to convert datetime to ISO strings before DB insert
            sanitized_insights = _sanitize_for_json(insights)
            
            # Filter only valid Insight model fields to avoid SQLAlchemy errors
            valid_insight_fields = {
                'session_id', 'brand_summary', 'sentiment_score', 'total_mentions',
                'top_positives', 'top_negatives', 'competitors_mentioned', 'market_pain_points',
                'customer_language', 'customer_desires', 'trending_topics', 'icps', 'pain_points',
                'value_props', 'messaging_angles', 'tone_emotions', 'content_insights',
                'competitor_analysis', 'purchase_triggers', 'objections', 'decision_factors',
                'verbatim_quotes', 'content_opportunities', 'recommended_hooks', 'price_sensitivity',
                'feature_requests', 'ad_library_data', 'competitor_ads_data', 'ad_creative_patterns',
                'landing_page_analysis', 'generated_scripts', 'thumbnail_suggestions',
                'ab_test_suggestions', 'competitor_profiles', 'competitive_matrix', 'swot_analysis',
                'data_summary', 'top_quotes', 'data_by_topic', 'cross_source_insights',
                'proto_icps', 'proto_icp_recommendations', 'proto_icp_stats', 'full_report',
                'tiktok_trends',            # TikTok: Trending sounds, hashtags, content patterns
                'hooks_library',            # Structured hooks library for creative briefs
                'instagram_brand_presence', # Brand voice, content pillars, archetype
                'ctp_data', 'ctp_hypothesis', 'ctp_stats'  # Creative Target Personas
            }
            filtered_insights = {k: v for k, v in sanitized_insights.items() if k in valid_insight_fields}
            
            # Save insights with proper error handling
            try:
                insight_obj = Insight(
                    session_id=session_id,
                    **filtered_insights
                )
                self.db.add(insight_obj)
                
                # Mark session as completed
                session.status = "completed"
                session.completed_at = datetime.now()
                await self.db.commit()
                print(f"       [+] Insights saved to database successfully")
            except Exception as db_err:
                print(f"       [!] Error saving insights to DB: {db_err}")
                await self.db.rollback()
                # Try to at least mark as completed
                try:
                    session.status = "completed"
                    session.completed_at = datetime.now()
                    await self.db.commit()
                except:
                    pass
                raise
            
            # Export to knowledge base for Open WebUI
            try:
                self._log("Exporting scraped data to local knowledge base...", source="KB Export")
                kb_exporter = get_kb_exporter()
                export_result = await kb_exporter.export_session(self.db, session_id)
                self._log(f"Local KB exported: {export_result.get('total_files', 0)} markdown files created in knowledge_base/{brand.name}/", source="KB Export")
                
                # Process with Knowledge Synthesizer (LLM-powered extraction) - OPTIONAL
                # This creates summarized docs but is not required for RAG chat
                # RAG chat now uses raw docs from knowledge_base/ directly
                use_synthesizer = False  # Set to True if you want summarized docs
                if use_synthesizer:
                    self._log(f"Starting Knowledge Synthesizer - Processing {len(all_scraped_data)} items with Gemini LLM...", source="Synthesizer")
                    self._log("This extracts quotes, sentiment, pain points from all scraped content (reviews, Reddit, forums, etc.)", source="Synthesizer")
                    try:
                        synthesizer = get_knowledge_synthesizer(output_dir="knowledge_base_processed", use_llm=True)
                        synth_result = await synthesizer.synthesize_session(
                            self.db, 
                            session_id,
                            progress_callback=lambda msg: self._log(msg, source="Synthesizer")
                        )
                        items_by_type = synth_result.get('items_by_type', {})
                        type_summary = ", ".join([f"{k}: {v}" for k, v in items_by_type.items()])
                        self._log(f"Synthesizer complete: {synth_result.get('items_processed', 0)} items processed ({type_summary})", source="Synthesizer")
                        self._log(f"Generated {len(synth_result.get('files_created', []))} structured documents: reviews_synthesis.md, discussions_insights.md, etc.", source="Synthesizer")
                    except Exception as synth_err:
                        self._log(f"Synthesizer failed (non-critical, RAG will use basic data): {synth_err}", level="warning", source="Synthesizer")
                else:
                    self._log("Skipping Knowledge Synthesizer (using raw docs for RAG)", source="Synthesizer")
                
                # Sync RAW documents to AnythingLLM workspace
                self._log(f"Syncing RAW documents to AnythingLLM workspace '{brand.name}'...", source="AnythingLLM")
                self._log("Uploading raw markdown files (reddit, trustpilot, etc) for RAG chat...", source="AnythingLLM")
                sync_result = await sync_brand_to_workspace(brand.name)  # Uses knowledge_base/ by default
                if sync_result.get('success'):
                    self._log(f"AnythingLLM sync complete: {sync_result.get('documents_uploaded', 0)} docs uploaded, workspace '{sync_result.get('workspace_slug')}' ready for chat", source="AnythingLLM")
                else:
                    self._log(f"AnythingLLM sync partial (some docs may not be indexed): {sync_result.get('errors', [])}", level="warning", source="AnythingLLM")
            except Exception as kb_err:
                self._log(f"Knowledge base export/sync failed (non-critical, data is still in DB): {kb_err}", level="warning", source="KB Export")
            
            # =========================================================================
            # PRINT API QUOTA SUMMARY (non-critical — must not crash pipeline)
            # =========================================================================
            try:
                tracker = get_quota_tracker()
                if tracker.has_quota_errors():
                    print("\n" + "="*60)
                    print("  API QUOTA ISSUES DETECTED DURING RESEARCH")
                    print("="*60)
                    for err in tracker.get_session_errors():
                        api_name = err.get('api', 'unknown').upper()
                        error_msg = str(err.get('error', ''))[:60]
                        print(f"  - {api_name}: {error_msg}")
                    print("Some data may be missing due to quota limits.")
                    print("="*60 + "\n")
                # print_summary uses emojis that crash on Windows cp1252
                summary = tracker.get_summary()
                apis = summary.get("apis", {})
                if apis:
                    print("\n  API Status:")
                    for api_name, info in apis.items():
                        print(f"    {api_name}: {info.get('status','?')} ({info.get('requests',0)} requests, {info.get('failed',0)} failed)")
                        if info.get('last_error'):
                            print(f"      Last error: {info['last_error']}")
            except Exception as qt_err:
                print(f"    [!] Quota tracker error (non-critical): {str(qt_err)[:80]}")

            print(f"[+] Research completed for '{brand.name}'!")
            print(f"    Total data points: {len(all_scraped_data)}")
            print(f"    Ads analyzed: {ad_library_results.get('total_ads_analyzed', 0)}")
            print(f"    Competitors profiled: {len(competitor_results.get('profiles', []))}")

        except Exception as e:
            # Only mark as failed if insights weren't already saved
            if session.status != "completed":
                session.status = "failed"
                await self.db.commit()
            print(f"[-] Research failed: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    async def reprocess_insights(self, session_id: int, brand_id: int):
        """
        Reprocess insights using existing scraped data from the database.
        Skips all scraping phases - only runs insight generation and content generators.
        Useful when insight generation failed but data was already scraped.
        
        This mirrors run_full_research Phase 5-7:
        1. Generate base insights (ICPs, pain_points, value_props, messaging_angles)
        2. Run content generators (scripts, thumbnails, ab_tests)
        3. Create full report
        """
        import asyncio
        
        print(f"\n{'='*50}")
        print(f"[Reprocess] Starting FULL insight reprocessing for session {session_id}")
        print(f"{'='*50}")
        
        session = await self._get_session(session_id)
        brand = await self._get_brand(brand_id)
        
        session.status = "in_progress"
        await self.db.commit()
        
        try:
            # =============================================
            # STEP 1: Load existing scraped data
            # =============================================
            print(f"[1/5] Loading scraped data from database...")
            result = await self.db.execute(
                select(ScrapedData).where(ScrapedData.session_id == session_id)
            )
            scraped_records = result.scalars().all()
            
            # Convert to dict format for processing
            all_scraped_data = []
            for record in scraped_records:
                all_scraped_data.append({
                    "session_id": record.session_id,
                    "source_type": record.source_type,
                    "source_url": record.source_url,
                    "track": record.track,
                    "title": record.title,
                    "content": record.content,
                    "author": record.author,
                    "posted_at": str(record.posted_at) if record.posted_at else None,
                    "likes": record.likes,
                    "comments_count": record.comments_count,
                    "shares": record.shares,
                    "rating": record.rating,
                    "mention_type": record.mention_type,
                    "sentiment": record.sentiment,
                    "sentiment_score": record.sentiment_score,
                    "raw_data": record.raw_data
                })
            
            print(f"    [+] Loaded {len(all_scraped_data)} items from database")
            
            # Helper to safely parse JSON or return list as-is
            def safe_json_parse(value):
                if not value:
                    return []
                if isinstance(value, list):
                    return value
                if isinstance(value, str):
                    try:
                        return json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        return []
                return []
            
            # Prepare brand/discovery info
            brand_info = {
                "name": brand.name,
                "sector": brand.sector or "Unknown",
                "vertical": brand.vertical or "",
                "description": brand.description or "",
                "target_audience": brand.target_audience or "",
                "products": safe_json_parse(brand.products) if brand.products else [],
                "value_propositions": [],
                "brand_values": safe_json_parse(brand.brand_values),
                "tone_of_voice": safe_json_parse(brand.tone_of_voice)
            }
            
            # =============================================
            # STEP 2: Generate base insights using AI
            # =============================================
            print(f"[2/5] Generating deep insights with AI (ICPs, pain points, value props)...")
            
            insights = await self.insights_generator.generate(
                brand_name=brand.name,
                brand_info=brand_info,
                scraped_data=all_scraped_data
            )
            
            print(f"    [+] Generated: {len(insights.get('icps', []))} ICPs, "
                  f"{len(insights.get('pain_points', []))} pain points, "
                  f"{len(insights.get('value_props', []))} value props")
            
            # =============================================
            # STEP 3: Add data summaries and cross-source analysis
            # =============================================
            print(f"[3/5] Creating data summaries and cross-source analysis...")
            
            data_summary = self._create_data_summary(all_scraped_data)
            insights["data_summary"] = data_summary
            insights["top_quotes"] = self._extract_top_quotes(all_scraped_data)
            insights["data_by_topic"] = self._categorize_by_topic(all_scraped_data)
            
            # Cross-source insights
            cross_source = self._create_cross_source_insights(all_scraped_data, {})
            insights["cross_source_insights"] = cross_source
            print(f"    [+] Summary: {data_summary['total_items']} items, "
                  f"{data_summary['sentiment_pct'].get('positive', 0):.1f}% positive")
            
            # Generate Proto-ICPs from VoC data
            print(f"    [+] Building Proto-ICPs from customer voice...")
            try:
                proto_icp_result = await self.generate_proto_icps(session_id, brand.name)
                insights["proto_icps"] = proto_icp_result.get("clusters", [])
                insights["proto_icp_recommendations"] = proto_icp_result.get("recommendations", [])
                insights["proto_icp_stats"] = proto_icp_result.get("stats", {})
                print(f"    [+] {len(proto_icp_result.get('clusters', []))} Proto-ICP clusters generated")
            except Exception as e:
                print(f"    [!] Proto-ICP generation error: {str(e)[:80]}")
                insights["proto_icps"] = []

            # Generate Creative Target Personas (CTP) from stance-based clustering
            print(f"    [+] Building Creative Target Personas...")
            try:
                ctp_result = await asyncio.wait_for(
                    self.generate_ctps(
                        session_id=session_id,
                        brand_name=brand.name,
                        sector=brand.sector or "",
                        vertical=brand.vertical or "",
                        existing_pain_points=insights.get("market_pain_points", []),
                        ad_library_data=None,
                        ad_creative_patterns=None
                    ),
                    timeout=600.0
                )
                insights["ctp_data"] = ctp_result.get("ctps", [])
                insights["ctp_hypothesis"] = ctp_result.get("hypothesis", [])
                insights["ctp_stats"] = ctp_result.get("stats", {})
                print(f"    [+] {len(ctp_result.get('ctps', []))} Creative Target Personas generated")
            except Exception as e:
                print(f"    [!] CTP generation error: {str(e)[:80]}")
                insights["ctp_data"] = []
                insights["ctp_hypothesis"] = []
                insights["ctp_stats"] = {}

            # =============================================
            # STEP 4: Run content generators in parallel
            # =============================================
            print(f"[4/5] Generating content with AI (scripts, thumbnails, A/B tests)...")
            
            async def gen_scripts():
                try:
                    return await self.script_generator.generate_scripts(
                        brand_info=brand_info, ad_patterns={}, insights=insights, num_scripts=5
                    )
                except Exception as e:
                    print(f"       [!] Scripts error: {e}")
                    return []
            
            async def gen_thumbnails():
                try:
                    return await self.thumbnail_suggester.suggest_thumbnails(
                        brand_info=brand_info, ad_patterns={}, insights=insights, num_suggestions=5
                    )
                except Exception as e:
                    print(f"       [!] Thumbnails error: {e}")
                    return []
            
            async def gen_ab_tests():
                try:
                    return await self.ab_test_suggester.suggest_tests(
                        brand_info=brand_info, ad_patterns={}, insights=insights,
                        competitor_data={}, num_tests=5
                    )
                except Exception as e:
                    print(f"       [!] A/B tests error: {e}")
                    return []
            
            scripts, thumbnails, ab_tests = await asyncio.gather(
                gen_scripts(), gen_thumbnails(), gen_ab_tests()
            )
            
            insights["generated_scripts"] = scripts if isinstance(scripts, list) else []
            insights["thumbnail_suggestions"] = thumbnails if isinstance(thumbnails, list) else []
            insights["ab_test_suggestions"] = ab_tests if isinstance(ab_tests, list) else []
            print(f"    [+] Generated: {len(scripts)} scripts, {len(thumbnails)} thumbnails, {len(ab_tests)} A/B tests")
            
            # =============================================
            # STEP 5: Generate full report and save
            # =============================================
            print(f"[5/5] Generating full report and saving...")
            
            insights["full_report"] = self._generate_full_report(
                brand, insights, {}, {}
            )
            
            # Preserve ad library data from existing insight before deleting
            existing_result = await self.db.execute(
                select(Insight).where(Insight.session_id == session_id)
            )
            existing_insight = existing_result.scalar_one_or_none()
            
            preserved_ad_data = {}
            if existing_insight:
                preserved_ad_data = {
                    "ad_library_data": existing_insight.ad_library_data,
                    "competitor_ads_data": existing_insight.competitor_ads_data,
                    "ad_creative_patterns": existing_insight.ad_creative_patterns,
                    "landing_page_analysis": existing_insight.landing_page_analysis,
                    "competitor_profiles": existing_insight.competitor_profiles,
                    "competitive_matrix": existing_insight.competitive_matrix,
                    "swot_analysis": existing_insight.swot_analysis,
                }
            
            # Delete old insights
            await self.db.execute(
                delete(Insight).where(Insight.session_id == session_id)
            )
            await self.db.commit()
            
            # Sanitize insights and preserved data to convert datetime to strings
            insights = _sanitize_for_json(insights)
            preserved_ad_data = _sanitize_for_json(preserved_ad_data)
            
            # Create new insight record with all fields
            insight_record = Insight(
                session_id=session_id,
                brand_summary=insights.get("brand_summary") or brand.description or f"Analysis for {brand.name}",
                sentiment_score=insights.get("sentiment_score") or (
                    (data_summary["sentiment_pct"].get("positive", 50) - 
                     data_summary["sentiment_pct"].get("negative", 0)) / 100
                ),
                total_mentions=data_summary["total_items"],
                # Track 1 insights
                top_positives=insights.get("top_positives"),
                top_negatives=insights.get("top_negatives"),
                competitors_mentioned=insights.get("competitors_mentioned"),
                # Track 2 insights  
                market_pain_points=insights.get("market_pain_points"),
                customer_language=insights.get("customer_language"),
                customer_desires=insights.get("customer_desires"),
                trending_topics=insights.get("trending_topics"),
                # Creative Dimensions
                icps=insights.get("icps"),
                pain_points=insights.get("pain_points"),
                value_props=insights.get("value_props"),
                messaging_angles=insights.get("messaging_angles"),
                tone_emotions=insights.get("tone_emotions"),
                content_insights=insights.get("content_insights"),
                # Enhanced insights
                competitor_analysis=insights.get("competitor_analysis"),
                purchase_triggers=insights.get("purchase_triggers"),
                objections=insights.get("objections"),
                decision_factors=insights.get("decision_factors"),
                verbatim_quotes=insights.get("verbatim_quotes") or insights.get("top_quotes"),
                content_opportunities=insights.get("content_opportunities"),
                recommended_hooks=insights.get("recommended_hooks"),
                price_sensitivity=insights.get("price_sensitivity"),
                feature_requests=insights.get("feature_requests"),
                # Ad Library data (preserved from original)
                ad_library_data=preserved_ad_data.get("ad_library_data"),
                competitor_ads_data=preserved_ad_data.get("competitor_ads_data"),
                ad_creative_patterns=preserved_ad_data.get("ad_creative_patterns"),
                landing_page_analysis=preserved_ad_data.get("landing_page_analysis"),
                # Competitive Intelligence (preserved from original)
                competitor_profiles=preserved_ad_data.get("competitor_profiles"),
                competitive_matrix=preserved_ad_data.get("competitive_matrix"),
                swot_analysis=preserved_ad_data.get("swot_analysis"),
                # Generated content
                generated_scripts=insights.get("generated_scripts"),
                thumbnail_suggestions=insights.get("thumbnail_suggestions"),
                ab_test_suggestions=insights.get("ab_test_suggestions"),
                # Raw data summary
                data_summary=insights.get("data_summary"),
                top_quotes=insights.get("top_quotes"),
                data_by_topic=insights.get("data_by_topic"),
                cross_source_insights=insights.get("cross_source_insights"),
                # Proto-ICPs
                proto_icps=insights.get("proto_icps"),
                proto_icp_recommendations=insights.get("proto_icp_recommendations"),
                proto_icp_stats=insights.get("proto_icp_stats"),
                # Creative Target Personas
                ctp_data=insights.get("ctp_data"),
                ctp_hypothesis=insights.get("ctp_hypothesis"),
                ctp_stats=insights.get("ctp_stats"),
                full_report=insights.get("full_report"),
                created_at=datetime.now()
            )
            self.db.add(insight_record)

            # Update session
            session.status = "completed"
            session.completed_at = datetime.now()
            await self.db.commit()

            # Export to knowledge base for Open WebUI
            try:
                self._log("Exporting scraped data to local knowledge base...", source="KB Export")
                kb_exporter = get_kb_exporter()
                export_result = await kb_exporter.export_session(self.db, session_id)
                self._log(f"Local KB exported: {export_result.get('total_files', 0)} markdown files created in knowledge_base/{brand.name}/", source="KB Export")
                
                # Process with Knowledge Synthesizer (LLM-powered extraction) - OPTIONAL
                use_synthesizer = False  # Set to True if you want summarized docs
                if use_synthesizer:
                    self._log(f"Starting Knowledge Synthesizer - Processing {len(all_scraped_data)} items with Gemini LLM...", source="Synthesizer")
                    self._log("This extracts quotes, sentiment, pain points from all scraped content (reviews, Reddit, forums, etc.)", source="Synthesizer")
                    try:
                        synthesizer = get_knowledge_synthesizer(output_dir="knowledge_base_processed", use_llm=True)
                        synth_result = await synthesizer.synthesize_session(
                            self.db, 
                            session_id,
                            progress_callback=lambda msg: self._log(msg, source="Synthesizer")
                        )
                        items_by_type = synth_result.get('items_by_type', {})
                        type_summary = ", ".join([f"{k}: {v}" for k, v in items_by_type.items()])
                        self._log(f"Synthesizer complete: {synth_result.get('items_processed', 0)} items processed ({type_summary})", source="Synthesizer")
                        self._log(f"Generated {len(synth_result.get('files_created', []))} structured documents: reviews_synthesis.md, discussions_insights.md, etc.", source="Synthesizer")
                    except Exception as synth_err:
                        self._log(f"Synthesizer failed (non-critical, RAG will use basic data): {synth_err}", level="warning", source="Synthesizer")
                else:
                    self._log("Skipping Knowledge Synthesizer (using raw docs for RAG)", source="Synthesizer")
                
                # Sync RAW documents to AnythingLLM workspace
                self._log(f"Syncing RAW documents to AnythingLLM workspace '{brand.name}'...", source="AnythingLLM")
                self._log("Uploading raw markdown files (reddit, trustpilot, etc) for RAG chat...", source="AnythingLLM")
                sync_result = await sync_brand_to_workspace(brand.name)  # Uses knowledge_base/ by default
                if sync_result.get('success'):
                    self._log(f"AnythingLLM sync complete: {sync_result.get('documents_uploaded', 0)} docs uploaded, workspace '{sync_result.get('workspace_slug')}' ready for chat", source="AnythingLLM")
                else:
                    self._log(f"AnythingLLM sync partial (some docs may not be indexed): {sync_result.get('errors', [])}", level="warning", source="AnythingLLM")
            except Exception as kb_err:
                self._log(f"Knowledge base export/sync failed (non-critical, data is still in DB): {kb_err}", level="warning", source="KB Export")
            
            print(f"\n{'='*50}")
            print(f"[+] Reprocessing COMPLETED for '{brand.name}'!")
            print(f"    Data points: {len(all_scraped_data)}")
            print(f"    ICPs: {len(insights.get('icps', []))}")
            print(f"    Pain points: {len(insights.get('pain_points', []))}")
            print(f"    Scripts: {len(insights.get('generated_scripts', []))}")
            print(f"{'='*50}")
            
        except Exception as e:
            session.status = "failed"
            await self.db.commit()
            print(f"[-] Reprocessing failed: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    async def run_incremental_research(
        self, 
        session_id: int, 
        brand_id: int, 
        skip_sources: List[str]
    ):
        """
        Run INCREMENTAL research - scrapes only new sources, merges with existing data.
        
        Args:
            session_id: Research session ID
            brand_id: Brand ID
            skip_sources: List of source types to skip (already scraped)
        """
        import asyncio
        
        self._session_id = session_id
        
        print(f"\n{'='*50}")
        print(f"[Incremental] Starting for session {session_id}")
        print(f"[Incremental] Skipping sources: {skip_sources}")
        print(f"{'='*50}")
        
        session = await self._get_session(session_id)
        brand = await self._get_brand(brand_id)
        
        session.status = "in_progress"
        await self.db.commit()
        
        try:
            # Step 1: Load existing scraped data
            self._update_progress("scraping", 1, 4, "Loading existing data...")
            result = await self.db.execute(
                select(ScrapedData).where(ScrapedData.session_id == session_id)
            )
            existing_records = result.scalars().all()
            
            # Convert to dicts
            all_scraped_data = []
            for record in existing_records:
                all_scraped_data.append({
                    "session_id": record.session_id,
                    "source_type": record.source_type,
                    "source_url": record.source_url,
                    "track": record.track,
                    "title": record.title,
                    "content": record.content,
                    "author": record.author,
                    "posted_at": str(record.posted_at) if record.posted_at else None,
                    "likes": record.likes,
                    "comments_count": record.comments_count,
                    "shares": record.shares,
                    "rating": record.rating,
                    "mention_type": record.mention_type,
                    "sentiment": record.sentiment,
                    "raw_data": record.raw_data
                })
            
            print(f"    [+] Loaded {len(all_scraped_data)} existing items")
            
            # Step 2: Generate queries if needed
            self._update_progress("scraping", 2, 4, "Preparing new source queries...")
            if not session.brand_queries:
                queries = await self.keyword_generator.generate(
                    brand_name=brand.name,
                    sector=brand.sector,
                    vertical=brand.vertical,
                    products=brand.products or [],
                    target_audience=brand.target_audience
                )
                session.brand_queries = queries.get("brand_queries", {})
                session.segment_queries = queries.get("segment_queries", {})
                await self.db.commit()
            else:
                queries = {
                    "brand_queries": session.brand_queries,
                    "segment_queries": session.segment_queries
                }
            
            # Step 3: Scrape only NEW sources
            self._update_progress("scraping", 3, 4, f"Scraping new sources (skipping {len(skip_sources)})...")
            new_data = await self._scrape_new_sources_only(
                session_id, brand.name, brand.sector, queries,
                skip_sources=skip_sources
            )
            
            if new_data:
                print(f"    [+] Scraped {len(new_data)} new items")
                # Analyze sentiment before saving (atomic)
                try:
                    from .sentiment import classify_sentiment
                    for data in new_data:
                        content = data.get("content") or data.get("title") or ""
                        if content and len(content.strip()) > 10 and not data.get("sentiment"):
                            try:
                                _sent, _score = classify_sentiment(content)
                                data["sentiment"] = _sent
                                data["sentiment_score"] = _score
                            except Exception:
                                data["sentiment"] = "neutral"
                                data["sentiment_score"] = 0.0
                except Exception:
                    pass
                # Save new data (with sentiment already set)
                for data in new_data:
                    filtered_data = filter_scraped_data(data)
                    data_obj = ScrapedData(**filtered_data)
                    self.db.add(data_obj)
                await self.db.commit()

                # Combine with existing
                all_scraped_data.extend(new_data)
            else:
                print("    [!] No new sources to scrape (all already exist)")
            
            # Step 4: Regenerate insights with all data
            self._update_progress("insights", 1, 3, "Regenerating insights with all data...")
            
            # Prepare brand info
            brand_info = {
                "name": brand.name,
                "sector": brand.sector or "Unknown",
                "vertical": brand.vertical or "",
                "description": brand.description or "",
                "target_audience": brand.target_audience or "",
                "products": brand.products or [],
                "value_propositions": [],
            }
            
            insights = await self.insights_generator.generate(
                brand_name=brand.name,
                brand_info=brand_info,
                scraped_data=all_scraped_data
            )
            
            # Add data summaries
            self._update_progress("insights", 2, 3, "Creating cross-source analysis...")
            data_summary = self._create_data_summary(all_scraped_data)
            insights["data_summary"] = data_summary
            insights["top_quotes"] = self._extract_top_quotes(all_scraped_data)
            
            # Persist sentiment scores to DB (non-blocking)
            await self._update_db_sentiment(session_id)
            
            cross_source = self._create_cross_source_insights(all_scraped_data, {})
            insights["cross_source_insights"] = cross_source
            
            # Generate content with timeout protection
            self._update_progress("insights", 3, 3, "Generating scripts and content...")
            ad_patterns = {}
            
            try:
                scripts, thumbnails, ab_tests = await asyncio.wait_for(
                    asyncio.gather(
                        self.script_generator.generate_scripts(brand_info, ad_patterns, insights, num_scripts=3),
                        self.thumbnail_suggester.suggest_thumbnails(brand_info, ad_patterns, insights, num_suggestions=3),
                        self.ab_test_suggester.suggest_tests(brand_info, ad_patterns, insights, num_tests=3)
                    ),
                    timeout=180.0  # 3 minute timeout for all generators
                )
            except asyncio.TimeoutError:
                print(f"       [!] Content generators timed out after 180 seconds, using fallbacks")
                add_session_log(self.session_id, "warning", "Content generators timed out, using fallbacks")
                scripts = []
                thumbnails = []
                ab_tests = []
            except Exception as e:
                print(f"       [!] Error in content generators: {e}")
                add_session_log(self.session_id, "warning", f"Content generators error: {str(e)[:100]}")
                scripts = []
                thumbnails = []
                ab_tests = []
            
            insights["generated_scripts"] = scripts
            insights["thumbnail_suggestions"] = thumbnails
            insights["ab_test_suggestions"] = ab_tests
            
            # Save insights
            existing_insight = await self.db.execute(
                select(Insight).where(Insight.session_id == session_id)
            )
            insight = existing_insight.scalar_one_or_none()
            
            if insight:
                # Update existing
                for key, value in insights.items():
                    if hasattr(insight, key):
                        setattr(insight, key, value)
            else:
                insight = Insight(session_id=session_id, **insights)
                self.db.add(insight)
            
            await self.db.commit()
            
            # Complete
            session.status = "completed"
            session.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
            
            print(f"[+] Incremental research completed!")
            print(f"    Total data points: {len(all_scraped_data)}")
            print(f"    New items added: {len(new_data) if new_data else 0}")
            
        except Exception as e:
            session.status = "failed"
            await self.db.commit()
            print(f"[-] Incremental research failed: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    async def _scrape_new_sources_only(
        self,
        session_id: int,
        brand_name: str,
        sector: str,
        queries: Dict,
        skip_sources: List[str]
    ) -> List[Dict[str, Any]]:
        """Scrape only sources that aren't in skip_sources."""
        new_data = []
        
        # Map of source types to scraping functions
        # Only scrape if source not in skip_sources
        
        # Website scraping
        if "website" not in skip_sources and "firecrawl_website" not in skip_sources:
            try:
                self._log("    [New] Scraping website content...")
                # Website scraping logic would go here
            except Exception as e:
                self._log(f"    [!] Website error: {str(e)[:50]}")
        
        # Reddit (using Firecrawl, NOT Apify - much cheaper!)
        if "reddit" not in skip_sources:
            try:
                self._log("    [New] Scraping Reddit via Firecrawl...")
                reddit_queries = queries.get("brand_queries", {}).get("reddit", [])[:3]
                if reddit_queries:
                    for query in reddit_queries:
                        posts = await self.firecrawl.search_reddit(query)
                        for post in posts[:15]:  # Limit to 15 posts per query
                            post["source_type"] = "reddit"
                            post["session_id"] = session_id
                            post["track"] = 1
                            new_data.append(post)
            except Exception as e:
                self._log(f"    [!] Reddit error: {str(e)[:50]}")
        
        # Twitter
        if "twitter" not in skip_sources:
            try:
                self._log("    [New] Scraping Twitter...")
                tweets = await self.apify.scrape_twitter([brand_name], track=1)
                for tweet in tweets:
                    tweet["source_type"] = "twitter"
                    tweet["session_id"] = session_id
                    tweet["track"] = 1
                    new_data.append(tweet)
            except Exception as e:
                self._log(f"    [!] Twitter error: {str(e)[:50]}")
        
        # TikTok
        if "tiktok" not in skip_sources:
            try:
                self._log("    [New] Scraping TikTok...")
                tiktoks = await self.apify.scrape_tiktok(brand_name, limit=15)
                for tiktok in tiktoks:
                    tiktok["source_type"] = "tiktok"
                    tiktok["session_id"] = session_id
                    tiktok["track"] = 1
                    new_data.append(tiktok)
            except Exception as e:
                self._log(f"    [!] TikTok error: {str(e)[:50]}")
        
        # Trustpilot
        if "trustpilot" not in skip_sources:
            try:
                self._log("    [New] Scraping Trustpilot reviews...")
                reviews = await self.firecrawl.scrape_trustpilot(brand_name, pages=2)
                for review in reviews:
                    review["source_type"] = "trustpilot"
                    review["session_id"] = session_id
                    review["track"] = 1
                    new_data.append(review)
            except Exception as e:
                self._log(f"    [!] Trustpilot error: {str(e)[:50]}")
        
        return new_data
    
    async def _get_session(self, session_id: int) -> ResearchSession:
        """Get research session by ID."""
        result = await self.db.execute(
            select(ResearchSession).where(ResearchSession.id == session_id)
        )
        return result.scalar_one()
    
    async def _get_brand(self, brand_id: int) -> Brand:
        """Get brand by ID."""
        result = await self.db.execute(
            select(Brand).where(Brand.id == brand_id)
        )
        return result.scalar_one()
    
    async def _scrape_track1(
        self, 
        session_id: int, 
        brand_name: str,
        sector: str,
        queries: Dict,
        competitors: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape Track 1: Brand Mentions
        """
        from datetime import datetime
        all_data = []
        brand_queries = queries.get("brand_queries", {})
        
        print(f"\n{'='*60}")
        print(f"[T1][{datetime.now().strftime('%H:%M:%S')}] STARTING TRACK 1: Brand Mentions for '{brand_name}'")
        print(f"{'='*60}")
        
        # 1. Reddit brand mentions (Firecrawl) + Deep Analysis
        print(f"    [T1][{datetime.now().strftime('%H:%M:%S')}] START: Reddit mentions...")
        reddit_items = []
        try:
            reddit_queries = brand_queries.get("reddit", [f'"{brand_name}" site:reddit.com'])
            print(f"       Queries: {reddit_queries[:2]}")
            for i, query in enumerate(reddit_queries[:3]):
                print(f"       [{datetime.now().strftime('%H:%M:%S')}] Reddit query {i+1}/3: {query[:40]}...")
                data = await self.firecrawl.search_reddit(query)
                for item in data:
                    reddit_items.append(item)
                    all_data.append({
                        "session_id": session_id,
                        "source_type": "reddit",
                        "track": 1,
                        "mention_type": "direct_brand",
                        **item
                    })
            print(f"    [T1][{datetime.now().strftime('%H:%M:%S')}] END: Reddit -> {len(reddit_items)} items")
        except Exception as e:
            print(f"    [T1][{datetime.now().strftime('%H:%M:%S')}] ERROR: Reddit scraping: {str(e)[:60]}")
        
        # NEW: Deep Reddit Analysis
        if reddit_items:
            print(f"       -> Analyzing {len(reddit_items)} Reddit posts with AI...")
            try:
                reddit_insights = await self.reddit_analyzer.analyze_reddit_content(
                    reddit_items,
                    brand_name=brand_name
                )
                
                if reddit_insights and reddit_insights.get("total_analyzed", 0) > 0:
                    insight_record = {
                        "session_id": session_id,
                        "source_type": "reddit_insights",
                        "track": 1,
                        "mention_type": "analysis",
                        "title": f"Reddit Analysis ({reddit_insights['total_analyzed']} posts)",
                        "content": json.dumps({
                            "sentiment": reddit_insights.get("overall_sentiment", {}).get("overall"),
                            "top_complaints": reddit_insights.get("recurring_complaints", [])[:3],
                            "top_praises": reddit_insights.get("recurring_praises", [])[:3],
                            "wish_patterns": [p["quote"][:80] for p in reddit_insights.get("wish_patterns", [])[:3]],
                            "verbatim_quotes": reddit_insights.get("verbatim_quotes", [])[:3]
                        }),
                        "raw_data": reddit_insights
                    }
                    all_data.append(insight_record)
                    
                    sentiment = reddit_insights.get("overall_sentiment", {})
                    print(f"       -> Reddit: {sentiment.get('overall', 'N/A')} sentiment, "
                          f"{len(reddit_insights.get('recurring_complaints', []))} complaints, "
                          f"{len(reddit_insights.get('wish_patterns', []))} wish patterns")
            except Exception as re:
                print(f"       [!] Reddit analysis error: {str(re)[:80]}")
        
        # 2. Reviews - Trustpilot (Firecrawl)
        print(f"    [T1][{datetime.now().strftime('%H:%M:%S')}] START: Trustpilot reviews...")
        all_reviews = []
        try:
            data = await self.firecrawl.scrape_trustpilot(brand_name)
            for item in data:
                all_reviews.append(item)
                all_data.append({
                    "session_id": session_id,
                    "source_type": "trustpilot",
                    "track": 1,
                    "mention_type": "direct_brand",
                    **item
                })
            print(f"    [T1][{datetime.now().strftime('%H:%M:%S')}] END: Trustpilot -> {len(data)} reviews")
        except Exception as e:
            print(f"    [T1][{datetime.now().strftime('%H:%M:%S')}] ERROR: Trustpilot: {str(e)[:60]}")
        
        # 3. General Reviews Search (Firecrawl)
        print(f"    [T1][{datetime.now().strftime('%H:%M:%S')}] START: Review sites search...")
        try:
            data = await self.firecrawl.search_reviews(brand_name)
            for item in data:
                all_reviews.append(item)
                all_data.append({
                    "session_id": session_id,
                    "source_type": item.get("source_type", "reviews"),
                    "track": 1,
                    "mention_type": "direct_brand",
                    **item
                })
            print(f"    [T1][{datetime.now().strftime('%H:%M:%S')}] END: Reviews -> {len(data)} items")
        except Exception as e:
            print(f"    [T1][{datetime.now().strftime('%H:%M:%S')}] ERROR: Reviews search: {str(e)[:60]}")
        
        # NEW: Deep Review Analysis
        if all_reviews:
            print(f"       -> Analyzing {len(all_reviews)} reviews with AI...")
            try:
                review_insights = await self.review_analyzer.analyze_reviews(
                    all_reviews,
                    brand_name=brand_name,
                    source_type="mixed_reviews"
                )
                
                if review_insights and review_insights.get("total_analyzed", 0) > 0:
                    rating_dist = review_insights.get("rating_distribution", {})
                    insight_record = {
                        "session_id": session_id,
                        "source_type": "review_insights",
                        "track": 1,
                        "mention_type": "analysis",
                        "title": f"Review Analysis ({review_insights['total_analyzed']} reviews)",
                        "content": json.dumps({
                            "avg_rating": review_insights.get("avg_rating"),
                            "positive_pct": rating_dist.get("positive_pct"),
                            "negative_pct": rating_dist.get("negative_pct"),
                            "top_complaints": [c.get("quote", "")[:80] for c in review_insights.get("top_complaints", [])[:3]],
                            "top_praises": [p.get("quote", "")[:80] for p in review_insights.get("top_praises", [])[:3]],
                            "deal_breakers": review_insights.get("deal_breakers", [])[:3]
                        }),
                        "raw_data": review_insights
                    }
                    all_data.append(insight_record)
                    
                    sentiment = review_insights.get("sentiment_summary", {})
                    print(f"       -> Reviews: {review_insights.get('avg_rating', 'N/A')}* avg, "
                          f"{sentiment.get('positive_pct', 0)}% positive, "
                          f"{len(review_insights.get('top_complaints', []))} complaints identified")
            except Exception as re:
                print(f"       [!] Review analysis error: {str(re)[:80]}")
        
        # 4. News and Blog mentions (Firecrawl)
        print(f"    [T1][{datetime.now().strftime('%H:%M:%S')}] START: News & blogs...")
        try:
            data = await self.firecrawl.search_news_mentions(brand_name)
            for item in data:
                all_data.append({
                    "session_id": session_id,
                    "source_type": "news_blog",
                    "track": 1,
                    "mention_type": "direct_brand",
                    **item
                })
            print(f"    [T1][{datetime.now().strftime('%H:%M:%S')}] END: News -> {len(data)} items")
        except Exception as e:
            print(f"    [T1][{datetime.now().strftime('%H:%M:%S')}] ERROR: News search: {str(e)[:60]}")
        
        # 5. Competitor comparisons (Firecrawl)
        print(f"    [T1][{datetime.now().strftime('%H:%M:%S')}] START: Competitor comparisons...")
        try:
            data = await self.firecrawl.search_competitors(brand_name, sector, competitors)
            for item in data:
                all_data.append({
                    "session_id": session_id,
                    "source_type": "competitor_comparison",
                    "track": 1,
                    "mention_type": "competitor_mention",
                    **item
                })
            print(f"    [T1][{datetime.now().strftime('%H:%M:%S')}] END: Competitors -> {len(data)} items")
        except Exception as e:
            print(f"    [T1][{datetime.now().strftime('%H:%M:%S')}] ERROR: Competitor search: {str(e)[:60]}")
        
        # 6. Social Media Scraping
        print(f"    [T1][{datetime.now().strftime('%H:%M:%S')}] START: Social Media (Twitter/TikTok/Instagram/Facebook)...")
        
        # Strategy: Try free scrapers first, use Apify if available for fallback/primary
        
        # Twitter - use Apify (social_free/Nitter is dead since 2024)
        twitter_queries = brand_queries.get("twitter", [brand_name])
        twitter_data = []
        if self.apify.is_available:
            try:
                twitter_data = await self.apify.scrape_twitter(twitter_queries, track=1)
            except Exception as e:
                print(f"       [!] Twitter Apify: {str(e)[:60]}")
        
        for item in twitter_data:
            all_data.append({
                "session_id": session_id,
                "source_type": "twitter",
                "track": 1,
                "mention_type": "direct_brand",
                **item
            })
        
        if twitter_data:
            print(f"       -> {len(twitter_data)} tweets collected")
            
            # NEW: Deep Twitter Analysis
            print(f"       -> Analyzing tweets with AI...")
            try:
                twitter_insights = await self.twitter_analyzer.analyze_tweets(
                    twitter_data, 
                    brand_name=brand_name
                )
                
                if twitter_insights and twitter_insights.get("total_analyzed", 0) > 0:
                    # Store top performing tweets as quotable content
                    top_tweets = twitter_insights.get("top_performing_tweets", [])[:5]
                    
                    insight_record = {
                        "session_id": session_id,
                        "source_type": "twitter_insights",
                        "track": 1,
                        "mention_type": "analysis",
                        "title": f"Twitter/X Analysis ({twitter_insights['total_analyzed']} tweets)",
                        "content": json.dumps({
                            "sentiment": twitter_insights.get("sentiment", {}).get("overall"),
                            "top_hashtags": list(twitter_insights.get("hashtags", {}).keys())[:5],
                            "key_topics": list(twitter_insights.get("topics", {}).keys())[:5],
                            "winning_hooks": twitter_insights.get("common_hooks", [])[:3],
                            "top_tweets": [{"content": t["content"][:200], "likes": t["likes"]} for t in top_tweets]
                        }),
                        "raw_data": twitter_insights
                    }
                    all_data.append(insight_record)
                    
                    sentiment = twitter_insights.get("sentiment", {})
                    print(f"       -> Twitter: {sentiment.get('overall', 'N/A')} sentiment, "
                          f"{len(twitter_insights.get('common_hooks', []))} hooks identified, "
                          f"top tweet: {twitter_insights.get('engagement_stats', {}).get('max_likes', 0)} likes")
            except Exception as te:
                print(f"       [!] Twitter analysis error: {str(te)[:80]}")
        
        # Instagram - try free with login first, then Apify
        ig_queries = brand_queries.get("instagram", [brand_name])
        ig_data = await self.social_free.scrape_instagram_hashtags(ig_queries, limit=20)
        if not ig_data and self.apify.is_available:
            try:
                ig_data = await self.apify.scrape_instagram(ig_queries, track=1)
            except Exception as e:
                print(f"       [!] Instagram Apify: {str(e)[:60]}")
        for item in ig_data:
            all_data.append({
                "session_id": session_id,
                "source_type": "instagram",
                "track": 1,
                "mention_type": "direct_brand",
                **item
            })
        if ig_data:
            print(f"       -> {len(ig_data)} Instagram posts")
        
        # TikTok - Apify only (free library broken on Windows)
        if self.apify.is_available:
            try:
                tiktok_queries = brand_queries.get("tiktok", [brand_name])
                tiktok_data = await self.apify.scrape_tiktok(tiktok_queries, track=1)
                for item in tiktok_data:
                    all_data.append({
                        "session_id": session_id,
                        "source_type": "tiktok",
                        "track": 1,
                        "mention_type": "direct_brand",
                        **item
                    })
                if tiktok_data:
                    print(f"       -> {len(tiktok_data)} TikTok videos")
            except Exception as e:
                print(f"       [!] TikTok Apify: {str(e)[:60]}")
        
        # Facebook - Apify only
        if self.apify.is_available:
            try:
                fb_data = await self.apify.scrape_facebook([brand_name])
                for item in fb_data:
                    all_data.append({
                        "session_id": session_id,
                        "source_type": "facebook",
                        "track": 1,
                        "mention_type": "direct_brand",
                        **item
                    })
                if fb_data:
                    print(f"       -> {len(fb_data)} Facebook posts")
            except Exception as e:
                print(f"       [!] Facebook Apify: {str(e)[:60]}")
        
        if not self.apify.is_available:
            print("       [!] Apify not configured - set APIFY_API_TOKEN in .env for TikTok/Facebook")
        
        # 7. YouTube comments/videos (Firecrawl for search, free scraper for comments + LLM analysis)
        print("    -> YouTube videos & comments...")
        try:
            # First use Firecrawl to find videos
            data = await self.firecrawl.search_youtube_comments(brand_name)
            video_urls = []
            
            for item in data:
                all_data.append({
                    "session_id": session_id,
                    "source_type": "youtube",
                    "track": 1,
                    "mention_type": "direct_brand",
                    **item
                })
                if item.get("source_url"):
                    video_urls.append({
                        "url": item["source_url"],
                        "title": item.get("title", ""),
                        "description": item.get("content", "")
                    })
            
            # Then scrape comments from top videos using free scraper
            all_youtube_comments = []
            per_video_comments = {}  # {url: [comments]}
            if video_urls and self.social_free.youtube_available:
                print(f"       -> Scraping comments from {min(3, len(video_urls))} videos...")
                for video_info in video_urls[:3]:
                    url = video_info["url"]
                    try:
                        comments = await self.social_free.scrape_youtube_comments(url, limit=50)
                        per_video_comments[url] = comments
                        for comment in comments:
                            comment_data = {
                                "session_id": session_id,
                                "source_type": "youtube_comment",
                                "track": 1,
                                "mention_type": "direct_brand",
                                **comment
                            }
                            all_data.append(comment_data)
                            all_youtube_comments.append(comment)
                    except Exception as ce:
                        print(f"       [!] Error getting comments for video: {str(ce)[:80]}")

            # Analyze YouTube content: per-video analysis + aggregation
            if all_youtube_comments or video_urls:
                try:
                    analyzed_videos = []
                    for video_info in video_urls[:3]:
                        url = video_info["url"]
                        vid_comments = per_video_comments.get(url, [])
                        print(f"       -> Analyzing video: {video_info.get('title', url)[:60]} ({len(vid_comments)} comments)")
                        vid_result = await self.youtube_analyzer.analyze_youtube_content(
                            video_url=url,
                            comments=vid_comments,
                            video_title=video_info.get("title", ""),
                            video_description=video_info.get("description", ""),
                            brand_name=brand_name,
                            analyze_video=False  # Skip expensive video download/upload
                        )
                        if vid_result:
                            analyzed_videos.append(vid_result)

                    # Aggregate insights across all analyzed videos
                    if analyzed_videos:
                        aggregated = await self.youtube_analyzer.aggregate_youtube_insights(analyzed_videos)

                        # Store aggregated insights
                        total_comments = aggregated.get("total_comments_analyzed", 0)
                        video_titles = [v.get("title", "") for v in video_urls[:3] if v.get("title")]
                        insight_record = {
                            "session_id": session_id,
                            "source_type": "youtube_insights",
                            "track": 1,
                            "mention_type": "analysis",
                            "title": f"YouTube Analysis ({aggregated['videos_analyzed']} videos, {total_comments} comments)",
                            "content": json.dumps({
                                "video_titles": video_titles,
                                "sentiment": aggregated.get("overall_sentiment"),
                                "pain_points": aggregated.get("top_pain_points", [])[:5],
                                "faqs": aggregated.get("top_faqs", [])[:5],
                                "pros": aggregated.get("product_pros", [])[:5],
                                "cons": aggregated.get("product_cons", [])[:5],
                                "quotable_moments": aggregated.get("quotable_moments", [])[:3]
                            }),
                            "raw_data": aggregated
                        }
                        all_data.append(insight_record)
                        print(f"       -> YouTube aggregated: {aggregated['videos_analyzed']} videos, "
                              f"{total_comments} comments, "
                              f"{len(aggregated.get('top_pain_points', []))} pain points")
                except Exception as ae:
                    print(f"       [!] YouTube analysis error: {str(ae)[:80]}")
            
            yt_count = len([d for d in all_data if d.get('source_type') in ['youtube', 'youtube_comment', 'youtube_insights']])
            if yt_count > 0:
                print(f"       -> {yt_count} items from YouTube")
        except Exception as e:
            print(f"    [!] YouTube search error: {str(e)[:100]}")
        
        # 8. Quora questions (Firecrawl)
        print("    -> Quora questions...")
        try:
            keywords = brand_queries.get("general", [sector])[:3]
            data = await self.firecrawl.search_quora(brand_name, keywords)
            for item in data:
                all_data.append({
                    "session_id": session_id,
                    "source_type": "quora",
                    "track": 1,
                    "mention_type": "direct_brand",
                    **item
                })
        except Exception as e:
            print(f"    [!] Quora search error: {e}")
        
        # 9. Product Hunt (Firecrawl)
        print("    -> Product Hunt...")
        try:
            data = await self.firecrawl.search_product_hunt(brand_name)
            for item in data:
                all_data.append({
                    "session_id": session_id,
                    "source_type": "product_hunt",
                    "track": 1,
                    "mention_type": "direct_brand",
                    **item
                })
        except Exception as e:
            print(f"    [!] Product Hunt search error: {e}")
        
        # 10. App Store / Play Store reviews (Firecrawl)
        print("    -> App store reviews...")
        try:
            data = await self.firecrawl.search_app_store_reviews(brand_name)
            for item in data:
                all_data.append({
                    "session_id": session_id,
                    "source_type": item.get("source_type", "app_store"),
                    "track": 1,
                    "mention_type": "direct_brand",
                    **item
                })
        except Exception as e:
            print(f"    [!] App store search error: {e}")
        
        # 11. Medium articles (Firecrawl)
        print(f"    [T1][{datetime.now().strftime('%H:%M:%S')}] START: Medium articles...")
        try:
            keywords = brand_queries.get("general", [sector])[:2]
            data = await self.firecrawl.search_medium_articles(brand_name, keywords)
            for item in data:
                all_data.append({
                    "session_id": session_id,
                    "source_type": "medium",
                    "track": 1,
                    "mention_type": "direct_brand",
                    **item
                })
            print(f"    [T1][{datetime.now().strftime('%H:%M:%S')}] END: Medium -> {len(data)} items")
        except Exception as e:
            print(f"    [T1][{datetime.now().strftime('%H:%M:%S')}] ERROR: Medium: {str(e)[:60]}")
        
        # 12. LinkedIn posts (Firecrawl)
        print(f"    [T1][{datetime.now().strftime('%H:%M:%S')}] START: LinkedIn posts...")
        try:
            data = await self.firecrawl.search_linkedin_posts(brand_name)
            for item in data:
                all_data.append({
                    "session_id": session_id,
                    "source_type": "linkedin",
                    "track": 1,
                    "mention_type": "direct_brand",
                    **item
                })
            print(f"    [T1][{datetime.now().strftime('%H:%M:%S')}] END: LinkedIn -> {len(data)} items")
        except Exception as e:
            print(f"    [T1][{datetime.now().strftime('%H:%M:%S')}] ERROR: LinkedIn: {str(e)[:60]}")
        
        print(f"\n{'='*60}")
        print(f"[T1][{datetime.now().strftime('%H:%M:%S')}] TRACK 1 COMPLETE: {len(all_data)} total items")
        print(f"{'='*60}\n")
        return all_data
    
    async def _scrape_track2(
        self,
        session_id: int,
        sector: str,
        queries: Dict
    ) -> List[Dict[str, Any]]:
        """
        Scrape Track 2: Segment Research
        """
        all_data = []
        segment_queries = queries.get("segment_queries", {})
        
        # 1. Reddit - Subreddits (Firecrawl)
        print("    -> Subreddits...")
        try:
            subreddits = segment_queries.get("subreddits", [])
            for subreddit in subreddits[:5]:
                data = await self.firecrawl.scrape_subreddit(subreddit)
                for item in data:
                    all_data.append({
                        "session_id": session_id,
                        "source_type": "reddit",
                        "track": 2,
                        "mention_type": "segment_discussion",
                        **item
                    })
        except Exception as e:
            print(f"    [!] Subreddit scraping error: {e}")
        
        # 1.5. Reddit - Problem-focused searches (Firecrawl)
        print("    -> Reddit problem searches...")
        try:
            reddit_searches = segment_queries.get("reddit_searches", [])
            for query in reddit_searches[:5]:
                data = await self.firecrawl.search_reddit(query)
                for item in data:
                    all_data.append({
                        "session_id": session_id,
                        "source_type": "reddit",
                        "track": 2,
                        "mention_type": "problem_discussion",
                        **item
                    })
            if reddit_searches:
                print(f"       -> Found {len(all_data)} Reddit problem discussions")
        except Exception as e:
            print(f"    [!] Reddit problem search error: {e}")
        
        # 2. Forums (Firecrawl)
        print("    -> Forums...")
        try:
            forum_queries = segment_queries.get("forums", [])
            for query in forum_queries[:5]:
                data = await self.firecrawl.search_forums(query)
                for item in data:
                    all_data.append({
                        "session_id": session_id,
                        "source_type": "forum",
                        "track": 2,
                        "mention_type": "segment_discussion",
                        **item
                    })
        except Exception as e:
            print(f"    [!] Forum scraping error: {e}")
        
        # 3. Deep Segment Search (Firecrawl)
        print("    -> Deep segment search...")
        try:
            keywords = segment_queries.get("keywords", []) + segment_queries.get("problems", [])
            if keywords:
                data = await self.firecrawl.deep_search_segment(keywords, sector)
                for item in data:
                    all_data.append({
                        "session_id": session_id,
                        "source_type": item.get("source_type", "web"),
                        "track": 2,
                        "mention_type": "problem_discussion",
                        **item
                    })
        except Exception as e:
            print(f"    [!] Deep segment search error: {e}")
        
        # 3.5. Quora Questions (Firecrawl)
        print("    -> Quora questions...")
        try:
            quora_questions = segment_queries.get("quora_questions", [])
            for question in quora_questions[:5]:
                # Use Firecrawl search with site:quora.com
                async with httpx.AsyncClient(timeout=self.firecrawl.timeout) as client:
                    response = await self.firecrawl._rate_limited_request(
                        client, "POST",
                        f"{self.firecrawl.base_url}/search",
                        json={
                            "query": f"{question} site:quora.com",
                            "limit": 10
                        }
                    )
                    if response:
                        data = response.json()
                        for item in data.get("data", []):
                            all_data.append({
                                "session_id": session_id,
                                "source_type": "quora",
                                "track": 2,
                                "mention_type": "problem_discussion",
                                "source_url": item.get("url"),
                                "title": item.get("title"),
                                "content": item.get("description", ""),
                                "raw_data": item
                            })
            if quora_questions:
                print(f"       -> Found Quora discussions for {len(quora_questions)} questions")
        except Exception as e:
            print(f"    [!] Quora questions error: {e}")
        
        # 4. Social Media Hashtags (Free scrapers first, Apify as fallback)
        
        # Social media hashtags (segment discussions)
        # Note: Free scrapers are mostly broken in 2024, using Apify if available
        print("    -> Social Media segment hashtags...")
        
        # Twitter hashtags and problem searches - use Apify (Nitter/social_free is dead)
        twitter_hashtags = segment_queries.get("twitter_hashtags", [])
        twitter_problem_searches = segment_queries.get("twitter_problem_searches", [])
        twitter_queries = twitter_hashtags + twitter_problem_searches
        
        if twitter_queries and self.apify.is_available:
            try:
                twitter_data = await self.apify.scrape_twitter(twitter_queries[:5], track=2)
                for item in twitter_data:
                    all_data.append({
                        "session_id": session_id,
                        "source_type": "twitter",
                        "track": 2,
                        "mention_type": "segment_discussion",
                        **item
                    })
                if twitter_data:
                    print(f"       -> {len(twitter_data)} tweets from segment search")
            except Exception as e:
                print(f"       [!] Twitter segment search error: {str(e)[:60]}")
        
        # TikTok and Instagram via Apify only (free scrapers are broken)
        if self.apify.is_available:
            # TikTok hashtags
            tiktok_hashtags = segment_queries.get("tiktok_hashtags", [])
            if tiktok_hashtags:
                try:
                    tiktok_data = await self.apify.scrape_tiktok(tiktok_hashtags, track=2)
                    for item in tiktok_data:
                        all_data.append({
                            "session_id": session_id,
                            "source_type": "tiktok",
                            "track": 2,
                            "mention_type": "segment_discussion",
                            **item
                        })
                    if tiktok_data:
                        print(f"       -> {len(tiktok_data)} TikTok videos via Apify")
                except Exception as e:
                    print(f"       [!] TikTok Apify error: {str(e)[:80]}")
            
            # Instagram hashtags
            ig_hashtags = segment_queries.get("instagram_hashtags", [])
            if ig_hashtags:
                try:
                    ig_data = await self.apify.scrape_instagram(ig_hashtags, track=2)
                    for item in ig_data:
                        all_data.append({
                            "session_id": session_id,
                            "source_type": "instagram",
                            "track": 2,
                            "mention_type": "segment_discussion",
                            **item
                        })
                    if ig_data:
                        print(f"       -> {len(ig_data)} Instagram posts via Apify")
                except Exception as e:
                    print(f"       [!] Instagram Apify error: {str(e)[:80]}")
        
        # Amazon Reviews (Apify only)
        if self.apify.is_available:
            print("    -> Amazon reviews (Apify)...")
            try:
                amazon_queries = segment_queries.get("amazon_products", [])
                if amazon_queries:
                    data = await self.apify.scrape_amazon_reviews(amazon_queries)
                    for item in data:
                        all_data.append({
                            "session_id": session_id,
                            "source_type": "amazon_reviews",
                            "track": 2,
                            "mention_type": "segment_discussion",
                            **item
                        })
                    print(f"       -> {len(data)} reviews de Amazon")
            except Exception as e:
                print(f"    [!] Amazon reviews scraping error: {e}")
        
        # Google Reviews - Use Firecrawl (free) as primary, Apify as fallback
        google_queries = segment_queries.get("google_business", [])
        if google_queries:
            print("    -> Google reviews...")
            google_data = []
            
            # PRIMARY: Firecrawl (free)
            if self.firecrawl.has_key:
                try:
                    google_data = await self.firecrawl.scrape_google_reviews(google_queries[:5])
                    if google_data:
                        print(f"       -> {len(google_data)} reviews via Firecrawl (free)")
                except Exception as e:
                    print(f"       Firecrawl error: {str(e)[:50]}")
            
            # FALLBACK: Apify only if enabled and Firecrawl failed
            if not google_data and settings.APIFY_ENABLE_GOOGLE_PLACES and self.apify.is_available:
                try:
                    google_queries = google_queries[:settings.APIFY_MAX_GOOGLE_PLACES]
                    google_data = await self.apify.scrape_google_reviews(google_queries)
                    print(f"       -> {len(google_data)} reviews via Apify")
                except Exception as e:
                    print(f"       Apify error: {str(e)[:50]}")
            
            for item in google_data:
                all_data.append({
                    "session_id": session_id,
                    "source_type": "google_reviews",
                    "track": 2,
                    "mention_type": "segment_discussion",
                    **item
                })
        
        print(f"    [+] Track 2: {len(all_data)} items scraped")
        return all_data
    
    # =============================================
    # PARALLEL SCRAPING METHODS
    # =============================================
    
    async def _scrape_track1_parallel(
        self,
        session_id: int,
        brand_name: str,
        sector: str,
        queries: Dict,
        competitors: List[str] = None,
        social_media_urls: Dict[str, str] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape Track 1 with ALL scrapers running in parallel.
        Uses asyncio.gather for maximum speed.
        
        Args:
            session_id: Research session ID
            brand_name: Name of the brand
            sector: Industry sector
            queries: Generated queries dict
            competitors: List of competitor names
            social_media_urls: Dict with social platform URLs from brand.social_media_urls
                               e.g. {"instagram": "https://instagram.com/hims", "twitter": "..."}
        """
        import asyncio
        
        brand_queries = queries.get("brand_queries", {})
        all_data = []
        
        # Extract usernames from social_media_urls if available
        instagram_username = None
        if social_media_urls and social_media_urls.get("instagram"):
            # Extract username from URL like https://instagram.com/hims
            ig_url = social_media_urls["instagram"]
            import re
            match = re.search(r'instagram\.com/([^/?]+)', ig_url)
            if match:
                instagram_username = match.group(1)
                print(f"    [Instagram] Found brand username: @{instagram_username}")
        
        # Also extract TikTok username from social_media_urls if available
        # This ensures the brand's own TikTok is searched first (as a primary query)
        tiktok_username = None
        if social_media_urls and social_media_urls.get("tiktok"):
            tiktok_url = social_media_urls["tiktok"]
            import re
            match = re.search(r'tiktok\.com/@([^/?]+)', tiktok_url)
            if match:
                tiktok_username = match.group(1)
                print(f"    [TikTok] Found brand username: @{tiktok_username}")
        
        # Define all scraping tasks
        async def scrape_reddit():
            results = []
            try:
                reddit_queries = brand_queries.get("reddit", [f'"{brand_name}" site:reddit.com'])
                for query in reddit_queries[:3]:
                    data = await self.firecrawl.search_reddit(query)
                    for item in data:
                        results.append({"session_id": session_id, "source_type": "reddit", "track": 1, "mention_type": "direct_brand", **item})
            except Exception as e:
                print(f"    [!] Reddit: {str(e)[:60]}")
            return results
        
        async def scrape_trustpilot():
            results = []
            try:
                data = await self.firecrawl.scrape_trustpilot(brand_name)
                for item in data:
                    results.append({"session_id": session_id, "source_type": "trustpilot", "track": 1, "mention_type": "direct_brand", **item})
            except Exception as e:
                print(f"    [!] Trustpilot: {str(e)[:60]}")
            return results
        
        async def scrape_reviews():
            results = []
            try:
                data = await self.firecrawl.search_reviews(brand_name)
                for item in data:
                    results.append({"session_id": session_id, "source_type": item.get("source_type", "reviews"), "track": 1, "mention_type": "direct_brand", **item})
            except Exception as e:
                print(f"    [!] Reviews: {str(e)[:60]}")
            return results
        
        async def scrape_news():
            results = []
            try:
                data = await self.firecrawl.search_news_mentions(brand_name)
                for item in data:
                    results.append({"session_id": session_id, "source_type": "news_blog", "track": 1, "mention_type": "direct_brand", **item})
            except Exception as e:
                print(f"    [!] News: {str(e)[:60]}")
            return results
        
        async def scrape_competitors():
            results = []
            try:
                data = await self.firecrawl.search_competitors(brand_name, sector, competitors)
                for item in data:
                    results.append({"session_id": session_id, "source_type": "competitor_comparison", "track": 1, "mention_type": "competitor_mention", **item})
            except Exception as e:
                print(f"    [!] Competitors: {str(e)[:60]}")
            return results
        
        async def scrape_twitter():
            """Scrape Twitter/X using Apify (social_free Nitter is dead in 2024)."""
            results = []
            try:
                twitter_queries = brand_queries.get("twitter", [brand_name])
                print(f"    [Twitter] Queries: {twitter_queries[:3]}")
                
                # Use Apify directly - social_free nitter is dead
                if self.apify.is_available:
                    print(f"    [Twitter] Calling Apify...")
                    data = await self.apify.scrape_twitter(twitter_queries[:5], track=1)
                    print(f"    [Twitter] Apify returned: {len(data)} items")
                    for item in data:
                        results.append({"session_id": session_id, "source_type": "twitter", "track": 1, "mention_type": "direct_brand", **item})
                else:
                    print(f"    [Twitter] Apify not available, skipping")
                print(f"    [Twitter] Total results: {len(results)}")
            except Exception as e:
                print(f"    [!] Twitter ERROR: {type(e).__name__}: {str(e)[:100]}")
            return results
        
        async def scrape_instagram_profile_task():
            """Scrape brand's own Instagram profile (separate task with own timeout)."""
            results = []
            if not instagram_username or not self.apify.is_available:
                return results
            try:
                print(f"    [InstagramProfile] Scraping brand profile: @{instagram_username}")
                profile_data = await self.apify.scrape_instagram_profile(instagram_username, max_posts=50)
                print(f"    [InstagramProfile] Brand profile returned: {len(profile_data)} posts")
                for item in profile_data:
                    results.append({
                        "session_id": session_id,
                        "source_type": "instagram_profile",
                        "track": 1,
                        "mention_type": "brand_content",
                        **item
                    })
            except Exception as e:
                print(f"    [!] InstagramProfile error: {str(e)[:80]}")
            return results

        async def scrape_instagram_mentions():
            """Search for brand mentions on Instagram (separate task with own timeout)."""
            results = []
            if not self.apify.is_available:
                return results
            ig_queries = brand_queries.get("instagram", [brand_name])
            if not ig_queries:
                return results
            try:
                print(f"    [InstagramMentions] Searching for brand mentions: {ig_queries[:3]}")
                mention_data = await self.apify.scrape_instagram(ig_queries[:5], track=1)
                print(f"    [InstagramMentions] Mentions search returned: {len(mention_data)} items")
                for item in mention_data:
                    if item.get("author", "").lower() != (instagram_username or "").lower():
                        results.append({
                            "session_id": session_id,
                            "source_type": "instagram",
                            "track": 1,
                            "mention_type": "direct_brand",
                            **item
                        })
            except Exception as e:
                print(f"    [!] InstagramMentions error: {str(e)[:80]}")
            return results
        
        async def scrape_tiktok():
            results = []
            print(f"    [TikTok] Apify available: {self.apify.is_available}")
            if self.apify.is_available:
                try:
                    tiktok_queries = brand_queries.get("tiktok", [brand_name])
                    # If we have the brand's TikTok handle, prepend it as first query
                    # This ensures @methodiq content is searched first
                    if tiktok_username and tiktok_username not in tiktok_queries:
                        tiktok_queries = [tiktok_username] + tiktok_queries
                    print(f"    [TikTok] Queries: {tiktok_queries[:3]}")
                    print(f"    [TikTok] Calling Apify...")
                    data = await self.apify.scrape_tiktok(tiktok_queries, track=1)
                    print(f"    [TikTok] Apify returned: {len(data)} items")
                    for item in data:
                        results.append({"session_id": session_id, "source_type": "tiktok", "track": 1, "mention_type": "direct_brand", **item})
                    print(f"    [TikTok] Total results: {len(results)}")
                    
                    # Analyze TikTok videos with Gemini
                    if results and len([r for r in results if r.get('source_url')]) > 0:
                        print(f"    [TikTok] Analyzing videos with Gemini (max 20)...")
                        try:
                            analyzed = await self.social_analyzer.analyze_social_content(
                                results, platform="tiktok", max_videos=20
                            )
                            # Update results with analysis
                            for i, item in enumerate(analyzed):
                                if i < len(results) and item.get('video_analysis'):
                                    results[i]['video_analysis'] = item['video_analysis']
                        except Exception as e:
                            print(f"    [!] TikTok video analysis error: {e}")
                except Exception as e:
                    print(f"    [!] TikTok ERROR: {type(e).__name__}: {str(e)[:100]}")
            else:
                print(f"    [TikTok] Skipped - Apify not available")
            return results
        
        async def scrape_facebook():
            """Scrape Facebook posts using Apify."""
            results = []
            try:
                print(f"    [Facebook] Apify available: {self.apify.is_available}")
                if self.apify.is_available:
                    print(f"    [Facebook] Calling Apify...")
                    data = await self.apify.scrape_facebook([brand_name])
                    print(f"    [Facebook] Apify returned: {len(data)} items")
                    for item in data:
                        results.append({"session_id": session_id, "source_type": "facebook", "track": 1, "mention_type": "direct_brand", **item})
                print(f"    [Facebook] Total results: {len(results)}")
            except Exception as e:
                print(f"    [!] Facebook ERROR: {type(e).__name__}: {str(e)[:100]}")
            return results
        
        async def scrape_youtube():
            results = []
            try:
                data = await self.firecrawl.search_youtube_comments(brand_name)
                video_urls = []
                for item in data:
                    results.append({"session_id": session_id, "source_type": "youtube", "track": 1, "mention_type": "direct_brand", **item})
                    if item.get("source_url"):
                        video_urls.append(item["source_url"])
                # Scrape comments from top videos
                if video_urls and self.social_free.youtube_available:
                    for url in video_urls[:2]:
                        try:
                            comments = await self.social_free.scrape_youtube_comments(url, limit=20)
                            for comment in comments:
                                results.append({"session_id": session_id, "source_type": "youtube_comment", "track": 1, "mention_type": "direct_brand", **comment})
                        except:
                            pass
            except Exception as e:
                print(f"    [!] YouTube: {str(e)[:60]}")
            return results
        
        async def scrape_quora():
            results = []
            try:
                keywords = brand_queries.get("general", [sector])[:3]
                data = await self.firecrawl.search_quora(brand_name, keywords)
                for item in data:
                    results.append({"session_id": session_id, "source_type": "quora", "track": 1, "mention_type": "direct_brand", **item})
            except Exception as e:
                print(f"    [!] Quora: {str(e)[:60]}")
            return results
        
        async def scrape_product_hunt():
            results = []
            try:
                data = await self.firecrawl.search_product_hunt(brand_name)
                for item in data:
                    results.append({"session_id": session_id, "source_type": "product_hunt", "track": 1, "mention_type": "direct_brand", **item})
            except Exception as e:
                print(f"    [!] Product Hunt: {str(e)[:60]}")
            return results
        
        async def scrape_app_stores():
            results = []
            try:
                data = await self.firecrawl.search_app_store_reviews(brand_name)
                for item in data:
                    results.append({"session_id": session_id, "source_type": item.get("source_type", "app_store"), "track": 1, "mention_type": "direct_brand", **item})
            except Exception as e:
                print(f"    [!] App Store: {str(e)[:60]}")
            return results
        
        async def scrape_medium():
            results = []
            try:
                keywords = brand_queries.get("general", [sector])[:2]
                data = await self.firecrawl.search_medium_articles(brand_name, keywords)
                for item in data:
                    results.append({"session_id": session_id, "source_type": "medium", "track": 1, "mention_type": "direct_brand", **item})
            except Exception as e:
                print(f"    [!] Medium: {str(e)[:60]}")
            return results
        
        async def scrape_linkedin():
            results = []
            try:
                data = await self.firecrawl.search_linkedin_posts(brand_name)
                for item in data:
                    results.append({"session_id": session_id, "source_type": "linkedin", "track": 1, "mention_type": "direct_brand", **item})
            except Exception as e:
                print(f"    [!] LinkedIn: {str(e)[:60]}")
            return results
        
        # RUN SCRAPERS IN BATCHES TO AVOID RATE LIMITING
        # Firecrawl scrapers: run sequentially (one at a time) 
        # Social scrapers (Apify/free): run in parallel
        
        from datetime import datetime
        SCRAPER_TIMEOUT = 30  # Max seconds per individual scraper
        
        print(f"    [{datetime.now().strftime('%H:%M:%S')}] [Sequential] Running Firecrawl scrapers one by one (timeout={SCRAPER_TIMEOUT}s)...")
        
        # BATCH 1: Firecrawl scrapers (sequential to avoid 429)
        firecrawl_scrapers = [
            ("Reddit", scrape_reddit),
            ("Trustpilot", scrape_trustpilot),
            ("Reviews", scrape_reviews),
            ("News", scrape_news),
            ("Competitors", scrape_competitors),
            ("YouTube", scrape_youtube),
            ("Quora", scrape_quora),
            ("ProductHunt", scrape_product_hunt),
            ("AppStore", scrape_app_stores),
            ("Medium", scrape_medium),
            ("LinkedIn", scrape_linkedin),
        ]
        
        for name, scraper_fn in firecrawl_scrapers:
            start_time = datetime.now()
            print(f"       [{start_time.strftime('%H:%M:%S')}] START: {name}...")
            try:
                # Wrap each scraper with a timeout
                result = await asyncio.wait_for(scraper_fn(), timeout=SCRAPER_TIMEOUT)
                elapsed = (datetime.now() - start_time).total_seconds()
                if result:
                    all_data.extend(result)
                    print(f"       [{datetime.now().strftime('%H:%M:%S')}] [+] {name}: {len(result)} items ({elapsed:.1f}s)")
                else:
                    print(f"       [{datetime.now().strftime('%H:%M:%S')}] [-] {name}: 0 items ({elapsed:.1f}s)")
            except asyncio.TimeoutError:
                elapsed = (datetime.now() - start_time).total_seconds()
                print(f"       [{datetime.now().strftime('%H:%M:%S')}] [TIMEOUT] {name}: exceeded {SCRAPER_TIMEOUT}s ({elapsed:.1f}s)")
            except Exception as e:
                elapsed = (datetime.now() - start_time).total_seconds()
                print(f"       [{datetime.now().strftime('%H:%M:%S')}] [!] {name}: {str(e)[:50]} ({elapsed:.1f}s)")
        
        # BATCH 2: Social scrapers (parallel - they use different APIs)
        SOCIAL_TIMEOUT = 90  # Increased: Social scrapers can be slow (Apify actors)
        print(f"    [{datetime.now().strftime('%H:%M:%S')}] [Parallel] Running social scrapers (timeout={SOCIAL_TIMEOUT}s)...")
        
        async def timed_scraper(name, fn):
            """Wrapper to add timeout to each social scraper."""
            start = datetime.now()
            try:
                result = await asyncio.wait_for(fn(), timeout=SOCIAL_TIMEOUT)
                elapsed = (datetime.now() - start).total_seconds()
                return (name, result, elapsed, None)
            except asyncio.TimeoutError:
                elapsed = (datetime.now() - start).total_seconds()
                return (name, [], elapsed, f"TIMEOUT after {SOCIAL_TIMEOUT}s")
            except Exception as e:
                elapsed = (datetime.now() - start).total_seconds()
                return (name, [], elapsed, str(e)[:50])
        
        social_results = await asyncio.gather(
            timed_scraper("Twitter", scrape_twitter),
            timed_scraper("InstagramProfile", scrape_instagram_profile_task),
            timed_scraper("InstagramMentions", scrape_instagram_mentions),
            timed_scraper("TikTok", scrape_tiktok),
            timed_scraper("Facebook", scrape_facebook),
        )
        
        for name, result, elapsed, error in social_results:
            if error:
                print(f"       [{datetime.now().strftime('%H:%M:%S')}] [!] {name}: {error} ({elapsed:.1f}s)")
                # Log errors to frontend
                if self._session_id:
                    add_session_log(self._session_id, f"{name} error: {error}", level="warning", source="Track 1")
            elif result:
                all_data.extend(result)
                print(f"       [{datetime.now().strftime('%H:%M:%S')}] [+] {name}: {len(result)} items ({elapsed:.1f}s)")
            else:
                print(f"       [{datetime.now().strftime('%H:%M:%S')}] [-] {name}: 0 items ({elapsed:.1f}s)")
        
        # Send summary to frontend
        if self._session_id:
            add_session_log(self._session_id, f"Track 1 complete: {len(all_data)} items from Reddit, Reviews, Twitter, Instagram, TikTok, YouTube, etc.", level="info", source="Track 1")
        
        print(f"    [{datetime.now().strftime('%H:%M:%S')}] [+] Track 1 complete: {len(all_data)} items total")
        return all_data
    
    async def _scrape_track2_parallel(
        self,
        session_id: int,
        sector: str,
        queries: Dict
    ) -> List[Dict[str, Any]]:
        """
        Scrape Track 2 (Segment Research) with ALL scrapers in parallel.
        """
        import asyncio
        
        segment_queries = queries.get("segment_queries", {})
        all_data = []
        
        async def scrape_subreddits():
            from datetime import datetime
            results = []
            print(f"    [T2][{datetime.now().strftime('%H:%M:%S')}] START: Subreddits scraping...")
            try:
                subreddits = segment_queries.get("subreddits", [])
                for i, subreddit in enumerate(subreddits[:5]):
                    print(f"       [{datetime.now().strftime('%H:%M:%S')}] Subreddit {i+1}/{len(subreddits[:5])}: r/{subreddit}")
                    data = await self.firecrawl.scrape_subreddit(subreddit)
                    for item in data:
                        results.append({"session_id": session_id, "source_type": "reddit", "track": 2, "mention_type": "segment_discussion", **item})
            except Exception as e:
                print(f"    [!] Subreddits ERROR: {str(e)[:60]}")
            print(f"    [T2][{datetime.now().strftime('%H:%M:%S')}] END: Subreddits -> {len(results)} items")
            return results
        
        async def scrape_forums():
            from datetime import datetime
            results = []
            print(f"    [T2][{datetime.now().strftime('%H:%M:%S')}] START: Forums search...")
            try:
                forum_queries = segment_queries.get("forums", [])
                for i, query in enumerate(forum_queries[:5]):
                    print(f"       [{datetime.now().strftime('%H:%M:%S')}] Forum query {i+1}/{len(forum_queries[:5])}: {query[:30]}")
                    data = await self.firecrawl.search_forums(query)
                    for item in data:
                        results.append({"session_id": session_id, "source_type": "forum", "track": 2, "mention_type": "segment_discussion", **item})
            except Exception as e:
                print(f"    [!] Forums ERROR: {str(e)[:60]}")
            print(f"    [T2][{datetime.now().strftime('%H:%M:%S')}] END: Forums -> {len(results)} items")
            return results
        
        async def scrape_deep_segment():
            from datetime import datetime
            results = []
            print(f"    [T2][{datetime.now().strftime('%H:%M:%S')}] START: Deep segment search...")
            try:
                keywords = segment_queries.get("keywords", []) + segment_queries.get("problems", [])
                if keywords:
                    print(f"       [{datetime.now().strftime('%H:%M:%S')}] Keywords: {keywords[:3]}...")
                    data = await self.firecrawl.deep_search_segment(keywords, sector)
                    for item in data:
                        results.append({"session_id": session_id, "source_type": item.get("source_type", "web"), "track": 2, "mention_type": "problem_discussion", **item})
            except Exception as e:
                print(f"    [!] Deep segment ERROR: {str(e)[:60]}")
            print(f"    [T2][{datetime.now().strftime('%H:%M:%S')}] END: DeepSegment -> {len(results)} items")
            return results
        
        async def scrape_twitter_hashtags():
            from datetime import datetime
            results = []
            print(f"    [T2][{datetime.now().strftime('%H:%M:%S')}] START: Twitter segment search...")
            if self.apify.is_available:
                try:
                    twitter_hashtags = segment_queries.get("twitter_hashtags", [])
                    twitter_problem_searches = segment_queries.get("twitter_problem_searches", [])
                    twitter_queries = twitter_hashtags + twitter_problem_searches
                    
                    if twitter_queries:
                        print(f"       Queries: {twitter_queries[:3]}")
                        data = await self.apify.scrape_twitter(twitter_queries[:5], track=2)
                        for item in data:
                            results.append({"session_id": session_id, "source_type": "twitter", "track": 2, "mention_type": "segment_discussion", **item})
                except Exception as e:
                    print(f"    [!] Twitter ERROR: {str(e)[:60]}")
            else:
                print(f"       [SKIP] Apify not available")
            print(f"    [T2][{datetime.now().strftime('%H:%M:%S')}] END: Twitter -> {len(results)} items")
            return results
        
        async def scrape_tiktok_hashtags():
            from datetime import datetime
            results = []
            print(f"    [T2][{datetime.now().strftime('%H:%M:%S')}] START: TikTok hashtags...")
            if self.apify.is_available:
                try:
                    tiktok_hashtags = segment_queries.get("tiktok_hashtags", [])
                    if tiktok_hashtags:
                        print(f"       Hashtags: {tiktok_hashtags[:3]}")
                        data = await self.apify.scrape_tiktok(tiktok_hashtags, track=2)
                        for item in data:
                            results.append({"session_id": session_id, "source_type": "tiktok", "track": 2, "mention_type": "segment_discussion", **item})
                except Exception as e:
                    print(f"    [!] TikTok ERROR: {str(e)[:60]}")
            else:
                print(f"       [SKIP] Apify not available")
            print(f"    [T2][{datetime.now().strftime('%H:%M:%S')}] END: TikTok -> {len(results)} items")
            return results
        
        async def scrape_ig_hashtags():
            from datetime import datetime
            results = []
            print(f"    [T2][{datetime.now().strftime('%H:%M:%S')}] START: Instagram hashtags...")
            if self.apify.is_available:
                try:
                    ig_hashtags = segment_queries.get("instagram_hashtags", [])
                    if ig_hashtags:
                        print(f"       Hashtags: {ig_hashtags[:3]}")
                        data = await self.apify.scrape_instagram(ig_hashtags, track=2)
                        for item in data:
                            results.append({"session_id": session_id, "source_type": "instagram", "track": 2, "mention_type": "segment_discussion", **item})
                except Exception as e:
                    print(f"    [!] Instagram ERROR: {str(e)[:60]}")
            else:
                print(f"       [SKIP] Apify not available")
            print(f"    [T2][{datetime.now().strftime('%H:%M:%S')}] END: Instagram -> {len(results)} items")
            return results
        
        async def scrape_amazon():
            from datetime import datetime
            results = []
            print(f"    [T2][{datetime.now().strftime('%H:%M:%S')}] START: Amazon reviews...")
            if self.apify.is_available:
                try:
                    amazon_queries = segment_queries.get("amazon_products", [])
                    if amazon_queries:
                        print(f"       Queries: {amazon_queries[:2]}")
                        data = await self.apify.scrape_amazon_reviews(amazon_queries)
                        for item in data:
                            results.append({"session_id": session_id, "source_type": "amazon_reviews", "track": 2, "mention_type": "segment_discussion", **item})
                except Exception as e:
                    print(f"    [!] Amazon ERROR: {str(e)[:60]}")
            else:
                print(f"       [SKIP] Apify not available")
            print(f"    [T2][{datetime.now().strftime('%H:%M:%S')}] END: Amazon -> {len(results)} items")
            return results
        
        async def scrape_google_reviews():
            from datetime import datetime
            results = []
            print(f"    [T2][{datetime.now().strftime('%H:%M:%S')}] START: Google Reviews...")
            
            google_queries = segment_queries.get("google_business", [])
            if not google_queries:
                print(f"       [SKIP] No Google queries")
                return results
            
            # PRIMARY: Use Firecrawl (FREE, uses search credits only)
            if self.firecrawl.has_key:
                try:
                    print(f"       Using Firecrawl (free alternative to Apify)")
                    data = await self.firecrawl.scrape_google_reviews(google_queries[:5])
                    for item in data:
                        results.append({"session_id": session_id, "source_type": "google_reviews", "track": 2, "mention_type": "segment_discussion", **item})
                    if results:
                        print(f"    [T2][{datetime.now().strftime('%H:%M:%S')}] END: Google Reviews -> {len(results)} items (via Firecrawl)")
                        return results
                except Exception as e:
                    print(f"       Firecrawl error: {str(e)[:50]}")
            
            # FALLBACK: Use Apify only if explicitly enabled (expensive!)
            if settings.APIFY_ENABLE_GOOGLE_PLACES and self.apify.is_available:
                try:
                    google_queries = google_queries[:settings.APIFY_MAX_GOOGLE_PLACES]
                    print(f"       Fallback to Apify (WARNING: expensive!) - {len(google_queries)} queries")
                    data = await self.apify.scrape_google_reviews(google_queries)
                    for item in data:
                        results.append({"session_id": session_id, "source_type": "google_reviews", "track": 2, "mention_type": "segment_discussion", **item})
                except Exception as e:
                    print(f"    [!] Google Reviews ERROR: {str(e)[:60]}")
            elif not settings.APIFY_ENABLE_GOOGLE_PLACES:
                print(f"       Apify Google Places disabled (cost control)")
            
            print(f"    [T2][{datetime.now().strftime('%H:%M:%S')}] END: Google Reviews -> {len(results)} items")
            return results
        
        # RUN TRACK 2 SCRAPERS - Firecrawl sequential, Apify parallel
        SCRAPER_TIMEOUT = 30
        SOCIAL_TIMEOUT = 90  # Match Track 1 timeout for Apify actors
        print(f"    [{datetime.now().strftime('%H:%M:%S')}] [Sequential] Running Firecrawl segment scrapers (timeout={SCRAPER_TIMEOUT}s)...")
        
        # Firecrawl scrapers (sequential with timeout)
        firecrawl_scrapers = [
            ("Subreddits", scrape_subreddits),
            ("Forums", scrape_forums),
            ("DeepSegment", scrape_deep_segment),
        ]
        
        for name, scraper_fn in firecrawl_scrapers:
            start_time = datetime.now()
            print(f"       [{start_time.strftime('%H:%M:%S')}] START: {name}...")
            try:
                result = await asyncio.wait_for(scraper_fn(), timeout=SCRAPER_TIMEOUT)
                elapsed = (datetime.now() - start_time).total_seconds()
                if result:
                    all_data.extend(result)
                    print(f"       [{datetime.now().strftime('%H:%M:%S')}] [+] {name}: {len(result)} items ({elapsed:.1f}s)")
                else:
                    print(f"       [{datetime.now().strftime('%H:%M:%S')}] [-] {name}: 0 items ({elapsed:.1f}s)")
            except asyncio.TimeoutError:
                elapsed = (datetime.now() - start_time).total_seconds()
                print(f"       [{datetime.now().strftime('%H:%M:%S')}] [TIMEOUT] {name}: exceeded {SCRAPER_TIMEOUT}s ({elapsed:.1f}s)")
            except Exception as e:
                elapsed = (datetime.now() - start_time).total_seconds()
                print(f"       [{datetime.now().strftime('%H:%M:%S')}] [!] {name}: {str(e)[:50]} ({elapsed:.1f}s)")
        
        # Social/Apify scrapers (parallel with timeout)
        print(f"    [{datetime.now().strftime('%H:%M:%S')}] [Parallel] Running social segment scrapers (timeout={SOCIAL_TIMEOUT}s)...")
        
        async def timed_scraper(name, fn):
            start = datetime.now()
            try:
                result = await asyncio.wait_for(fn(), timeout=SOCIAL_TIMEOUT)
                elapsed = (datetime.now() - start).total_seconds()
                return (name, result, elapsed, None)
            except asyncio.TimeoutError:
                elapsed = (datetime.now() - start).total_seconds()
                return (name, [], elapsed, f"TIMEOUT after {SOCIAL_TIMEOUT}s")
            except Exception as e:
                elapsed = (datetime.now() - start).total_seconds()
                return (name, [], elapsed, str(e)[:50])
        
        social_results = await asyncio.gather(
            timed_scraper("TwitterHashtags", scrape_twitter_hashtags),
            timed_scraper("TikTokHashtags", scrape_tiktok_hashtags),
            timed_scraper("InstagramHashtags", scrape_ig_hashtags),
            timed_scraper("Amazon", scrape_amazon),
            timed_scraper("GoogleReviews", scrape_google_reviews),
        )
        
        for name, result, elapsed, error in social_results:
            if error:
                print(f"       [{datetime.now().strftime('%H:%M:%S')}] [!] {name}: {error} ({elapsed:.1f}s)")
                # Log errors to frontend
                if self._session_id:
                    add_session_log(self._session_id, f"{name} error: {error}", level="warning", source="Track 2")
            elif result:
                all_data.extend(result)
                print(f"       [{datetime.now().strftime('%H:%M:%S')}] [+] {name}: {len(result)} items ({elapsed:.1f}s)")
            else:
                print(f"       [{datetime.now().strftime('%H:%M:%S')}] [-] {name}: 0 items ({elapsed:.1f}s)")
        
        # Send summary to frontend
        if self._session_id:
            add_session_log(self._session_id, f"Track 2 complete: {len(all_data)} items from Forums, Quora, TikTok, Amazon, Google Reviews, etc.", level="info", source="Track 2")
        
        print(f"    [{datetime.now().strftime('%H:%M:%S')}] [+] Track 2 complete: {len(all_data)} items total")
        return all_data
    
    async def _run_ad_library_analysis(
        self,
        brand_name: str,
        website_url: str,
        competitors: List[str],
        facebook_url: Optional[str] = None,
        instagram_url: Optional[str] = None,
        ad_library_page_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run Ad Library scraping and analysis.
        Uses ad_library_page_id (priority) or facebook_url/instagram_url to find correct Ad Library page.
        """
        results = {
            "brand_ads": None,
            "competitor_ads": [],
            "patterns": {},
            "landing_pages": [],
            "total_ads_analyzed": 0
        }
        
        try:
            # =====================================================
            # 1. FIND AND SCRAPE BRAND ADS (curious_coder actor)
            # Strategy: FB URL → page_id → view_all → page name search
            # =====================================================
            from ..config import settings
            from .adlibrary.apify_facebook import get_apify_facebook_service
            apify = get_apify_facebook_service()
            max_ads = settings.AD_LIBRARY_MAX_ADS

            brand_ads = None
            resolved_page_id = ad_library_page_id
            fb_handle = extract_fb_handle(facebook_url)

            # STRATEGY 1: Facebook page URL (most reliable — 100% precision + gives page_id)
            if facebook_url and not brand_ads:
                print(f"    [Ad Library] Strategy 1: Facebook URL → {facebook_url}")
                raw_ads = await apify.scrape_by_facebook_url(facebook_url, limit=max_ads)
                if raw_ads:
                    # Get page_id from results for free
                    if not resolved_page_id:
                        resolved_page_id = apify.get_page_id_from_results(raw_ads)
                        if resolved_page_id:
                            print(f"    [Ad Library] Extracted page_id={resolved_page_id} from FB URL results")
                    # Filter by brand name (FB URL results are usually 100% correct but just in case)
                    raw_ads = apify.filter_by_page_name(raw_ads, brand_name)
                    if raw_ads:
                        brand_ads = await self.adlib_scraper.process_raw_apify_ads(raw_ads, brand_name, max_ads)

            # STRATEGY 2: view_all_page_id (100% precision when we have the page_id)
            if resolved_page_id and not brand_ads:
                print(f"    [Ad Library] Strategy 2: view_all_page_id={resolved_page_id}")
                raw_ads = await apify.scrape_by_page_id(resolved_page_id, limit=max_ads)
                if raw_ads:
                    brand_ads = await self.adlib_scraper.process_raw_apify_ads(raw_ads, brand_name, max_ads)

            # STRATEGY 3: Playwright to find page_id, then view_all_page_id
            if not brand_ads and not resolved_page_id:
                print(f"    [Ad Library] Strategy 3: Playwright → page_id")
                try:
                    from .adlibrary.playwright_search import get_playwright_search
                    playwright_search = await get_playwright_search()
                    ig_handle = extract_ig_handle(instagram_url)
                    usernames_to_try = []
                    if ig_handle:
                        usernames_to_try.append(ig_handle)
                    if fb_handle:
                        usernames_to_try.append(fb_handle)
                    usernames_to_try.append(brand_name.lower().replace(" ", ""))

                    resolved_page_id = await playwright_search.find_page_id_by_clicking_advertiser(
                        usernames_to_try=usernames_to_try
                    )
                    if resolved_page_id:
                        print(f"    [Ad Library] Playwright found page_id={resolved_page_id}")
                        raw_ads = await apify.scrape_by_page_id(resolved_page_id, limit=max_ads)
                        if raw_ads:
                            brand_ads = await self.adlib_scraper.process_raw_apify_ads(raw_ads, brand_name, max_ads)
                    else:
                        print(f"    [Ad Library] Playwright could not find page_id for '{brand_name}'")
                except Exception as e:
                    print(f"    [!] Playwright error: {e}")

            # STRATEGY 4: search by page name (fallback — may include other pages)
            if not brand_ads:
                print(f"    [Ad Library] Strategy 4: Page name search '{brand_name}'")
                raw_ads = await apify.scrape_by_page_name(brand_name, limit=max_ads)
                if raw_ads:
                    raw_ads = apify.filter_by_page_name(raw_ads, brand_name)
                    if raw_ads:
                        # Extract page_id from filtered results
                        if not resolved_page_id:
                            resolved_page_id = apify.get_page_id_from_results(raw_ads)
                        brand_ads = await self.adlib_scraper.process_raw_apify_ads(raw_ads, brand_name, max_ads)

            if not brand_ads or not brand_ads.get("ads"):
                print("    [!] No ads found via any method")
            
            if brand_ads:
                ads_found = len(brand_ads.get("ads", []))
                print(f"    [Ad Library] {ads_found} ads encontrados")
                
                if ads_found > 0:
                    # Analyze with Gemini - 30 unique videos + 20 unique statics
                    max_analyze_videos = settings.AD_LIBRARY_MAX_BRAND_VIDEOS
                    max_analyze_images = settings.AD_LIBRARY_MAX_BRAND_STATICS
                    print(f"    [Gemini] Analizando {ads_found} ads con IA (max {max_analyze_videos} videos, {max_analyze_images} estaticos)...")
                    print("       (esto puede tardar 3-8 minutos por el analisis de video)")
                    analyzed_ads = await self.ad_analyzer.analyze_ads_batch(
                        brand_ads.get("ads", []),
                        max_videos=max_analyze_videos,
                        max_images=max_analyze_images
                    )
                    brand_ads["ads"] = analyzed_ads
                    results["brand_ads"] = brand_ads
                    analyzed_count = len([a for a in analyzed_ads if a.get("creative_analysis")])
                    results["total_ads_analyzed"] += analyzed_count
                    print(f"    [Gemini] {analyzed_count} ads analizados con exito")
                    
                    # Extract landing page URLs
                    lp_urls = [ad.get("cta_destination") or ad.get("destination_url") 
                              for ad in analyzed_ads if ad.get("cta_destination") or ad.get("destination_url")]
                    
                    if lp_urls:
                        print(f"    [Landing Pages] Analizando {min(5, len(lp_urls))} landing pages...")
                        lps = await self.lp_analyzer.analyze_multiple(lp_urls[:5])
                        results["landing_pages"].extend(lps)
                        print(f"    [Landing Pages] {len(lps)} LPs analizadas")
            else:
                print("    [!] No se encontro Ad Library para la marca")
            
            # 2. Scrape competitor ads (10 video + 10 static per competitor)
            if competitors:
                from ..config import settings
                max_competitors = settings.AD_LIBRARY_MAX_COMPETITORS
                comp_videos = settings.AD_LIBRARY_MAX_COMP_VIDEOS
                comp_statics = settings.AD_LIBRARY_MAX_COMP_STATICS
                ads_per_competitor = comp_videos + comp_statics  # 20 per competitor
                actual_competitors = min(len(competitors), max_competitors)
                
                print(f"    [Competidores] Scrapeando {actual_competitors} competidores ({comp_videos} videos + {comp_statics} estaticos c/u)...")
                
                competitor_ads_collected = 0
                for i, comp_name in enumerate(competitors[:max_competitors], 1):
                    try:
                        print(f"       [{i}/{actual_competitors}] {comp_name} (buscando {ads_per_competitor} ads)...")
                        comp_ads = await self.adlib_scraper.scrape_competitor_ads(
                            competitor_name=comp_name,
                            limit=ads_per_competitor
                        )
                        
                        if comp_ads.get("ads"):
                            comp_count = len(comp_ads["ads"])
                            competitor_ads_collected += comp_count
                            print(f"       -> {comp_count} ads encontrados, analizando (max {comp_videos} videos, {comp_statics} estaticos)...")
                            # Analyze competitor ads with per-competitor limits
                            analyzed_comp = await self.ad_analyzer.analyze_ads_batch(
                                comp_ads["ads"],
                                max_videos=comp_videos,
                                max_images=comp_statics
                            )
                            comp_ads["ads"] = analyzed_comp
                            results["competitor_ads"].append(comp_ads)
                            results["total_ads_analyzed"] += len([a for a in analyzed_comp if a.get("creative_analysis")])
                        else:
                            print(f"       -> No se encontraron ads")
                    except Exception as e:
                        print(f"       [!] Error con {comp_name}: {e}")
            
            # 3. Aggregate patterns
            print("    [Patrones] Agregando patrones creativos...")
            all_ads = []
            if results["brand_ads"]:
                all_ads.extend(results["brand_ads"].get("ads", []))
            for comp_data in results["competitor_ads"]:
                all_ads.extend(comp_data.get("ads", []))
            
            if all_ads:
                results["patterns"] = self.ad_analyzer.aggregate_patterns(all_ads)
                print(f"    [Patrones] Patrones extraidos de {len(all_ads)} ads")
            
            print(f"    [+] Ad Library completado: {results['total_ads_analyzed']} ads analizados en total")
            
        except Exception as e:
            print(f"    [!] Error en Ad Library analysis: {e}")
        
        return results
    
    async def _run_competitor_analysis(
        self,
        brand_name: str,
        sector: str,
        vertical: str,
        brand_info: Dict,
        initial_competitors: List[str],
        competitor_ads: List[Dict]
    ) -> Dict[str, Any]:
        """
        Run deep competitor analysis.
        """
        results = {
            "profiles": [],
            "matrix": {},
            "swot": {},
            "messaging_analysis": {}
        }
        
        try:
            # 1. Identify and profile competitors
            print("    [Competidores] Identificando y perfilando competidores...")
            print("       (buscando en web y analizando con IA)")
            profiles = await self.competitor_analyzer.identify_competitors(
                brand_name=brand_name,
                sector=sector,
                vertical=vertical,
                known_competitors=initial_competitors
            )
            results["profiles"] = profiles
            print(f"    [Competidores] {len(profiles)} competidores identificados")
            
            # 2. Generate competitive matrix
            print("    [Matriz] Generando matriz competitiva...")
            matrix = await self.competitor_analyzer.generate_competitive_matrix(
                brand_info=brand_info,
                competitors=profiles
            )
            results["matrix"] = matrix
            print("    [Matriz] Matriz competitiva generada")
            
            # 3. Generate SWOT
            print("    [SWOT] Generando analisis SWOT...")
            swot = await self.competitor_analyzer.generate_swot(
                brand_info=brand_info,
                competitors=profiles
            )
            results["swot"] = swot
            print("    [SWOT] Analisis SWOT completado")
            
            # 4. Analyze competitor messaging from ads
            if competitor_ads:
                print("    [Messaging] Analizando messaging de competidores...")
                # Get competitor LPs
                comp_lps = []
                for comp_data in competitor_ads:
                    for ad in comp_data.get("ads", []):
                        if ad.get("cta_destination"):
                            lp = await self.lp_analyzer.analyze_landing_page(ad["cta_destination"])
                            comp_lps.append(lp)
                            if len(comp_lps) >= 5:
                                break
                    if len(comp_lps) >= 5:
                        break
                
                messaging = await self.competitor_analyzer.analyze_competitor_messaging(
                    competitor_ads=[ad for comp in competitor_ads for ad in comp.get("ads", [])],
                    competitor_lps=comp_lps
                )
                results["messaging_analysis"] = messaging
                print("    [Messaging] Analisis de messaging completado")
            
            print(f"    [+] Competitor Analysis completado: {len(profiles)} competidores perfilados")
            
        except Exception as e:
            print(f"    [!] Error en Competitor analysis: {e}")
        
        return results
    
    async def _update_db_sentiment(self, session_id: int):
        """
        Safety net: update sentiment for items that missed pre-save analysis.
        Most items should already have sentiment from the pre-save step.
        Uses RoBERTa if available, falls back to keyword-based.
        """
        try:
            from .sentiment import get_sentiment_analyzer, is_roberta_available
            analyzer = get_sentiment_analyzer()
            model_name = "roberta" if is_roberta_available() else "keyword"

            result = await self.db.execute(
                select(ScrapedData).where(
                    ScrapedData.session_id == session_id,
                    ScrapedData.sentiment.is_(None)  # Only items missing sentiment
                )
            )
            items = result.scalars().all()

            if not items:
                print(f"    [Sentiment] All items already have sentiment [OK]")
                return

            updated = 0
            for item in items:
                content = item.content or item.title or ""
                if content and len(content.strip()) > 10:
                    try:
                        result = analyzer.analyze(content)
                        item.sentiment = result["sentiment"]
                        item.sentiment_score = result["score"]
                        updated += 1
                    except Exception:
                        item.sentiment = "neutral"
                        item.sentiment_score = 0.0
                else:
                    item.sentiment = "neutral"
                    item.sentiment_score = 0.0

            if updated:
                await self.db.commit()
                print(f"    [Sentiment] Backfilled {updated} items missing sentiment ({model_name})")
        except Exception as e:
            print(f"    [!] Sentiment DB update failed (non-blocking): {str(e)[:100]}")
    
    def _create_data_summary(self, scraped_data: List[Dict]) -> Dict[str, Any]:
        """Create summary statistics from scraped data with real sentiment analysis."""
        summary = {
            "total_items": len(scraped_data),
            "by_source": {},
            "by_track": {1: 0, 2: 0},
            "by_mention_type": {},
            "by_sentiment": {"positive": 0, "negative": 0, "neutral": 0},
            "sentiment_keywords": {"positive": [], "negative": []}
        }
        
        # Run sentiment analysis on all items
        analyzer = get_sentiment_analyzer()
        all_positive_keywords = []
        all_negative_keywords = []
        
        for item in scraped_data:
            # By source
            source = item.get("source_type", "unknown")
            summary["by_source"][source] = summary["by_source"].get(source, 0) + 1
            
            # By track
            track = item.get("track", 1)
            summary["by_track"][track] = summary["by_track"].get(track, 0) + 1
            
            # By mention type
            mention = item.get("mention_type", "unknown")
            summary["by_mention_type"][mention] = summary["by_mention_type"].get(mention, 0) + 1
            
            # Real sentiment analysis
            content = item.get("content", "") or item.get("title", "") or ""
            if content:
                result = analyzer.analyze(content)
                sentiment = result["sentiment"]
                item["sentiment"] = sentiment  # Update item with analyzed sentiment
                item["sentiment_score"] = result["score"]
                all_positive_keywords.extend(result.get("positive_keywords", []))
                all_negative_keywords.extend(result.get("negative_keywords", []))
            else:
                sentiment = "neutral"
            
            if sentiment in summary["by_sentiment"]:
                summary["by_sentiment"][sentiment] += 1
        
        # Get top sentiment keywords
        from collections import Counter
        summary["sentiment_keywords"]["positive"] = [kw for kw, _ in Counter(all_positive_keywords).most_common(10)]
        summary["sentiment_keywords"]["negative"] = [kw for kw, _ in Counter(all_negative_keywords).most_common(10)]
        
        # Calculate percentages
        total = len(scraped_data) or 1
        summary["sentiment_pct"] = {
            k: round((v / total) * 100, 1) for k, v in summary["by_sentiment"].items()
        }
        
        return summary
    
    def _extract_top_quotes(self, scraped_data: List[Dict], limit: int = 20) -> List[Dict]:
        """Extract top quotes from scraped data."""
        quotes = []
        
        def safe_int(val):
            """Safely convert value to int."""
            if val is None:
                return 0
            try:
                return int(val)
            except (ValueError, TypeError):
                return 0
        
        for item in scraped_data:
            content = item.get("content", "")
            if content and len(content) > 50 and len(content) < 500:
                # Score based on engagement
                likes = safe_int(item.get("likes", 0))
                comments = safe_int(item.get("comments_count", 0))
                score = likes + comments * 2
                quotes.append({
                    "text": content[:300],
                    "source": item.get("source_type"),
                    "source_url": item.get("source_url"),
                    "author": item.get("author"),
                    "engagement_score": score,
                    "sentiment": item.get("sentiment")
                })
        
        # Sort by engagement and return top
        quotes.sort(key=lambda x: x["engagement_score"], reverse=True)
        return quotes[:limit]
    
    def _categorize_by_topic(self, scraped_data: List[Dict]) -> Dict[str, List[Dict]]:
        """Categorize scraped data by detected topics."""
        categories = {
            "pricing": [],
            "features": [],
            "support": [],
            "quality": [],
            "comparison": [],
            "problems": [],
            "positive_reviews": [],
            "negative_reviews": []
        }
        
        for item in scraped_data:
            content = ((item.get("content") or "") + " " + (item.get("title") or "")).lower()
            
            # Simple keyword-based categorization
            if any(w in content for w in ["price", "cost", "expensive", "cheap", "worth", "$", "discount"]):
                categories["pricing"].append(item)
            if any(w in content for w in ["feature", "function", "capability", "tool", "option"]):
                categories["features"].append(item)
            if any(w in content for w in ["support", "help", "customer service", "response", "contact"]):
                categories["support"].append(item)
            if any(w in content for w in ["quality", "reliable", "works", "effective", "results"]):
                categories["quality"].append(item)
            if any(w in content for w in ["vs", "versus", "compared", "alternative", "better than"]):
                categories["comparison"].append(item)
            if any(w in content for w in ["problem", "issue", "bug", "broken", "doesn't work", "frustrated"]):
                categories["problems"].append(item)
            
            # By sentiment
            sentiment = item.get("sentiment", "neutral")
            if sentiment == "positive":
                categories["positive_reviews"].append(item)
            elif sentiment == "negative":
                categories["negative_reviews"].append(item)
        
        # Limit each category
        for key in categories:
            categories[key] = categories[key][:10]
        
        return categories
    
    def _create_cross_source_insights(
        self, 
        scraped_data: List[Dict], 
        ad_patterns: Dict
    ) -> Dict[str, Any]:
        """
        Create cross-source insights by finding patterns that appear across multiple sources.
        This is valuable because patterns validated across sources are more reliable.
        """
        cross_insights = {
            "validated_pain_points": [],  # Pain points mentioned in multiple sources
            "consistent_praise": [],  # Praise that appears in multiple places
            "recurring_objections": [],  # Objections appearing across sources
            "messaging_gaps": [],  # What customers say vs what ads communicate
            "source_correlations": [],  # Which sources have similar sentiments
            "universal_themes": []  # Themes that transcend source type
        }
        
        # Group data by source type
        by_source = {}
        for item in scraped_data:
            source = item.get("source_type", "unknown")
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(item)
        
        # Extract common keywords/phrases across sources
        keyword_counts_by_source = {}
        common_keywords = {}
        
        for source, items in by_source.items():
            source_keywords = set()
            for item in items:
                content = ((item.get("content") or "") + " " + (item.get("title") or "")).lower()
                # Extract significant words (simplified)
                words = [w.strip() for w in content.split() if len(w) > 5]
                source_keywords.update(words[:50])  # Limit per item
            keyword_counts_by_source[source] = source_keywords
        
        # Find keywords that appear in 3+ sources
        all_keywords = {}
        for source, keywords in keyword_counts_by_source.items():
            for kw in keywords:
                if kw not in all_keywords:
                    all_keywords[kw] = []
                all_keywords[kw].append(source)
        
        for kw, sources in all_keywords.items():
            if len(sources) >= 3:
                cross_insights["universal_themes"].append({
                    "theme": kw,
                    "sources": sources,
                    "source_count": len(sources)
                })
        
        # Sort by source count
        cross_insights["universal_themes"] = sorted(
            cross_insights["universal_themes"],
            key=lambda x: x["source_count"],
            reverse=True
        )[:20]
        
        # Find validated pain points (negative items in 2+ sources)
        pain_keywords = ["problem", "issue", "frustrated", "annoying", "hate", "difficult", "confusing", "expensive"]
        pain_by_source = {}
        
        for source, items in by_source.items():
            for item in items:
                content = ((item.get("content") or "") + " " + (item.get("title") or "")).lower()
                sentiment = item.get("sentiment", "neutral")
                
                if sentiment == "negative" or any(pk in content for pk in pain_keywords):
                    # Extract the pain point phrase
                    for pk in pain_keywords:
                        if pk in content:
                            if pk not in pain_by_source:
                                pain_by_source[pk] = set()
                            pain_by_source[pk].add(source)
        
        for pain, sources in pain_by_source.items():
            if len(sources) >= 2:
                cross_insights["validated_pain_points"].append({
                    "pain_point": pain,
                    "validated_by": list(sources),
                    "source_count": len(sources)
                })
        
        # Find consistent praise (positive items in 2+ sources)
        praise_keywords = ["love", "great", "amazing", "excellent", "best", "recommend", "helpful"]
        praise_by_source = {}
        
        for source, items in by_source.items():
            for item in items:
                content = ((item.get("content") or "") + " " + (item.get("title") or "")).lower()
                sentiment = item.get("sentiment", "neutral")
                
                if sentiment == "positive" or any(pk in content for pk in praise_keywords):
                    for pk in praise_keywords:
                        if pk in content:
                            if pk not in praise_by_source:
                                praise_by_source[pk] = set()
                            praise_by_source[pk].add(source)
        
        for praise, sources in praise_by_source.items():
            if len(sources) >= 2:
                cross_insights["consistent_praise"].append({
                    "praise_type": praise,
                    "validated_by": list(sources),
                    "source_count": len(sources)
                })
        
        # Messaging gaps: Compare ad themes vs customer conversation themes
        ad_themes = set()
        if ad_patterns:
            # Extract themes from ad patterns
            for framework in ad_patterns.get("frameworks", {}).keys():
                ad_themes.add(framework.lower())
            for hook in ad_patterns.get("hook_types", {}).keys():
                ad_themes.add(hook.lower())
        
        customer_themes = set()
        for theme in cross_insights["universal_themes"]:
            customer_themes.add(theme["theme"])
        
        # Themes customers discuss but ads don't address
        gaps = customer_themes - ad_themes
        cross_insights["messaging_gaps"] = list(gaps)[:10]
        
        # Source sentiment correlations
        sentiment_by_source = {}
        for source, items in by_source.items():
            positive = sum(1 for i in items if i.get("sentiment") == "positive")
            negative = sum(1 for i in items if i.get("sentiment") == "negative")
            total = len(items) or 1
            sentiment_by_source[source] = {
                "positive_pct": (positive / total) * 100,
                "negative_pct": (negative / total) * 100,
                "total": total
            }
        
        cross_insights["source_correlations"] = sentiment_by_source
        
        # Extract source-specific insights from scraped data (from our new analyzers)
        collected_insights = {}
        for item in scraped_data:
            source_type = item.get("source_type", "")
            raw_data = item.get("raw_data")
            
            if source_type.endswith("_insights") and raw_data:
                # Map source_type to insight key
                key_map = {
                    "youtube_insights": "youtube_insights",
                    "twitter_insights": "twitter_insights",
                    "reddit_insights": "reddit_insights",
                    "review_insights": "review_insights"
                }
                if source_type in key_map:
                    collected_insights[key_map[source_type]] = raw_data
        
        # Store for later async analysis
        cross_insights["collected_source_insights"] = collected_insights
        
        return cross_insights
    
    def _generate_full_report(
        self,
        brand: Brand,
        insights: Dict,
        ad_library_results: Dict,
        competitor_results: Dict
    ) -> str:
        """Generate the full markdown report."""
        report = f"""
# BRAND INTELLIGENCE REPORT: {brand.name}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## DATA SUMMARY

| Metric | Value |
|--------|-------|
| Total Data Points | {insights.get('data_summary', {}).get('total_items', 0)} |
| Ads Analyzed | {ad_library_results.get('total_ads_analyzed', 0)} |
| Competitors Profiled | {len(competitor_results.get('profiles', []))} |

### Data by Source
"""
        
        for source, count in insights.get("data_summary", {}).get("by_source", {}).items():
            report += f"- {source}: {count} items\n"
        
        report += "\n### Sentiment Breakdown\n"
        sentiment = insights.get("data_summary", {}).get("by_sentiment", {})
        total_sent = sum(sentiment.values()) or 1
        for sent, count in sentiment.items():
            pct = (count / total_sent) * 100
            report += f"- {sent.capitalize()}: {count} ({pct:.1f}%)\n"
        
        # Top Quotes
        report += "\n---\n\n## TOP QUOTES FROM REAL USERS\n\n"
        for i, quote in enumerate(insights.get("top_quotes", [])[:10], 1):
            report += f'{i}. "{quote.get("text", "")}"\n'
            report += f'   - Source: {quote.get("source", "Unknown")} | Sentiment: {quote.get("sentiment", "N/A")}\n\n'
        
        # Competitive Landscape
        report += "\n---\n\n## COMPETITIVE LANDSCAPE\n\n"
        
        profiles = competitor_results.get("profiles", [])
        if profiles:
            report += "| Competitor | Positioning | Key Differentiator |\n"
            report += "|------------|-------------|--------------------|\n"
            for comp in profiles[:5]:
                report += f"| {comp.get('name', 'N/A')} | {comp.get('positioning', 'N/A')[:50]} | {comp.get('key_differentiator', 'N/A')[:50]} |\n"
        
        # SWOT
        swot = competitor_results.get("swot", {})
        if swot:
            report += "\n### SWOT Analysis\n\n"
            report += "**Strengths:**\n"
            for s in swot.get("strengths", [])[:3]:
                point = s.get("point") if isinstance(s, dict) else s
                report += f"- {point}\n"
            
            report += "\n**Weaknesses:**\n"
            for w in swot.get("weaknesses", [])[:3]:
                point = w.get("point") if isinstance(w, dict) else w
                report += f"- {point}\n"
            
            report += "\n**Opportunities:**\n"
            for o in swot.get("opportunities", [])[:3]:
                point = o.get("point") if isinstance(o, dict) else o
                report += f"- {point}\n"
            
            report += "\n**Threats:**\n"
            for t in swot.get("threats", [])[:3]:
                point = t.get("point") if isinstance(t, dict) else t
                report += f"- {point}\n"
        
        # Ad Creative Patterns
        report += "\n---\n\n## AD CREATIVE ANALYSIS\n\n"
        
        patterns = ad_library_results.get("patterns", {})
        if patterns:
            report += f"**Total Ads Analyzed:** {patterns.get('total_analyzed', 0)}\n\n"
            
            report += "### Top Frameworks\n"
            for fw, count in list(patterns.get("frameworks", {}).items())[:5]:
                report += f"- {fw}: {count} ads\n"
            
            report += "\n### Top Hook Types\n"
            for hook, count in list(patterns.get("hook_types", {}).items())[:5]:
                report += f"- {hook}: {count} ads\n"
            
            report += f"\n**Average Hook Strength:** {patterns.get('avg_hook_strength', 0):.1f}/5\n"
            report += f"**Average Effectiveness:** {patterns.get('avg_effectiveness', 0):.1f}/5\n"
            
            # Top Transcriptions
            report += "\n### Sample Transcriptions (Top Performers)\n\n"
            for trans in patterns.get("top_transcriptions", [])[:3]:
                report += f"**Ad {trans.get('library_id', 'N/A')}** (Effectiveness: {trans.get('effectiveness', 'N/A')}/5)\n"
                report += f"```\n{trans.get('text', 'No transcription')[:500]}\n```\n\n"
        
        # Creative Dimensions
        report += "\n---\n\n## CREATIVE DIMENSIONS\n\n"
        
        report += "### Ideal Customer Profiles (ICPs)\n"
        for icp in insights.get("icps", [])[:3]:
            if isinstance(icp, dict):
                report += f"- **{icp.get('name', 'ICP')}**: {icp.get('description', '')[:100]}\n"
            else:
                report += f"- {icp}\n"
        
        report += "\n### Pain Points\n"
        for pp in insights.get("pain_points", [])[:5]:
            report += f"- {pp}\n" if isinstance(pp, str) else f"- {pp.get('pain_point', pp)}\n"
        
        report += "\n### Value Props\n"
        for vp in insights.get("value_props", [])[:5]:
            report += f"- {vp}\n" if isinstance(vp, str) else f"- {vp.get('value_prop', vp)}\n"
        
        report += "\n### Purchase Triggers\n"
        for pt in insights.get("purchase_triggers", [])[:5]:
            if isinstance(pt, dict):
                report += f"- {pt.get('trigger', pt)}\n"
            else:
                report += f"- {pt}\n"
        
        report += "\n### Objections to Address\n"
        for obj in insights.get("objections", [])[:5]:
            if isinstance(obj, dict):
                report += f"- **{obj.get('objection', '')}**\n"
                report += f"  - Response: {obj.get('response', '')[:100]}\n"
            else:
                report += f"- {obj}\n"
        
        report += "\n### Recommended Hooks\n"
        for hook in insights.get("recommended_hooks", [])[:5]:
            if isinstance(hook, dict):
                report += f"- {hook.get('hook', hook)}\n"
            else:
                report += f"- {hook}\n"
        
        # Generated Scripts
        report += "\n---\n\n## GENERATED AD SCRIPTS\n\n"
        for i, script in enumerate(insights.get("generated_scripts", [])[:3], 1):
            report += f"### Script {i}: {script.get('script_name', 'Untitled')}\n"
            report += f"**Framework:** {script.get('framework', 'N/A')} | "
            report += f"**Hook Type:** {script.get('hook_type', 'N/A')} | "
            report += f"**Length:** ~{script.get('estimated_length_seconds', 'N/A')}s\n\n"
            report += f"**Hook:** {script.get('hook', '')}\n\n"
            report += f"**Script:**\n```\n{script.get('full_script', script.get('body', ''))[:500]}\n```\n\n"
            report += f"**Why it works:** {script.get('why_it_works', '')}\n\n"
        
        # Thumbnail Suggestions
        report += "\n---\n\n## THUMBNAIL/FIRST FRAME SUGGESTIONS\n\n"
        for i, thumb in enumerate(insights.get("thumbnail_suggestions", [])[:5], 1):
            report += f"### Concept {i}: {thumb.get('concept_name', 'Untitled')}\n"
            report += f"- **Type:** {thumb.get('thumbnail_type', 'N/A')}\n"
            report += f"- **Visual:** {thumb.get('visual_description', '')[:150]}\n"
            report += f"- **Text Overlay:** {thumb.get('text_overlay', 'None')}\n"
            report += f"- **Emotion:** {thumb.get('emotion_evoked', 'N/A')}\n\n"
        
        # A/B Test Suggestions
        report += "\n---\n\n## A/B TEST SUGGESTIONS\n\n"
        for i, test in enumerate(insights.get("ab_test_suggestions", [])[:5], 1):
            report += f"### Test {i}: {test.get('test_name', 'Untitled')}\n"
            report += f"**Priority:** {test.get('priority', 'N/A')} | **Type:** {test.get('test_type', 'N/A')}\n\n"
            report += f"**Hypothesis:** {test.get('hypothesis', '')}\n\n"
            control = test.get('control', {})
            variant = test.get('variant', {})
            report += f"- **Control:** {control.get('description', 'N/A')}\n"
            report += f"- **Variant:** {variant.get('description', 'N/A')}\n"
            report += f"- **Expected Impact:** {test.get('expected_impact', 'N/A')}\n\n"
        
        report += "\n---\n\n*Report generated by Brand Intelligence v2*\n"
        
        return report
    
    async def generate_proto_icps(
        self,
        session_id: int,
        brand_name: str
    ) -> Dict[str, Any]:
        """
        Generate Proto-ICPs from VoC (Voice of Customer) data.
        
        1. Collects all snippets from scraped data (reviews, reddit, comments)
        2. Classifies each snippet with Trigger, Blocker, Outcome, Proof
        3. Clusters by Trigger × Blocker
        4. Returns clusters with language cues and representative snippets
        
        Args:
            session_id: Research session ID
            brand_name: Brand name for context
            
        Returns:
            Dict with clusters, recommendations, report, and stats
        """
        self._log(f"[Proto-ICP] Starting Proto-ICP generation for {brand_name}")
        
        # Step 1: Collect VoC snippets from database
        voc_source_types = ['trustpilot', 'reddit', 'site_review', 'amazon', 'app_store', 'google_reviews', 'comment']
        
        result = await self.db.execute(
            select(ScrapedData).where(
                ScrapedData.session_id == session_id,
                ScrapedData.source_type.in_(voc_source_types)
            )
        )
        scraped_items = result.scalars().all()
        
        self._log(f"[Proto-ICP] Found {len(scraped_items)} VoC snippets to classify")
        
        if not scraped_items:
            self._log("[Proto-ICP] No VoC data found, skipping Proto-ICP generation")
            return {"clusters": [], "recommendations": [], "report": "", "stats": {"total_snippets": 0}}
        
        # Step 2: Format snippets for classification
        snippets_to_classify = []
        for item in scraped_items:
            content = item.content or ""
            if len(content) < 20:  # Skip very short snippets
                continue
            
            snippets_to_classify.append({
                "content": content[:500],  # Truncate long content
                "source_type": item.source_type,
                "source_url": item.source_url or "",
                "context": item.title or brand_name
            })
        
        self._log(f"[Proto-ICP] Classifying {len(snippets_to_classify)} snippets...")
        
        # Step 3: Classify snippets (batch)
        classified_snippets = await self.snippet_classifier.classify_batch(
            snippets_to_classify,
            batch_size=10
        )
        
        successful = sum(1 for s in classified_snippets if s.get("classification"))
        self._log(f"[Proto-ICP] Successfully classified {successful}/{len(classified_snippets)} snippets")
        
        # Step 4: Build Proto-ICP clusters
        proto_icp_result = build_proto_icps(classified_snippets, brand_name)
        
        self._log(f"[Proto-ICP] Generated {proto_icp_result['stats']['total_clusters']} clusters")
        
        # Log recommendations
        for rec in proto_icp_result.get('recommendations', [])[:3]:
            cluster = rec['cluster']
            self._log(f"[Proto-ICP] Recommended: {cluster['cluster_id']} ({cluster['trigger_label']} × {cluster['blocker_label']}) - Score: {rec['score']}")
        
        return proto_icp_result

    async def generate_ctps(
        self,
        session_id: int,
        brand_name: str,
        sector: str = "",
        vertical: str = "",
        existing_pain_points: List[str] = None,
        ad_library_data: Any = None,
        ad_creative_patterns: Any = None
    ) -> Dict[str, Any]:
        """
        Generate Creative Target Personas (CTPs) from VoC data.

        1. Collects classified snippets from DB (reuses intake engine tags)
        2. Runs stance classification (batch) — adds general_stance per snippet
        3. Updates DB with stance labels
        4. Builds CTPs by clustering on general_stance
        5. Generates hypothesis layer (one LLM call per CTP)

        Args:
            session_id: Research session ID
            brand_name: Brand name for LLM context
            sector: Brand sector
            vertical: Brand vertical
            existing_pain_points: Pain points from insights generation
            ad_library_data: Analyzed ads data (for hypothesis cross-reference)
            ad_creative_patterns: Aggregated ad patterns

        Returns:
            Dict with ctps, hypothesis, and stats
        """
        self._log(f"[CTP] Starting Creative Target Persona generation for {brand_name}")

        # Step 1: Collect VoC snippets from database
        voc_source_types = [
            'trustpilot', 'reddit', 'site_review', 'amazon', 'app_store',
            'google_reviews', 'comment', 'forum', 'quora', 'youtube_comment',
            'g2', 'capterra', 'other_review', 'tiktok', 'instagram', 'twitter'
        ]

        result = await self.db.execute(
            select(ScrapedData).where(
                ScrapedData.session_id == session_id,
                ScrapedData.source_type.in_(voc_source_types),
                ScrapedData.content.isnot(None)
            )
        )
        scraped_items = result.scalars().all()

        self._log(f"[CTP] Found {len(scraped_items)} VoC snippets")

        if not scraped_items:
            self._log("[CTP] No VoC data found, skipping CTP generation")
            return {"ctps": [], "hypothesis": [], "stats": {"total_ctps": 0, "total_snippets": 0}}

        # Step 2: Format snippets with existing intake tags as context
        snippets_for_stance = []
        for item in scraped_items:
            content = item.content or ""
            if len(content.strip()) < 20:
                continue

            snippets_for_stance.append({
                "id": item.id,
                "content": content[:500],
                "source_type": item.source_type,
                "source_url": item.source_url or "",
                "sentiment": item.sentiment or "",
                "sentiment_score": item.sentiment_score,
                "primary_trigger": item.primary_trigger or "",
                "blocker_type": item.blocker_type or "",
                "desired_outcome_level": item.desired_outcome_level or "",
                "proof_type_trusted": item.proof_type_trusted or "",
                "language_cues": item.language_cues or [],
                "context": item.title or brand_name
            })

        self._log(f"[CTP] Classifying {len(snippets_for_stance)} snippets by stance...")

        # Step 3: Run stance classification (batch)
        stance_classified = await self.stance_classifier.classify_batch(
            snippets_for_stance,
            batch_size=10
        )

        successful = sum(1 for s in stance_classified if s.get("general_stance") and s["general_stance"] != "unknown")
        self._log(f"[CTP] Successfully stance-classified {successful}/{len(stance_classified)} snippets")

        # Step 4: Update database with stance labels
        updated = 0
        for classified_dict in stance_classified:
            if classified_dict.get("general_stance"):
                snippet_id = classified_dict.get("id")
                if snippet_id:
                    for item in scraped_items:
                        if item.id == snippet_id:
                            item.general_stance = classified_dict["general_stance"]
                            item.stance_confidence = classified_dict.get("stance_confidence")
                            updated += 1
                            break

        await self.db.commit()
        self._log(f"[CTP] Updated {updated} snippets with stance labels in database")

        # Step 5: Build CTPs and hypothesis layer
        ctp_result = await build_ctps(
            classified_snippets=stance_classified,
            brand_name=brand_name,
            sector=sector,
            vertical=vertical,
            existing_pain_points=existing_pain_points,
            ad_library_data=ad_library_data,
            ad_creative_patterns=ad_creative_patterns
        )

        self._log(f"[CTP] Generated {ctp_result['stats']['total_ctps']} CTPs")

        for ctp in ctp_result.get("ctps", [])[:5]:
            self._log(f"[CTP] {ctp['ctp_id']}: {ctp['ctp_name']} (weight={ctp['weight']}, {ctp['snippet_count']} snippets)")

        return ctp_result
