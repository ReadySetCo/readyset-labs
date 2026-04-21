"""
Ad Library Scraper - Scrapes Facebook Ad Library using Firecrawl.
Adapted from existing scraper project.
"""

import os
import re
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, parse_qs
import httpx

from ...config import settings
from .playwright_search import get_playwright_search
from .apify_facebook import get_apify_facebook_service


# ── Shared social-handle extraction utilities ────────────────────────────────

_IG_EXCLUDED_PATHS = frozenset([
    'explore', 'reels', 'stories', 'p', 'tv', 'reel', 'accounts',
    'about', 'directory', 'developer', 'legal', 'emails',
])

_FB_EXCLUDED_PATHS = frozenset([
    'ads', 'watch', 'groups', 'events', 'marketplace', 'gaming',
    'login', 'help', 'pages', 'sharer', 'share', 'dialog', 'hashtag',
    'photo', 'profile.php', 'story.php', 'permalink.php',
])


def extract_ig_handle(url_or_handle: Optional[str]) -> Optional[str]:
    """
    Extract a clean Instagram handle from a URL or raw string.
    Handles: full URLs with query params, @ prefix, trailing slashes, etc.
    Returns None for generic/invalid paths.
    """
    if not url_or_handle:
        return None

    text = url_or_handle.strip().rstrip("/")

    # If it looks like a URL, parse the path component
    if "instagram.com" in text or "instagr.am" in text:
        match = re.search(r'instagram\.com/([^/?#\s]+)', text, re.IGNORECASE)
        if not match:
            match = re.search(r'instagr\.am/([^/?#\s]+)', text, re.IGNORECASE)
        if match:
            text = match.group(1)
        else:
            return None

    # Strip @ prefix, query params, fragments
    text = text.lstrip("@").split("?")[0].split("#")[0].strip().rstrip("/")

    if not text or text.lower() in _IG_EXCLUDED_PATHS:
        return None

    return text


def extract_fb_handle(url_or_handle: Optional[str]) -> Optional[str]:
    """
    Extract a clean Facebook page slug from a URL or raw string.
    Returns None for generic/invalid paths.
    """
    if not url_or_handle:
        return None

    text = url_or_handle.strip().rstrip("/")

    if "facebook.com" in text:
        match = re.search(r'facebook\.com/([^/?#\s]+)', text, re.IGNORECASE)
        if match:
            text = match.group(1)
        else:
            return None

    text = text.split("?")[0].split("#")[0].strip().rstrip("/")

    if not text or text.lower() in _FB_EXCLUDED_PATHS:
        return None

    return text


def normalize_fb_page_url(url: Optional[str]) -> Optional[str]:
    """
    Collapse any Facebook URL to the page root URL.

    Facebook Ad Library / Apify scrapers need the **page URL**, not a deep
    link. Brand DNA extractors sometimes return URLs like
    `facebook.com/IlMakiage/videos/abc/123/` or `facebook.com/Brand/posts/...`
    — these return 0 ads from the Apify actor. Normalize them all to
    `https://www.facebook.com/<handle>`.

    Special case: `facebook.com/p/Brand-Name-PAGEID/` URLs are preserved
    because the scraper extracts page_id from them (regex `/p/[^/]*-(\\d{10,})`).

    Returns None if the URL contains no extractable handle (e.g.
    `facebook.com/watch`, `facebook.com/groups/...`).
    """
    if not url:
        return None

    # Preserve /p/Name-PAGEID/ URLs — scrape_competitor_ads extracts the
    # page_id from them directly via regex. Truncate anything after the /p/<slug>.
    p_match = re.search(r'(https?://(?:www\.)?facebook\.com/p/[^/?#\s]+)', url, re.IGNORECASE)
    if p_match:
        return p_match.group(1).rstrip('/')

    handle = extract_fb_handle(url)
    if not handle:
        return None
    return f"https://www.facebook.com/{handle}"


class AdLibraryScraper:
    """Scraper for Facebook Ad Library using Firecrawl."""
    
    def __init__(self):
        self.api_key = settings.FIRECRAWL_API_KEY
        self.base_url = settings.FIRECRAWL_BASE_URL
        self.output_dir = Path("output/adlibrary")
        self.videos_dir = self.output_dir / "videos"
        self.images_dir = self.output_dir / "images"
        self.timeout = 120.0
    
    def _filter_diverse_ads(self, ads: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        """
        Filter ads for diversity: prioritize by longevity and deduplicate similar variations.
        
        Strategy:
        1. Sort by start_date (oldest first = longer running = likely better performance)
        2. Deduplicate by creative fingerprint (video/image URL from Apify snapshot)
        3. Deduplicate by ad_copy similarity (first 100 chars normalized)
        
        This ensures the same video/image uploaded multiple times to Ad Library
        is only counted ONCE — key for getting truly unique creatives.
        
        Args:
            ads: List of raw ads from Apify
            limit: Maximum ads to return
            
        Returns:
            Filtered list of diverse/unique ads
        """
        if len(ads) <= limit:
            return ads
        
        from datetime import datetime
        
        # Parse dates and add sort key
        for ad in ads:
            start = ad.get("start_date") or ad.get("startDateFormatted") or ""
            try:
                if isinstance(start, str) and start:
                    # Try common formats
                    for fmt in ["%Y-%m-%d", "%b %d, %Y", "%d %b %Y", "%Y-%m-%dT%H:%M:%S"]:
                        try:
                            ad["_parsed_date"] = datetime.strptime(start.split("T")[0] if "T" in start else start, fmt.replace("T%H:%M:%S", ""))
                            break
                        except:
                            continue
                    if "_parsed_date" not in ad:
                        ad["_parsed_date"] = datetime.now()
                else:
                    ad["_parsed_date"] = datetime.now()
            except:
                ad["_parsed_date"] = datetime.now()
        
        # Sort by date (oldest first = longer running = better performance)
        sorted_ads = sorted(ads, key=lambda x: x.get("_parsed_date", datetime.now()))
        
        def get_copy_key(ad):
            """Get normalized copy for comparison — uses more text for better dedup."""
            copy = ad.get("ad_body") or ad.get("ad_copy") or ad.get("snapshot", {}).get("body") or ""
            if isinstance(copy, dict):
                copy = copy.get("text", "")
            # Normalize: lowercase, remove extra spaces, take first 200 chars
            return " ".join(str(copy).lower().split())[:200]

        def is_similar_copy(new_key: str, seen: set, threshold: float = 0.80) -> bool:
            """Check if new_key is >80% similar to any seen copy (catches small variations)."""
            if not new_key or len(new_key) < 30:
                return False
            for existing in seen:
                if not existing or len(existing) < 30:
                    continue
                # Quick length check — very different lengths can't be 80% similar
                if abs(len(new_key) - len(existing)) / max(len(new_key), len(existing)) > 0.3:
                    continue
                # Character overlap ratio (fast approximation of similarity)
                shorter, longer = (new_key, existing) if len(new_key) <= len(existing) else (existing, new_key)
                # Compare by words for better semantic matching
                words_new = set(new_key.split())
                words_existing = set(existing.split())
                if not words_new or not words_existing:
                    continue
                overlap = len(words_new & words_existing)
                total = max(len(words_new), len(words_existing))
                if overlap / total >= threshold:
                    return True
            return False
        
        def get_creative_fingerprint(ad):
            """
            Get a fingerprint based on the actual media URL from Apify data.
            Handles both agenscrape (flat) and curious_coder (snapshot) formats.
            """
            snapshot = ad.get("snapshot", {})
            # Try video URL first — check both actor formats
            videos = ad.get("videos", []) or snapshot.get("videos", [])
            if videos:
                v = videos[0]
                url = (v.get("hd_url") or v.get("sd_url") or
                       v.get("videoHdUrl") or v.get("videoSdUrl") or v.get("url") or "")
                if url:
                    base = url.split("?")[0].rstrip("/").split("/")[-1]
                    if base and len(base) > 5:
                        return f"video:{base[:60]}"
            # Try image URL — check both formats
            images = ad.get("images", []) or snapshot.get("images", [])
            if images:
                first = images[0]
                url = ""
                if isinstance(first, dict):
                    url = (first.get("original_url") or first.get("originalImageUrl") or
                           first.get("resized_url") or first.get("resizedImageUrl") or
                           first.get("url") or "")
                elif isinstance(first, str):
                    url = first
                if url:
                    base = url.split("?")[0].rstrip("/").split("/")[-1]
                    if base and len(base) > 5:
                        return f"image:{base[:60]}"
            return None
        
        # Sort: prioritize real ads over DCO templates ({{product.brand}} etc.)
        def _is_template(ad):
            copy = ad.get("ad_body") or ad.get("ad_copy") or ad.get("snapshot", {}).get("body") or ""
            if isinstance(copy, dict):
                copy = copy.get("text", "")
            return "{{" in str(copy)

        # Stable sort: real ads first, then templates (preserves date order within each group)
        sorted_ads = sorted(sorted_ads, key=lambda a: (1 if _is_template(a) else 0))

        seen_copies = set()
        seen_creatives = set()
        diverse_ads = []
        copy_dupes = 0
        creative_dupes = 0
        for ad in sorted_ads:
            copy_key = get_copy_key(ad)
            creative_fp = get_creative_fingerprint(ad)

            # Check creative fingerprint first (strongest dedup signal - same media file)
            if creative_fp and creative_fp in seen_creatives:
                creative_dupes += 1
                continue

            # Check copy text similarity (catches text-only ads and small variations)
            if copy_key and len(copy_key) > 20:
                if copy_key in seen_copies or is_similar_copy(copy_key, seen_copies):
                    copy_dupes += 1
                    continue
                seen_copies.add(copy_key)

            # Track creative fingerprint
            if creative_fp:
                seen_creatives.add(creative_fp)

            diverse_ads.append(ad)

            if len(diverse_ads) >= limit:
                break
        
        # Clean up temp field
        for ad in diverse_ads:
            ad.pop("_parsed_date", None)
        
        print(f"       [Diversity] {len(ads)} ads -> {len(diverse_ads)} unique (copy_dupes={copy_dupes}, creative_dupes={creative_dupes})")
        
        return diverse_ads
        
    def _setup_directories(self, brand_slug: str):
        """Create output directories."""
        brand_dir = self.output_dir / brand_slug
        (brand_dir / "videos").mkdir(parents=True, exist_ok=True)
        (brand_dir / "images").mkdir(parents=True, exist_ok=True)
        (brand_dir / "thumbnails").mkdir(parents=True, exist_ok=True)
        return brand_dir
    
    def _generate_video_thumbnail(self, video_path: str) -> Optional[str]:
        """
        Generate thumbnail from first frame of video using ffmpeg.
        Returns path to thumbnail if successful, None otherwise.
        """
        if not os.path.exists(video_path):
            return None
        
        # Create thumbnail path in same directory
        video_path_obj = Path(video_path)
        thumb_path = video_path_obj.parent / f"{video_path_obj.stem}_thumb.jpg"
        
        try:
            cmd = [
                'ffmpeg', '-i', str(video_path),
                '-ss', '00:00:01',  # 1 second in (skip any black frames)
                '-vframes', '1',    # Only 1 frame
                '-vf', 'scale=480:-1',  # Scale to 480px width
                '-q:v', '2',        # High quality
                '-y',               # Overwrite
                str(thumb_path)
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=15)
            if result.returncode == 0 and thumb_path.exists():
                return str(thumb_path)
            else:
                # Try at 0 seconds if 1 second fails (very short videos)
                cmd[3] = '00:00:00'
                result = subprocess.run(cmd, capture_output=True, timeout=15)
                if result.returncode == 0 and thumb_path.exists():
                    return str(thumb_path)
        except Exception as e:
            print(f"       [!] Thumbnail generation failed: {str(e)[:50]}")
        
        return None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get API headers for Firecrawl."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def find_ad_library_url(
        self, 
        brand_name: str,
        facebook_url: Optional[str] = None,
        instagram_url: Optional[str] = None,
        ad_library_page_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Search for a brand's Ad Library page using multiple strategies.
        PRIORITY ORDER:
        1. ad_library_page_id (if set in brand)
        2. Search with FB/IG usernames to find page_id
        3. Use FB username as search query
        4. Generic search fallback
        
        Args:
            brand_name: Name of the brand to search for
            facebook_url: Optional Facebook page URL from brand's social media
            instagram_url: Optional Instagram URL for better brand validation
            ad_library_page_id: Optional Ad Library page ID directly from brand
            
        Returns:
            Ad Library URL if found, None otherwise
        """
        print(f"       [AdLib] Buscando Ad Library para '{brand_name}'...")
        print(f"       [AdLib] facebook_url recibido: {facebook_url or 'NINGUNO'}")
        print(f"       [AdLib] instagram_url recibido: {instagram_url or 'NINGUNO'}")
        print(f"       [AdLib] ad_library_page_id recibido: {ad_library_page_id or 'NINGUNO'}")
        
        # PRIORITY 0 (HIGHEST): If we have ad_library_page_id, use it directly
        if ad_library_page_id:
            ad_lib_url = f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&is_targeted_country=false&media_type=all&search_type=page&view_all_page_id={ad_library_page_id}"
            print(f"       [+] Using ad_library_page_id: {ad_library_page_id}")
            return ad_lib_url
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Extract usernames from social URLs
            fb_username = None
            ig_username = None
            
            if facebook_url:
                import re
                # Handle /p/Name-PAGEID/ format (new FB profile URLs)
                p_match = re.search(r'facebook\.com/p/[^/]*?-(\d{10,})', facebook_url)
                if p_match:
                    # Extract numeric page ID directly — this is more reliable than username
                    extracted_page_id = p_match.group(1)
                    print(f"       [AdLib] Extracted page_id from /p/ URL: {extracted_page_id}")
                    ad_lib_url = f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&is_targeted_country=false&media_type=all&search_type=page&view_all_page_id={extracted_page_id}"
                    return ad_lib_url

                match = re.search(r'facebook\.com/([^/?]+)', facebook_url)
                if match:
                    fb_username = match.group(1)
                    if fb_username in ['watch', 'groups', 'events', 'marketplace', 'gaming', 'profile.php', 'p', 'pages', 'people']:
                        fb_username = None
            
            if instagram_url:
                import re
                match = re.search(r'instagram\.com/([^/?]+)', instagram_url)
                if match:
                    ig_username = match.group(1)
                    if ig_username in ['explore', 'reels', 'stories', 'p', 'tv']:
                        ig_username = None
            
            if fb_username or ig_username:
                print(f"       [AdLib] FB username: {fb_username or 'N/A'}, IG username: {ig_username or 'N/A'}")
                
                # =========================================================================
                # PRIORITY 1: Use Playwright to search and click on the first advertiser
                # This is the most reliable method because it actually interacts with
                # the JavaScript dropdown that Firecrawl can't see
                # =========================================================================
                print(f"       [AdLib] Usando Playwright para buscar y clickear anunciante...")
                try:
                    playwright_search = await get_playwright_search()
                    # Build ordered list: IG handle first (more specific), then FB slug
                    _pw_usernames = [u for u in [ig_username, fb_username] if u]
                    page_id = await playwright_search.find_page_id_by_clicking_advertiser(
                        usernames_to_try=_pw_usernames
                    )
                    if page_id:
                        ad_lib_url = f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&is_targeted_country=false&media_type=all&search_type=page&view_all_page_id={page_id}"
                        print(f"       [+] Playwright encontró page_id: {page_id}")
                        return ad_lib_url
                    else:
                        print(f"       [AdLib] Playwright no encontró page_id, intentando Firecrawl...")
                except Exception as e:
                    print(f"       [AdLib] Playwright error: {str(e)[:80]}, intentando Firecrawl...")
                
                # =========================================================================
                # FALLBACK: Try Firecrawl search (usually won't work for JS dropdowns)
                # =========================================================================
                username_to_search = fb_username or ig_username
                
                # Try to find the exact advertiser page_id via Firecrawl search
                search_queries = [
                    f'"{username_to_search}" site:facebook.com/ads/library',
                    f'{username_to_search} facebook ad library advertiser',
                ]
                
                for query in search_queries:
                    try:
                        response = await client.post(
                            f"{self.base_url}/search",
                            headers=self._get_headers(),
                            json={"query": query, "limit": 5}
                        )
                        if response.status_code == 200:
                            data = response.json()
                            for result in data.get("data", []):
                                url = result.get("url", "")
                                # Found a URL with view_all_page_id = exact advertiser
                                if "facebook.com/ads/library" in url and "view_all_page_id" in url:
                                    print(f"       [+] Found exact advertiser via Firecrawl: {url[:80]}...")
                                    return url
                    except Exception:
                        pass
                
                # TRY TO EXTRACT page_id FROM FACEBOOK URL BEFORE FALLBACK
                # This is critical because keyword search URLs don't work with Firecrawl
                if facebook_url:
                    print(f"       [AdLib] Intentando extraer page_id desde Facebook URL...")
                    page_id = await self._extract_page_id_from_facebook_url(client, facebook_url)
                    if page_id:
                        ad_lib_url = f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&is_targeted_country=false&media_type=all&search_type=page&view_all_page_id={page_id}"
                        print(f"       [+] Encontrado page_id: {page_id}")
                        return ad_lib_url
                
                # LAST RESORT FALLBACK: Use FB username directly as search query
                # NOTE: This may not work well because Firecrawl can't see the JS dropdown
                if fb_username:
                    print(f"       [AdLib] No page_id encontrado, usando búsqueda por username: {fb_username}")
                    print(f"       [!] WARN: Keyword search may not return ads - Firecrawl can't see JS dropdown")
                    username_search_url = f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&q={fb_username}&search_type=keyword_exact_phrase"
                    print(f"       [+] Ad Library URL con FB username: {username_search_url[:80]}...")
                    return username_search_url
                
                # Fallback: Use IG username if FB username not available
                if ig_username:
                    print(f"       [AdLib] Usando IG username: {ig_username}")
                    ig_search_url = f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&q={ig_username}&search_type=keyword_exact_phrase"
                    print(f"       [+] Ad Library URL con IG username: {ig_search_url[:80]}...")
                    return ig_search_url
            
            # Try multiple search strategies (used when no facebook_url)
            search_queries = [
                f'"{brand_name}" site:facebook.com/ads/library',
                f'{brand_name} facebook ad library',
                f'{brand_name} facebook page ads',
                f'"{brand_name}" ads facebook'
            ]
            
            all_results = []
            
            for query in search_queries:
                try:
                    response = await client.post(
                        f"{self.base_url}/search",
                        headers=self._get_headers(),
                        json={
                            "query": query,
                            "limit": 10
                        }
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        all_results.extend(data.get("data", []))
                    elif response.status_code == 429:
                        print(f"       [!] Rate limited on search, using fallback")
                        break
                    
                except Exception as e:
                    print(f"       [!] Search error: {e}")
                    continue
            
            # Helper to validate URL is not political-only
            def is_valid_adlib_url(url: str) -> bool:
                # Reject political-only URLs
                if "political_and_issue" in url.lower():
                    return False
                # Reject empty searches
                if "q=" not in url and "view_all_page_id" not in url and "id=" not in url:
                    return False
                return True
            
            # Priority 1: URL with view_all_page_id (specific page)
            for result in all_results:
                url = result.get("url", "")
                if "facebook.com/ads/library" in url and "view_all_page_id" in url:
                    if is_valid_adlib_url(url):
                        print(f"       [+] Found Ad Library (page_id): {url[:80]}...")
                        return url
            
            # Priority 2: URL with ad ID 
            for result in all_results:
                url = result.get("url", "")
                if "facebook.com/ads/library" in url and "id=" in url:
                    if is_valid_adlib_url(url):
                        print(f"       [+] Found Ad Library (ad_id): {url[:80]}...")
                        return url
            
            # Priority 3: Any Ad Library URL with search query matching brand
            for result in all_results:
                url = result.get("url", "")
                if "facebook.com/ads/library" in url and is_valid_adlib_url(url):
                    # Make sure it's actually searching for this brand
                    if brand_name.lower().replace(" ", "") in url.lower().replace("%20", "").replace("+", ""):
                        print(f"       [+] Found Ad Library URL: {url[:80]}...")
                        return url
            
            # Fallback: Build search URL directly with correct parameters
            clean_name = brand_name.strip().replace(' ', '%20')
            search_url = f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&q={clean_name}&search_type=keyword_exact_phrase"
            print(f"       [~] Using constructed search URL for: {brand_name}")
            return search_url
    
    async def _extract_page_id_from_facebook_url(
        self, 
        client: httpx.AsyncClient, 
        facebook_url: str
    ) -> Optional[str]:
        """
        Extract page_id from a Facebook page URL by scraping the page.
        This ensures we get the correct brand's Ad Library.
        """
        try:
            # Clean up URL
            if not facebook_url.startswith("http"):
                facebook_url = f"https://{facebook_url}"
            
            # Extract page name from URL (e.g., facebook.com/SelfFinancial -> SelfFinancial)
            import re
            page_match = re.search(r'facebook\.com/([^/?]+)', facebook_url)
            if not page_match:
                return None
            
            page_name = page_match.group(1)
            
            # Skip non-page URLs
            if page_name in ['watch', 'groups', 'events', 'marketplace', 'gaming', 'profile.php']:
                return None
            
            print(f"       [AdLib] Extracting page_id for: {page_name}")
            
            # METHOD 1: Try to scrape Facebook page directly (often fails with 403)
            try:
                response = await client.post(
                    f"{self.base_url}/scrape",
                    headers=self._get_headers(),
                    json={
                        "url": facebook_url,
                        "formats": ["markdown", "html"],
                        "waitFor": 3000
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result.get("data", {}).get("html", "") or result.get("data", {}).get("markdown", "")
                    
                    # Try to find page_id in the content
                    patterns = [
                        r'"page_id"[:\s]+"?(\d+)"?',
                        r'view_all_page_id=(\d+)',
                        r'"entity_id"[:\s]+"?(\d+)"?',
                        r'pageID[:\s]+"?(\d+)"?',
                    ]
                    for pattern in patterns:
                        match = re.search(pattern, content)
                        if match:
                            print(f"       [AdLib] Found page_id from FB page: {match.group(1)}")
                            return match.group(1)
                else:
                    print(f"       [AdLib] Facebook scrape failed ({response.status_code}), trying search method...")
            except Exception as e:
                print(f"       [AdLib] Facebook scrape error: {str(e)[:50]}, trying search method...")
            
            # METHOD 2: Search Ad Library directly with page name
            print(f"       [AdLib] Searching Ad Library for page: {page_name}")
            search_response = await client.post(
                f"{self.base_url}/search",
                headers=self._get_headers(),
                json={
                    "query": f'"{page_name}" site:facebook.com/ads/library view_all_page_id',
                    "limit": 5
                },
                timeout=30.0
            )
            
            if search_response.status_code == 200:
                search_results = search_response.json().get("data", [])
                for result in search_results:
                    url = result.get("url", "")
                    match = re.search(r'view_all_page_id=(\d+)', url)
                    if match:
                        print(f"       [AdLib] Found page_id via search: {match.group(1)}")
                        return match.group(1)
            
            # METHOD 3: Try Ad Library search API directly
            print(f"       [AdLib] Trying direct Ad Library scrape for: {page_name}")
            ad_lib_search_url = f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&q={page_name}&search_type=keyword_exact_phrase"
            
            ad_lib_response = await client.post(
                f"{self.base_url}/scrape",
                headers=self._get_headers(),
                json={
                    "url": ad_lib_search_url,
                    "formats": ["markdown", "links"],
                    "waitFor": 5000
                },
                timeout=45.0
            )
            
            if ad_lib_response.status_code == 200:
                ad_lib_result = ad_lib_response.json()
                ad_lib_content = ad_lib_result.get("data", {}).get("markdown", "")
                
                # Look for page_id in Ad Library content
                match = re.search(r'view_all_page_id=(\d+)', ad_lib_content)
                if match:
                    print(f"       [AdLib] Found page_id in Ad Library: {match.group(1)}")
                    return match.group(1)
            
            return None
            
        except Exception as e:
            print(f"       [!] Error extracting page_id: {e}")
            return None
    
    async def scrape_ad_library(
        self, 
        ad_library_url: str, 
        limit: int = 20,
        brand_name: str = "brand"
    ) -> Dict[str, Any]:
        """
        Scrape ads from Facebook Ad Library.
        
        Args:
            ad_library_url: URL of the Ad Library page
            limit: Maximum number of ads to scrape
            brand_name: Name of the brand for file naming
            
        Returns:
            Dict with ads data and metadata
        """
        brand_slug = re.sub(r'[^a-z0-9]+', '_', brand_name.lower()).strip('_')
        brand_dir = self._setup_directories(brand_slug)
        
        print(f"    -> Scraping Ad Library for {brand_name}...")
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                # Scrape the main Ad Library page
                response = await client.post(
                    f"{self.base_url}/scrape",
                    headers=self._get_headers(),
                    json={
                        "url": ad_library_url,
                        "formats": ["markdown", "links"],
                        "waitFor": 5000
                    }
                )
                response.raise_for_status()
                result = response.json()
                
                if not result.get("success"):
                    return {"ads": [], "error": "Scrape failed"}
                
                markdown = result.get("data", {}).get("markdown", "")
                
                # Validate that the page matches the expected brand
                if markdown and brand_name.lower() != "brand":
                    # Try multiple patterns to extract page name from markdown
                    page_name_patterns = [
                        r'\[([^\]]+)\]\(https://(?:www\.)?facebook\.com/[^/]+\)\s*\*\*Sponsored\*\*',  # Page name before Sponsored
                        r'^#\s*([^\n]+)',  # Title header
                        r'Page:\s*([^\n]+)',  # Explicit Page label
                        r'About this ad\s*\n+([^\n]+)',  # After About this ad
                    ]
                    found_page_name = None
                    for pattern in page_name_patterns:
                        match = re.search(pattern, markdown)
                        if match:
                            found_page_name = match.group(1).strip()
                            break
                    
                    if found_page_name:
                        brand_name_lower = brand_name.lower().replace('-', '').replace(' ', '')
                        found_lower = found_page_name.lower().replace('-', '').replace(' ', '')
                        
                        # Check if names match (fuzzy match)
                        if brand_name_lower not in found_lower and found_lower not in brand_name_lower:
                            print(f"    [!] WARN: Page name '{found_page_name}' may not match brand '{brand_name}'")
                        else:
                            print(f"    [+] Brand validated: '{found_page_name}' matches '{brand_name}'")
                
                # Parse ads from markdown, filtering by expected brand
                ads = self._parse_ads_from_markdown(markdown, limit, expected_brand=brand_name)
                
                if not ads:
                    print(f"    [!] No ads found in initial scrape, trying individual pages...")
                    # Try to get Library IDs and scrape individually
                    library_ids = re.findall(r'Library ID[:\s]+(\d+)', markdown)
                    library_ids = list(dict.fromkeys(library_ids))[:limit]
                    
                    print(f"    [DEBUG] Found {len(library_ids)} Library IDs in markdown")
                    
                    for lib_id in library_ids:
                        ad_url = f"https://www.facebook.com/ads/library/?id={lib_id}"
                        ad_data = await self._scrape_single_ad(client, ad_url, lib_id)
                        if ad_data:
                            ads.append(ad_data)
                
                print(f"    [+] Found {len(ads)} ads")
                
                # Download media for each ad
                total_ads = len(ads)
                print(f"       [AdLib] Processing {total_ads} ads for download...")
                for i, ad in enumerate(ads, 1):
                    ad_id = ad.get("library_id", "unknown")
                    ad_type = "VIDEO" if ad.get("has_video") else "IMAGE"
                    print(f"       [{i}/{total_ads}] Ad {ad_id} ({ad_type})")
                    
                    if ad.get("has_video"):
                        video_path = await self._download_video(
                            ad["ad_library_url"],
                            brand_dir / "videos",
                            brand_slug,
                            ad["library_id"]
                        )
                        if video_path:
                            ad["media_file"] = str(video_path)
                            # Update media_url to point to local API endpoint
                            # Remove 'output/' prefix since endpoint already adds it
                            relative_path = str(video_path).replace("\\", "/")
                            if relative_path.startswith("output/"):
                                relative_path = relative_path[7:]  # Remove 'output/'
                            ad["media_url"] = f"/api/research/videos/{relative_path}"
                            
                            # Generate thumbnail from first frame
                            thumb_path = self._generate_video_thumbnail(str(video_path))
                            if thumb_path:
                                thumb_relative = thumb_path.replace("\\", "/")
                                if thumb_relative.startswith("output/"):
                                    thumb_relative = thumb_relative[7:]
                                ad["thumbnail_url"] = f"/api/research/videos/{thumb_relative}"
                            else:
                                # Fallback: use video URL (won't show as image but allows click to play)
                                ad["thumbnail_url"] = ad["media_url"]
                            
                            print(f"           -> Downloaded: {video_path.name}")
                        else:
                            print(f"           -> FAILED to download video")
                    else:
                        image_url = ad.get("image_url")
                        if image_url:
                            image_path = await self._download_image(
                                image_url,
                                brand_dir / "images",
                                brand_slug,
                                ad["library_id"]
                            )
                            if image_path:
                                ad["media_file"] = str(image_path)
                                # Update media_url/thumbnail_url to point to local file
                                # Remove 'output/' prefix since endpoint already adds it
                                relative_path = str(image_path).replace("\\", "/")
                                if relative_path.startswith("output/"):
                                    relative_path = relative_path[7:]  # Remove 'output/'
                                ad["media_url"] = f"/api/research/videos/{relative_path}"
                                ad["thumbnail_url"] = f"/api/research/videos/{relative_path}"
                                print(f"           -> Downloaded: {image_path.name}")
                            else:
                                print(f"           -> FAILED to download image")
                        else:
                            print(f"           -> No image URL available")
                
                # Extract page_id from URL
                page_id = self._extract_page_id(ad_library_url)
                
                result_data = {
                    "brand": brand_name,
                    "brand_slug": brand_slug,
                    "page_id": page_id,
                    "scrape_date": datetime.now().isoformat(),
                    "ad_library_url": ad_library_url,
                    "total_ads": len(ads),
                    "video_ads_count": len([a for a in ads if a.get("has_video")]),
                    "image_ads_count": len([a for a in ads if not a.get("has_video")]),
                    "ads": ads
                }
                
                # Save to JSON
                json_path = brand_dir / f"{brand_slug}_ads.json"
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(result_data, f, indent=2, ensure_ascii=False)
                
                return result_data
                
            except Exception as e:
                print(f"    [!] Error scraping Ad Library: {e}")
                return {"ads": [], "error": str(e)}
    
    async def _scrape_single_ad(
        self, 
        client: httpx.AsyncClient, 
        url: str, 
        library_id: str
    ) -> Optional[Dict[str, Any]]:
        """Scrape a single ad page."""
        try:
            response = await client.post(
                f"{self.base_url}/scrape",
                headers=self._get_headers(),
                json={
                    "url": url,
                    "formats": ["markdown"],
                    "waitFor": 3000
                }
            )
            response.raise_for_status()
            result = response.json()
            
            if not result.get("success"):
                return None
            
            markdown = result.get("data", {}).get("markdown", "")
            
            # Parse the single ad
            ad = {
                "library_id": library_id,
                "brand_name": self._extract_brand_name(markdown),
                "start_date": self._extract_date(markdown),
                "status": "Active" if "Active" in markdown else "Unknown",
                "ad_copy": self._extract_ad_copy(markdown),
                "discount_code": self._extract_discount_code(markdown),
                "cta": self._extract_cta(markdown),
                "has_video": "trouble playing this video" in markdown.lower(),
                "platforms": self._extract_platforms(markdown),
                "ad_library_url": url,
                "image_url": self._extract_image_url(markdown),
                # Frontend-compatible fields
                "thumbnail_url": self._extract_image_url(markdown),
                "media_url": self._extract_image_url(markdown),
                "media_type": "video" if "trouble playing this video" in markdown.lower() else "image"
            }
            
            return ad
            
        except Exception as e:
            print(f"    [!] Error scraping ad {library_id}: {e}")
            return None
    
    def _parse_ads_from_markdown(self, markdown: str, limit: int = 20, expected_brand: str = None) -> List[Dict[str, Any]]:
        """Extract ad information from markdown content.
        
        Args:
            markdown: The markdown content from Ad Library scrape
            limit: Maximum number of ads to return
            expected_brand: If provided, only return ads from this brand (fuzzy match)
        """
        ads = []
        
        # Find all Library IDs
        library_ids = re.findall(r'Library ID[:\s]+(\d+)', markdown)
        library_ids = list(dict.fromkeys(library_ids))[:limit]
        
        # Split into sections by Library ID
        sections = re.split(r'(?=Library ID[:\s]+\d+)', markdown)
        
        for section in sections:
            id_match = re.search(r'Library ID[:\s]+(\d+)', section)
            if not id_match:
                continue
            
            library_id = id_match.group(1)
            if library_id not in library_ids:
                continue
            if any(ad['library_id'] == library_id for ad in ads):
                continue
            if len(ads) >= limit:
                break
            
            # Detect if this ad is a video (multiple detection patterns - EXPANDED)
            section_lower = section.lower()
            has_video = any([
                "trouble playing this video" in section_lower,
                "video" in section_lower and ("play" in section_lower or "watch" in section_lower),
                ".mp4" in section_lower,
                ".webm" in section_lower,
                ".mov" in section_lower,
                "video ad" in section_lower,
                "video creative" in section_lower,
                "see video" in section_lower,
                "watch video" in section_lower,
                "play video" in section_lower,
                "video_hd_url" in section_lower,
                "video_sd_url" in section_lower,
                "displayformat.*video" in section_lower,
                "media_type.*video" in section_lower,
            ])
            
            ad = {
                "library_id": library_id,
                "brand_name": self._extract_brand_name(section),
                "start_date": self._extract_date(section),
                "status": "Active" if "Active" in section else "Unknown",
                "ad_copy": self._extract_ad_copy(section),
                "discount_code": self._extract_discount_code(section),
                "cta": self._extract_cta(section),
                "has_video": has_video,
                "platforms": self._extract_platforms(section),
                "ad_library_url": f"https://www.facebook.com/ads/library/?id={library_id}",
                "image_url": self._extract_image_url(section),
                # Frontend-compatible fields
                "thumbnail_url": self._extract_image_url(section),
                "media_url": self._extract_image_url(section),
                "media_type": "video" if has_video else "image"
            }
            
            # Filter by expected brand if provided
            if expected_brand:
                ad_brand = (ad.get("brand_name") or "").lower().replace("-", "").replace(" ", "")
                expected_clean = expected_brand.lower().replace("-", "").replace(" ", "")
                # Allow ads from: matching brand OR unknown brand (couldn't extract name)
                if ad_brand and ad_brand != "unknown":
                    if expected_clean not in ad_brand and ad_brand not in expected_clean:
                        print(f"       [AdLib] Filtered out ad from '{ad.get('brand_name')}' (expected '{expected_brand}')")
                        continue  # Skip ads from other brands
            
            ads.append(ad)
        
        # Sort by start_date (oldest first = longer running = likely higher spend)
        # Parse dates and sort
        from datetime import datetime as dt
        def parse_date(date_str):
            if not date_str:
                return dt.max  # Ads without dates go last
            try:
                return dt.strptime(date_str, "%B %d, %Y")
            except:
                try:
                    return dt.strptime(date_str, "%b %d, %Y")  
                except:
                    return dt.max
        
        ads.sort(key=lambda x: parse_date(x.get("start_date")))
        
        # Deduplicate by similar ad_copy (keep oldest of each unique copy)
        seen_copies = set()
        unique_ads = []
        for ad in ads:
            copy = (ad.get("ad_copy") or "")[:100].lower().strip()
            if copy and copy in seen_copies:
                continue  # Skip duplicate creative
            if copy:
                seen_copies.add(copy)
            unique_ads.append(ad)
        
        print(f"       [AdLib] {len(ads)} ads found, {len(unique_ads)} unique, sorted by run time")
        
        return unique_ads[:limit]
    
    def _extract_page_id(self, url: str) -> Optional[str]:
        """Extract page_id from Ad Library URL."""
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        return params.get('view_all_page_id', [None])[0]
    
    def _extract_brand_name(self, text: str) -> str:
        """Extract brand name from ad text."""
        match = re.search(r'\[([^\]]+)\]\(https://(?:www\.)?facebook\.com/[^)]+\)\s*\*\*Sponsored\*\*', text)
        if match:
            return match.group(1)
        match = re.search(r'\[([^\]]+)\]\(https://facebook\.com', text)
        return match.group(1) if match else "Unknown"
    
    def _extract_date(self, text: str) -> Optional[str]:
        """Extract start date from ad text."""
        match = re.search(r'Started running on ([A-Za-z]+ \d+, \d+)', text)
        return match.group(1) if match else None
    
    def _extract_ad_copy(self, text: str) -> Optional[str]:
        """Extract ad copy text."""
        match = re.search(r'\*\*Sponsored\*\*\s*\n\n(.+?)(?=\n\n\[|\n\nSorry|$)', text, re.DOTALL)
        if match:
            copy = match.group(1).strip()
            copy = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', copy)
            return copy
        return None
    
    def _extract_discount_code(self, text: str) -> Optional[str]:
        """Extract discount codes from ad text."""
        match = re.search(r'Code[:\s]+([A-Z0-9]+)', text, re.IGNORECASE)
        return match.group(1) if match else None
    
    def _extract_cta(self, text: str) -> Optional[str]:
        """Extract call-to-action from ad text."""
        patterns = [
            r'\[([^\]]*Shop Now[^\]]*)\]',
            r'\[([^\]]*Learn more[^\]]*)\]',
            r'\[([^\]]*Sign up[^\]]*)\]',
            r'\[([^\]]*Get Started[^\]]*)\]',
            r'\[([^\]]*Buy Now[^\]]*)\]',
            r'(\d+% Off[^|\n]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    
    def _extract_platforms(self, text: str) -> List[str]:
        """Extract platforms where ad is shown."""
        platforms = []
        if 'facebook' in text.lower() or 'fb.com' in text.lower():
            platforms.append('Facebook')
        if 'instagram' in text.lower():
            platforms.append('Instagram')
        if 'messenger' in text.lower():
            platforms.append('Messenger')
        if 'audience network' in text.lower():
            platforms.append('Audience Network')
        if not platforms:
            platforms = ['Facebook', 'Instagram', 'Audience Network', 'Messenger']
        return platforms
    
    def _extract_image_url(self, text: str) -> Optional[str]:
        """Extract image URL from markdown. Tries multiple patterns."""
        # Try preferred 600x600 first
        urls = re.findall(r'https://scontent[^\s\)\"]+s600x600[^\s\)\"]+', text)
        if urls:
            return urls[0]
        # Try any scontent image URL with common image extensions
        urls = re.findall(r'https://scontent[^\s\)\"]+\.(?:jpg|png|jpeg|webp)[^\s\)\"]*', text)
        if urls:
            return urls[0]
        # Try any scontent URL (sometimes no extension visible)
        urls = re.findall(r'https://scontent[^\s\)\"]+', text)
        if urls:
            return urls[0]
        # Last resort: any image URL
        urls = re.findall(r'https://[^\s\)\"]+\.(?:jpg|png|jpeg|webp)[^\s\)\"]*', text)
        return urls[0] if urls else None
    
    async def _download_video(
        self, 
        ad_url: str, 
        output_dir: Path,
        brand_slug: str,
        library_id: str
    ) -> Optional[Path]:
        """Download video using yt-dlp with cookie file or browser cookies for auth."""
        output_path = output_dir / f"{brand_slug}_ad_{library_id}.mp4"
        
        # Check for cookie file first (most reliable)
        cookie_file = Path(__file__).parent.parent.parent.parent / "facebook_cookies.txt"
        alt_cookie_file = Path("facebook_cookies.txt")  # Also check current dir
        
        try:
            # Check if yt-dlp is available
            result = subprocess.run(
                ['yt-dlp', '--version'],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print(f"    [!] yt-dlp not installed")
                return None
            
            # Method 1: Try with cookie file if exists
            cookies_path = None
            if cookie_file.exists():
                cookies_path = cookie_file
                print(f"       -> Using cookie file: {cookie_file}")
            elif alt_cookie_file.exists():
                cookies_path = alt_cookie_file
                print(f"       -> Using cookie file: {alt_cookie_file}")
            
            if cookies_path:
                result = subprocess.run([
                    'yt-dlp',
                    '-o', str(output_path),
                    '--no-warnings',
                    '-q',
                    '-f', 'best[ext=mp4]/best',
                    '--socket-timeout', '30',
                    '--retries', '3',
                    '--cookies', str(cookies_path),
                    ad_url
                ], capture_output=True, text=True, timeout=180)
                
                if output_path.exists():
                    print(f"       [+] Downloaded video {library_id} with cookie file")
                    return output_path
                
                for ext in ['.mp4', '.webm', '.mkv']:
                    alt_path = output_dir / f"{brand_slug}_ad_{library_id}{ext}"
                    if alt_path.exists():
                        print(f"       [+] Downloaded video {library_id} as {ext}")
                        return alt_path
                
                if "403" in result.stderr:
                    print(f"       [!] Cookie file auth failed - cookies may be expired")
            
            # Method 2: Try browsers in order of preference for cookie extraction
            browsers_to_try = ['chrome', 'firefox', 'edge', 'brave', 'chromium']
            
            for browser in browsers_to_try:
                print(f"       -> Trying to download video {library_id} with {browser} cookies...")
                
                result = subprocess.run([
                    'yt-dlp',
                    '-o', str(output_path),
                    '--no-warnings',
                    '-q',
                    '-f', 'best[ext=mp4]/best',
                    '--socket-timeout', '30',
                    '--retries', '3',
                    '--cookies-from-browser', browser,
                    ad_url
                ], capture_output=True, text=True, timeout=180)
                
                if output_path.exists():
                    print(f"       [+] Downloaded video {library_id} successfully")
                    return output_path
                
                for ext in ['.mp4', '.webm', '.mkv']:
                    alt_path = output_dir / f"{brand_slug}_ad_{library_id}{ext}"
                    if alt_path.exists():
                        print(f"       [+] Downloaded video {library_id} as {ext}")
                        return alt_path
                
                # Check if browser doesn't exist or no cookies
                if "could not find" in result.stderr.lower() or "no cookies" in result.stderr.lower():
                    continue
                
                # If we got a different error (not auth), don't try other browsers
                if "403" not in result.stderr and "client challenge" not in result.stderr.lower():
                    break
            
            print(f"       [!] Could not download video {library_id} - auth required")
            return None
            
        except subprocess.TimeoutExpired:
            print(f"    [!] Video download timeout: {library_id}")
            return None
        except Exception as e:
            print(f"    [!] Video download error: {e}")
            return None
    
    async def _download_video_direct(
        self,
        video_url: str,
        output_dir: Path,
        brand_slug: str,
        library_id: str
    ) -> Optional[Path]:
        """
        Download video directly from URL (no auth needed).
        Used for Apify-provided video URLs which are public.
        """
        output_path = output_dir / f"{brand_slug}_ad_{library_id}.mp4"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "video/mp4,video/*,*/*",
            "Referer": "https://www.facebook.com/",
        }
        for attempt in range(1, 3):  # 2 attempts
            try:
                async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
                    print(f"       -> Downloading video {library_id} (attempt {attempt})...")
                    # Stream to disk to avoid loading huge files into memory
                    async with client.stream("GET", video_url, headers=headers) as response:
                        if response.status_code != 200:
                            print(f"       [!] Video {library_id}: HTTP {response.status_code}")
                            break
                        total_bytes = 0
                        with open(output_path, 'wb') as f:
                            async for chunk in response.aiter_bytes(chunk_size=65536):
                                f.write(chunk)
                                total_bytes += len(chunk)
                    if total_bytes > 10000:
                        size_mb = total_bytes / (1024 * 1024)
                        print(f"       [+] Downloaded video {library_id} ({size_mb:.1f} MB)")
                        return output_path
                    else:
                        print(f"       [!] Video {library_id}: too small ({total_bytes} bytes), likely error response")
                        output_path.unlink(missing_ok=True)
            except httpx.TimeoutException:
                print(f"       [!] Video {library_id}: timeout on attempt {attempt}")
            except Exception as e:
                print(f"       [!] Video {library_id} error (attempt {attempt}): {str(e)[:60]}")
        return None
    
    async def _download_image(
        self, 
        image_url: str, 
        output_dir: Path,
        brand_slug: str,
        library_id: str
    ) -> Optional[Path]:
        """Download image from URL."""
        output_path = output_dir / f"{brand_slug}_ad_{library_id}.jpg"
        
        try:
            # Reduced timeout to 15s to prevent hanging
            async with httpx.AsyncClient(timeout=15.0) as client:
                print(f"       -> Downloading image {library_id}...")
                response = await client.get(image_url)
                if response.status_code == 200 and len(response.content) > 1000:
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    return output_path
                else:
                    print(f"       [!] Image {library_id}: status={response.status_code}, size={len(response.content)}")
            return None
        except httpx.TimeoutException:
            print(f"       [!] Image {library_id}: timeout after 15s")
            return None
        except Exception as e:
            print(f"       [!] Image {library_id} error: {str(e)[:50]}")
            return None
    
    async def _extract_social_from_website(self, website_url: str) -> Dict[str, str]:
        """
        Fetch a website and extract social media URLs (IG, FB, Twitter, etc) from its HTML.
        Uses the same regex patterns as BrandDNA._extract_social_links.
        
        Args:
            website_url: URL to fetch and parse
            
        Returns:
            Dict like {"instagram": "https://instagram.com/handle", "facebook": "https://facebook.com/page"}
        """
        social = {}
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(
                    website_url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
                )
                html = response.text
                
                # Extract all href URLs from HTML
                all_urls = re.findall(r'href=["\'](https?://[^"\']+)["\']', html, re.IGNORECASE)
                
                # Social media patterns (same as BrandDNA._extract_social_links)
                social_patterns = {
                    "instagram": [r'instagram\.com/([a-zA-Z0-9._]+)'],
                    "facebook": [r'facebook\.com/([a-zA-Z0-9._-]+)'],
                    "twitter": [r'twitter\.com/([^/\s"\'?]+)', r'x\.com/([^/\s"\'?]+)'],
                }
                
                # Excluded handles (generic paths, not actual profiles)
                excluded = {
                    'explore', 'reels', 'stories', 'p', 'tv', 'reel', 'accounts',  # IG
                    'ads', 'watch', 'groups', 'events', 'marketplace', 'gaming', 'login', 'help', 'pages', 'sharer',  # FB
                    'intent', 'share', 'search', 'hashtag', 'home',  # Twitter
                }
                
                for url in all_urls:
                    for platform, patterns in social_patterns.items():
                        if platform in social:
                            continue
                        for pattern in patterns:
                            match = re.search(pattern, url, re.IGNORECASE)
                            if match and match.group(1).lower() not in excluded:
                                social[platform] = url
                                break
                                
        except Exception as e:
            print(f"       [!] Website social extraction error: {str(e)[:60]}")
        
        return social

    async def scrape_competitor_ads(
        self,
        competitor_name: str,
        competitor_url: Optional[str] = None,
        facebook_url: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Scrape ads for any brand (main brand or competitor).

        Chain of strategies (stop at first that yields real ads):
          1. Facebook page URL (gives fullest metadata: videos + media URLs)
          2. Ad Library keyword_exact_phrase (precise filter, sometimes image-only)
          3. Ad Library page search (loose match; last resort)

        Earlier single-strategy versions either short-circuited on Apify error
        records or returned image-only metadata for competitors.
        """
        from .apify_facebook import get_apify_facebook_service
        apify = get_apify_facebook_service()
        from urllib.parse import quote
        print(f"    -> Scraping: {competitor_name}...")

        # Normalize incoming FB URL if provided
        facebook_url = normalize_fb_page_url(facebook_url) if facebook_url else None

        # STEP 0: Discover FB URL if not provided (keep the existing discovery)
        discovered_fb_url = facebook_url
        if not discovered_fb_url and competitor_url:
            social = await self._extract_social_from_website(competitor_url)
            if social.get("facebook"):
                discovered_fb_url = normalize_fb_page_url(social["facebook"])
                if discovered_fb_url:
                    print(f"       [Website] Found FB: {discovered_fb_url[:60]}")

        # STRATEGY 1: Facebook page URL (most complete metadata)
        if discovered_fb_url:
            p_match = re.search(r'facebook\.com/p/[^/]*?-(\d{10,})', discovered_fb_url)
            if p_match:
                extracted_pid = p_match.group(1)
                print(f"       Strategy 1: Extracted page_id from /p/ URL: {extracted_pid}")
                raw_ads = await apify.scrape_by_page_id(extracted_pid, limit=limit)
            else:
                print(f"       Strategy 1: FB URL -> {discovered_fb_url[:60]}")
                raw_ads = await apify.scrape_by_facebook_url(discovered_fb_url, limit=limit)
            if raw_ads:
                filtered = apify.filter_by_page_name(raw_ads, competitor_name)
                if filtered:
                    result = await self.process_raw_apify_ads(filtered, competitor_name, limit)
                    # Only return if we got REAL ads with ad_archive_id — otherwise
                    # the strategy effectively failed and we fall through.
                    if result and result.get("ads"):
                        result["competitor_name"] = competitor_name
                        return result
                    print(f"       Strategy 1: filtered records were all Apify garbage — falling through")

        # STRATEGY 2: keyword_exact_phrase search (precise brand match)
        print(f"       Strategy 2: keyword_exact_phrase '{competitor_name}'")
        exact_url = (
            f"https://www.facebook.com/ads/library/"
            f"?active_status=active&ad_type=all&country=ALL"
            f"&q={quote(competitor_name)}&search_type=keyword_exact_phrase&media_type=all"
        )
        raw_ads = await apify._run_actor(exact_url, limit)
        if raw_ads:
            filtered = apify.filter_by_page_name(raw_ads, competitor_name)
            if filtered:
                result = await self.process_raw_apify_ads(filtered, competitor_name, limit)
                if result and result.get("ads"):
                    result["competitor_name"] = competitor_name
                    return result

        # STRATEGY 3: Page name search (loose; may include similar pages)
        print(f"       Strategy 3: page name search '{competitor_name}'")
        raw_ads = await apify.scrape_by_page_name(competitor_name, limit=limit)
        if raw_ads:
            filtered = apify.filter_by_page_name(raw_ads, competitor_name)
            if filtered:
                result = await self.process_raw_apify_ads(filtered, competitor_name, limit)
                if result and result.get("ads"):
                    result["competitor_name"] = competitor_name
                    return result

        print(f"    [!] Could not find ads for {competitor_name}")
        return {"competitor_name": competitor_name, "ads": [], "error": "No ads found"}

    async def process_raw_apify_ads(
        self,
        raw_ads: List[Dict[str, Any]],
        brand_name: str,
        limit: int = 200
    ) -> Dict[str, Any]:
        """
        Process raw ads from curious_coder Apify actor: extract URLs, download media, build output.
        This is the shared processing pipeline used by both brand and competitor ad scraping.

        Args:
            raw_ads: Raw ad dicts from curious_coder actor (with snapshot structure)
            brand_name: Brand name for file naming
            limit: Max ads to process

        Returns:
            Dict with processed ads, metadata, and downloaded media paths
        """
        from .apify_facebook import get_apify_facebook_service
        apify_service = get_apify_facebook_service()

        brand_slug = re.sub(r'[^a-z0-9]+', '_', brand_name.lower()).strip('_')
        brand_dir = self._setup_directories(brand_slug)

        # Drop Apify garbage records (no ad_archive_id = no real ad).
        # Apify occasionally returns placeholder records for pages with no active ads,
        # which used to become stub "unknown_1" ads that polluted downstream pipelines
        # (e.g. Il Makiage session 129 got 1 stub instead of real ads).
        valid_raw_ads = [
            r for r in raw_ads
            if r.get("ad_archive_id") or r.get("adArchiveID")
        ]
        dropped = len(raw_ads) - len(valid_raw_ads)
        if dropped:
            print(f"    [Process] Dropped {dropped} Apify records without ad_archive_id (garbage)")
        raw_ads = valid_raw_ads

        # Apply diversity filter
        raw_ads = self._filter_diverse_ads(raw_ads, limit)

        ads = []
        total_ads = len(raw_ads)
        print(f"    [Process] Processing {total_ads} ads for {brand_name}...")

        for i, raw_ad in enumerate(raw_ads[:limit], 1):
            snapshot = raw_ad.get("snapshot") or {}

            # ID — ad_archive_id is guaranteed by the filter above
            ad_id = str(raw_ad.get("ad_archive_id") or raw_ad.get("adArchiveID"))

            # Format detection
            display_format = snapshot.get("displayFormat") or raw_ad.get("display_format") or ""
            is_video = str(display_format).upper() in ("VIDEO", "VIDEO_AD", "VIDEO_CREATIVE")

            # Video URL extraction (curious_coder: snapshot.videos[].video_hd_url)
            video_url = apify_service.extract_video_url(raw_ad)
            if video_url and not is_video:
                is_video = True

            # Image URL extraction
            image_url = apify_service.extract_image_url(raw_ad)

            # Fix display_format from media presence
            if not display_format or display_format == "UNKNOWN":
                if video_url:
                    display_format = "VIDEO"
                    is_video = True
                elif image_url:
                    display_format = "IMAGE"

            # Page name and ad body
            page_name = raw_ad.get("page_name") or snapshot.get("pageName") or brand_name
            ad_body = snapshot.get("body") or raw_ad.get("ad_body") or ""
            if isinstance(ad_body, dict):
                ad_body = ad_body.get("text", "")

            print(f"       [{i}/{total_ads}] Ad {ad_id} (format={display_format}, video={'Y' if is_video else 'N'}, url={'Y' if video_url else 'N'})")

            ad = {
                "library_id": ad_id,
                "page_name": page_name,
                "brand_name": page_name,
                "display_format": display_format,
                "start_date": raw_ad.get("start_date") or raw_ad.get("start_date_formatted"),
                "end_date": raw_ad.get("end_date") or raw_ad.get("end_date_formatted"),
                "status": "Active" if raw_ad.get("is_active") else "Inactive",
                "ad_copy": ad_body,
                "cta": snapshot.get("cta_text") or snapshot.get("ctaText"),
                "has_video": is_video,
                "platforms": raw_ad.get("publisher_platform", []),
                "ad_library_url": f"https://www.facebook.com/ads/library/?id={ad_id}",
                "image_url": image_url,
                "video_hd_url": video_url,
                "thumbnail_url": image_url,
                "media_type": "video" if is_video else "image",
                "link_url": snapshot.get("link_url") or raw_ad.get("link_url"),
            }

            # Download media
            if is_video and video_url:
                video_path = await self._download_video_direct(
                    video_url, brand_dir / "videos", brand_slug, ad_id
                )
                if video_path:
                    ad["media_file"] = str(video_path)
                    rel = str(video_path).replace("\\", "/")
                    if rel.startswith("output/"):
                        rel = rel[7:]
                    ad["media_url"] = f"/api/research/videos/{rel}"
                    thumb_path = self._generate_video_thumbnail(str(video_path))
                    if thumb_path:
                        tr = thumb_path.replace("\\", "/")
                        if tr.startswith("output/"):
                            tr = tr[7:]
                        ad["thumbnail_url"] = f"/api/research/videos/{tr}"
                    print(f"           -> Downloaded video: {video_path.name}")
                else:
                    print(f"           -> FAILED to download video")
            elif image_url:
                image_path = await self._download_image(
                    image_url, brand_dir / "images", brand_slug, ad_id
                )
                if image_path:
                    ad["media_file"] = str(image_path)
                    rel = str(image_path).replace("\\", "/")
                    if rel.startswith("output/"):
                        rel = rel[7:]
                    ad["media_url"] = f"/api/research/videos/{rel}"
                    ad["thumbnail_url"] = ad["media_url"]
                    print(f"           -> Downloaded image: {image_path.name}")

            ads.append(ad)

        result_data = {
            "brand": brand_name,
            "brand_slug": brand_slug,
            "scrape_date": datetime.now().isoformat(),
            "source": "apify",
            "total_ads": len(ads),
            "video_ads_count": len([a for a in ads if a.get("has_video")]),
            "image_ads_count": len([a for a in ads if not a.get("has_video")]),
            "ads": ads
        }

        # Save JSON
        json_path = brand_dir / f"{brand_slug}_ads.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)

        print(f"    [Process] Done: {len(ads)} ads ({result_data['video_ads_count']} video, {result_data['image_ads_count']} image)")
        return result_data

    async def scrape_ad_library_via_apify(
        self,
        page_url: str,
        limit: int = 50,
        brand_name: str = "brand",
        target_page_id: str = None,
        ig_handle: str = None
    ) -> Dict[str, Any]:
        """
        Scrape ads using Apify which provides direct video URLs (no auth needed).
        This is the preferred method as it doesn't require cookies.
        
        Args:
            page_url: Facebook page URL (e.g., https://www.facebook.com/GoodFoodca)
            limit: Maximum ads to scrape
            brand_name: Brand name for file naming
            
        Returns:
            Dict with ads data and metadata
        """
        brand_slug = re.sub(r'[^a-z0-9]+', '_', brand_name.lower()).strip('_')
        brand_dir = self._setup_directories(brand_slug)
        
        print(f"    -> [Apify] Scraping Ad Library for {brand_name}...")
        
        try:
            apify_service = get_apify_facebook_service()
            
            # Get ads via Apify
            raw_ads = await apify_service.scrape_page_ads(
                page_url, limit, brand_name=brand_name, target_page_id=target_page_id
            )
            
            if not raw_ads:
                error_msg = f"Apify returned no ads for {brand_name}. Check: 1) APIFY_API_TOKEN is valid, 2) Facebook page URL is correct, 3) Brand has active ads"
                print(f"    [!] {error_msg}")
                return {"ads": [], "error": error_msg, "source": "apify"}
            
            print(f"    [+] Apify found {len(raw_ads)} ads")

            # For page-based searches, all ads are from the correct page — skip name filtering
            is_page_id_search = 'view_all_page_id=' in page_url or 'search_type=page' in page_url
            if is_page_id_search:
                print(f"       [Filter] Page search — all {len(raw_ads)} ads are from the correct page, skipping name filter")
            else:
                # Name-based filtering for keyword searches
                brand_lower = brand_name.lower().strip()
                ig_lower = (ig_handle or "").lower().strip()
                ig_no_dots = ig_lower.replace(".", "") if ig_lower else ""

                def _tier1(ad):
                    pn = (ad.get('page_name') or '').lower()
                    return brand_lower in pn or (ig_lower and ig_lower in pn)

                def _tier2(ad):
                    pn = (ad.get('page_name') or '').lower()
                    if ig_no_dots and ig_no_dots in pn.replace(".", ""):
                        return True
                    return False

                def _majority_filter(ads):
                    from collections import Counter
                    page_counts = Counter((a.get('page_name') or '').strip() for a in ads)
                    if page_counts:
                        top_name, top_count = page_counts.most_common(1)[0]
                        if top_count >= len(ads) * 0.5 and top_name:
                            return [a for a in ads if (a.get('page_name') or '').strip() == top_name], top_name
                    return None, None

                filtered = [a for a in raw_ads if _tier1(a)]
                if filtered:
                    print(f"       [Filter] Tier 1: Kept {len(filtered)}/{len(raw_ads)} ads matching '{brand_name}' or '{ig_handle}'")
                    raw_ads = filtered
                else:
                    filtered = [a for a in raw_ads if _tier2(a)]
                    if filtered:
                        print(f"       [Filter] Tier 2: Kept {len(filtered)}/{len(raw_ads)} ads via handle-no-dots '{ig_no_dots}'")
                        raw_ads = filtered
                    else:
                        majority, majority_name = _majority_filter(raw_ads)
                        if majority:
                            # Validate majority name has some relationship to brand
                            from difflib import SequenceMatcher
                            similarity = SequenceMatcher(None, brand_lower, majority_name.lower()).ratio()
                            if similarity >= 0.3 or brand_lower in majority_name.lower() or majority_name.lower() in brand_lower:
                                print(f"       [Filter] Tier 3: Kept {len(majority)}/{len(raw_ads)} ads from '{majority_name}' (similarity={similarity:.2f})")
                                raw_ads = majority
                            else:
                                print(f"       [Filter] Tier 3: REJECTED majority '{majority_name}' (similarity={similarity:.2f} to '{brand_name}') -- returning empty to avoid wrong-brand ads")
                                raw_ads = []
                        else:
                            print(f"       [!!! FILTER] No page_name matched '{brand_name}' / '{ig_handle}' -- returning empty to avoid wrong-brand ads")
                            raw_ads = []
            
            # Drop Apify garbage records (no ad_archive_id = no real ad)
            valid_raw_ads = [
                r for r in raw_ads
                if r.get("ad_archive_id") or r.get("adArchiveID")
            ]
            dropped_here = len(raw_ads) - len(valid_raw_ads)
            if dropped_here:
                print(f"       [Process] Dropped {dropped_here} records without ad_archive_id (garbage)")
            raw_ads = valid_raw_ads

            # Apply diversity filter: prioritize long-running ads, deduplicate variations
            raw_ads = self._filter_diverse_ads(raw_ads, limit)

            # Process ads and download media
            ads = []
            total_ads = len(raw_ads)

            for i, raw_ad in enumerate(raw_ads[:limit], 1):
                # Handle both old (curious_coder) and new (agenscrape) actor structures
                # agenscrape uses: ad_archive_id, display_format, videos[], images[], ad_body
                # curious_coder used: adArchiveID, snapshot.displayFormat, snapshot.videos, snapshot.body

                # ad_archive_id guaranteed by filter above
                ad_id = raw_ad.get("ad_archive_id") or raw_ad.get("adArchiveID")
                display_format = raw_ad.get("display_format") or raw_ad.get("snapshot", {}).get("displayFormat", "UNKNOWN")
                
                # More robust video detection
                is_video = str(display_format).upper() in ["VIDEO", "VIDEO_AD", "VIDEO_CREATIVE"]
                
                # Extract video URL - try all known field name variants from agenscrape + curious_coder
                video_url = None
                videos = raw_ad.get("videos", [])
                if videos and len(videos) > 0:
                    v = videos[0]
                    video_url = (
                        v.get("hd_url") or v.get("sd_url") or         # agenscrape flat
                        v.get("videoHdUrl") or v.get("videoSdUrl") or  # curious_coder camelCase
                        v.get("video_hd_url") or v.get("video_sd_url") or  # snake_case variants
                        v.get("url")                                    # generic fallback
                    )
                if not video_url:
                    # Try top-level fields (some actors put URLs here)
                    video_url = (
                        raw_ad.get("video_hd_url") or raw_ad.get("video_sd_url") or
                        raw_ad.get("videoHdUrl") or raw_ad.get("videoSdUrl")
                    )
                if not video_url:
                    video_url = apify_service.extract_video_url(raw_ad)  # snapshot.videos fallback

                if video_url and not is_video:
                    print(f"       [!] Ad {ad_id} has video URL but displayFormat={display_format}, treating as video")
                    is_video = True

                # Extract image URL - try all known field name variants
                image_url = None
                images = raw_ad.get("images", [])
                if images and len(images) > 0:
                    first_img = images[0]
                    if isinstance(first_img, dict):
                        image_url = (
                            first_img.get("original_url") or
                            first_img.get("originalImageUrl") or       # curious_coder
                            first_img.get("original_image_url") or     # snake_case
                            first_img.get("resized_url") or
                            first_img.get("resizedImageUrl") or
                            first_img.get("resized_image_url") or
                            first_img.get("url") or
                            first_img.get("src")
                        )
                    elif isinstance(first_img, str):
                        image_url = first_img
                if not image_url:
                    image_url = apify_service.extract_image_url(raw_ad)
                
                thumbnail_url = image_url  # Use image as thumbnail

                # Fix display_format when agenscrape returns None — detect from media presence
                if not display_format or display_format == "UNKNOWN":
                    if video_url or (videos and len(videos) > 0):
                        display_format = "VIDEO"
                        is_video = True
                    elif image_url or (images and len(images) > 0):
                        display_format = "IMAGE"

                print(f"       [{i}/{total_ads}] Ad {ad_id} (format={display_format}, video={'YES' if is_video else 'NO'}, url={'YES' if video_url else 'NO'})")
                
                # Build ad data structure - handle both actor formats
                page_name = raw_ad.get("page_name") or raw_ad.get("snapshot", {}).get("pageName", brand_name)
                ad_body = raw_ad.get("ad_body") or raw_ad.get("snapshot", {}).get("body")
                if isinstance(ad_body, dict):
                    ad_body = ad_body.get("text", "")
                
                ad = {
                    "library_id": ad_id,
                    "brand_name": page_name,
                    "start_date": raw_ad.get("start_date") or raw_ad.get("startDateFormatted"),
                    "end_date": raw_ad.get("end_date") or raw_ad.get("endDateFormatted"),
                    "status": "Active" if raw_ad.get("is_active", raw_ad.get("isActive")) else "Inactive",
                    "ad_copy": ad_body,
                    "cta": raw_ad.get("cta_text") or raw_ad.get("snapshot", {}).get("ctaText"),
                    "has_video": is_video,
                    "platforms": raw_ad.get("publisher_platform") or raw_ad.get("publisherPlatform", []),
                    "ad_library_url": f"https://www.facebook.com/ads/library/?id={ad_id}",
                    "image_url": image_url,
                    "video_hd_url": video_url,
                    "thumbnail_url": thumbnail_url or image_url,
                    "media_type": "video" if is_video else "image",
                    "link_url": raw_ad.get("link_url"),
                }
                
                # Download media
                if is_video and video_url:
                    video_path = await self._download_video_direct(
                        video_url,
                        brand_dir / "videos",
                        brand_slug,
                        ad_id
                    )
                    if video_path:
                        ad["media_file"] = str(video_path)
                        relative_path = str(video_path).replace("\\", "/")
                        if relative_path.startswith("output/"):
                            relative_path = relative_path[7:]
                        ad["media_url"] = f"/api/research/videos/{relative_path}"
                        
                        # Generate thumbnail
                        thumb_path = self._generate_video_thumbnail(str(video_path))
                        if thumb_path:
                            thumb_relative = thumb_path.replace("\\", "/")
                            if thumb_relative.startswith("output/"):
                                thumb_relative = thumb_relative[7:]
                            ad["thumbnail_url"] = f"/api/research/videos/{thumb_relative}"
                        
                        print(f"           -> Downloaded: {video_path.name}")
                    else:
                        print(f"           -> FAILED to download video")
                        
                elif image_url:
                    image_path = await self._download_image(
                        image_url,
                        brand_dir / "images",
                        brand_slug,
                        ad_id
                    )
                    if image_path:
                        ad["media_file"] = str(image_path)
                        relative_path = str(image_path).replace("\\", "/")
                        if relative_path.startswith("output/"):
                            relative_path = relative_path[7:]
                        ad["media_url"] = f"/api/research/videos/{relative_path}"
                        ad["thumbnail_url"] = ad["media_url"]
                        print(f"           -> Downloaded: {image_path.name}")
                
                ads.append(ad)
            
            # Build result
            result_data = {
                "brand": brand_name,
                "brand_slug": brand_slug,
                "scrape_date": datetime.now().isoformat(),
                "source": "apify",
                "total_ads": len(ads),
                "video_ads_count": len([a for a in ads if a.get("has_video")]),
                "image_ads_count": len([a for a in ads if not a.get("has_video")]),
                "ads": ads
            }
            
            # Save to JSON
            json_path = brand_dir / f"{brand_slug}_ads.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, indent=2, ensure_ascii=False)
            
            return result_data
            
        except Exception as e:
            print(f"    [!] Apify scrape error: {e}")
            return {"ads": [], "error": str(e)}

