"""
Playwright-based Ad Library scraper.
Navigates directly to Ad Library with view_all_page_id and extracts
structured JSON ad data embedded in the page HTML.

This replaces the broken Apify actor which ignores page-specific params.
"""

import asyncio
import re
import time
import json
import concurrent.futures
from typing import Optional, List, Dict, Any
from pathlib import Path
from playwright.sync_api import sync_playwright


class PlaywrightAdScraper:
    """Scrape ads from Facebook Ad Library using Playwright + embedded JSON extraction."""
    
    def __init__(self):
        self.cookies_path = Path(__file__).parent.parent.parent.parent / "facebook_cookies.txt"
    
    def _load_cookies_sync(self, context):
        """Load Facebook cookies from Netscape format file."""
        if not self.cookies_path.exists():
            print("       [PlaywrightAds] No cookies file found -- Ad Library may be limited")
            return
        
        cookies = []
        with open(self.cookies_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split('\t')
                if len(parts) >= 7:
                    cookies.append({
                        'name': parts[5],
                        'value': parts[6],
                        'domain': parts[0],
                        'path': parts[2],
                        'secure': parts[3].lower() == 'true',
                        'httpOnly': False,
                    })
        
        if cookies:
            context.add_cookies(cookies)
            print(f"       [PlaywrightAds] Loaded {len(cookies)} cookies")
    
    def _extract_ads_from_html(self, html: str, page_id: str) -> List[Dict[str, Any]]:
        """
        Extract structured ad data from the embedded JSON in the Ad Library HTML.
        
        Facebook renders ads from a JSON data structure embedded in the page:
        search_results_connection.edges[].node.collated_results[].ad_archive_id
        """
        ads = []
        
        # Strategy 1: Find all ad_archive_id entries with their surrounding JSON context
        # The data appears as: {"ad_archive_id":"XXXXX","collation_count":N,..."page_id":"YYYYY"...}
        
        # Find JSON-like blocks containing ad_archive_id
        pattern = r'\{"ad_archive_id":"(\d+)"[^}]*?"page_id":"(\d+)"[^}]*?\}'
        matches = re.finditer(pattern, html)
        
        seen_ids = set()
        for match in matches:
            ad_id = match.group(1)
            found_page_id = match.group(2)
            
            if ad_id in seen_ids:
                continue
            seen_ids.add(ad_id)
            
            # Get the full JSON block for this ad
            block = match.group(0)
            
            # Extract fields from the JSON block
            ad = {
                "ad_archive_id": ad_id,
                "page_id": found_page_id,
            }
            
            # Extract page_name
            name_match = re.search(r'"page_name":"([^"]*)"', block)
            if name_match:
                ad["page_name"] = name_match.group(1)
            
            # Extract collation_count
            coll_match = re.search(r'"collation_count":(\d+)', block)
            if coll_match:
                ad["collation_count"] = int(coll_match.group(1))
            
            # Extract ad_delivery_start_time
            start_match = re.search(r'"ad_delivery_start_time":"([^"]*)"', block)
            if start_match:
                ad["start_date"] = start_match.group(1)
            
            ads.append(ad)
        
        # Now extract the detailed ad content from the broader JSON context
        # Look for body text, snapshot data, and media URLs
        
        # Find snapshot data blocks that contain actual ad content
        # Pattern: "body":{"text":"..."} near the ad_archive_id
        for ad in ads:
            ad_id = ad["ad_archive_id"]
            
            # Find the broader context around this ad_archive_id
            id_pos = html.find(f'"ad_archive_id":"{ad_id}"')
            if id_pos == -1:
                continue
            
            # Get a large context window around this ad
            # FB's JSON nests video URLs far from the ad_archive_id anchor — need 20k chars
            start = max(0, id_pos - 1000)
            end = min(len(html), id_pos + 20000)
            context = html[start:end]
            
            # Extract body text
            body_match = re.search(r'"body":\{"text":"((?:[^"\\]|\\.)*)"\}', context)
            if body_match:
                body_text = body_match.group(1)
                # Unescape JSON string
                body_text = body_text.replace('\\n', '\n').replace('\\"', '"').replace('\\/', '/')
                ad["ad_body"] = body_text
            
            # Extract videos — try multiple patterns (FB changes key names often)
            video_url_raw = None
            video_patterns = [
                r'"video_hd_url":"((?:[^"\\]|\\.)*)"',
                r'"video_sd_url":"((?:[^"\\]|\\.)*)"',
                r'"playable_url_quality_hd":"((?:[^"\\]|\\.)*)"',
                r'"playable_url":"((?:[^"\\]|\\.)*)"',
                r'"browser_native_hd_url":"((?:[^"\\]|\\.)*)"',
                r'"video_url":"((?:[^"\\]|\\.)*)"',
            ]
            for vp in video_patterns:
                video_matches = re.findall(vp, context)
                video_matches = [v for v in video_matches if v.startswith('http') or v.startswith('\\/')]
                if video_matches:
                    ad["videos"] = [{"hd_url": url.replace('\\/', '/').replace('\\u0025', '%')} for url in video_matches[:3]]
                    ad["display_format"] = "VIDEO"
                    break
            
            # Extract images — broader patterns
            image_patterns = [
                r'"original_image_url":"((?:[^"\\]|\\.)*)"',
                r'"resized_image_url":"((?:[^"\\]|\\.)*)"',
                r'"image_url":"((?:[^"\\]|\\.)*)"',
                r'"url":"(https://[^"]*(?:scontent|fbcdn)[^"]*\.(?:jpg|jpeg|png|webp)[^"]*?)"',
            ]
            if "display_format" not in ad:
                for ip in image_patterns:
                    image_matches = re.findall(ip, context)
                    image_matches = [u for u in image_matches if 'scontent' in u or 'fbcdn' in u]
                    if image_matches:
                        ad["images"] = [{"url": url.replace('\\/', '/').replace('\\u0025', '%')} for url in image_matches[:3]]
                        ad["display_format"] = "IMAGE"
                        break
            
            # Extract CTA link
            cta_match = re.search(r'"cta_text":"([^"]*)"', context)
            if cta_match:
                ad["cta_text"] = cta_match.group(1)
            
            link_match = re.search(r'"link_url":"((?:[^"\\]|\\.)*)"', context)
            if link_match:
                ad["cta_destination"] = link_match.group(1).replace('\\/', '/')
            
            # Extract title/headline
            title_match = re.search(r'"title":"((?:[^"\\]|\\.)*)"', context)
            if title_match:
                ad["ad_title"] = title_match.group(1).replace('\\n', '\n')
            
            # If no format determined yet
            if "display_format" not in ad:
                ad["display_format"] = "UNKNOWN"
        
        return ads
    
    def _scrape_ads_sync(
        self,
        page_id: str,
        brand_name: str,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Synchronous Playwright ad scraping — runs in executor thread.
        """
        ads = []
        
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox']
                )
                
                context = browser.new_context(
                    viewport={'width': 1280, 'height': 900},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                
                self._load_cookies_sync(context)
                
                page = context.new_page()
                
                # Navigate directly to the page's Ad Library
                ad_lib_url = (
                    f"https://www.facebook.com/ads/library/"
                    f"?active_status=active&ad_type=all&country=ALL"
                    f"&is_targeted_country=false&media_type=all"
                    f"&search_type=page&view_all_page_id={page_id}"
                )
                print(f"       [PlaywrightAds] Opening Ad Library for page_id={page_id}...")
                
                # CAPTURE NETWORK RESPONSES to get video/image CDN URLs from GraphQL
                # FB AdLibrary loads media via XHR JSON, not embedded in HTML
                captured_payloads = []
                
                def handle_response(response):
                    try:
                        url = response.url
                        if "facebook.com/api/graphql" in url or "facebook.com/ads/library" in url:
                            body = response.body()
                            if body and len(body) > 100:
                                captured_payloads.append(body.decode("utf-8", errors="replace"))
                    except Exception:
                        pass
                
                page.on("response", handle_response)
                
                page.goto(ad_lib_url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(5)  # Wait for initial render
                
                # Scroll to load more ads
                max_scrolls = min(limit // 3, 40)
                print(f"       [PlaywrightAds] Scrolling to load ads (max {max_scrolls} scrolls)...")
                
                last_count = 0
                stale_scrolls = 0
                for i in range(max_scrolls):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(2)
                    
                    # Quick check for ad_archive_id count
                    current_html = page.content()
                    current_count = current_html.count('"ad_archive_id"')
                    
                    if current_count >= limit * 2:  # We have enough
                        print(f"       [PlaywrightAds] Loaded {current_count} ad refs, sufficient")
                        break
                    
                    if current_count == last_count:
                        stale_scrolls += 1
                        if stale_scrolls >= 3:
                            print(f"       [PlaywrightAds] No more ads loading ({current_count} refs)")
                            break
                    else:
                        stale_scrolls = 0
                    
                    last_count = current_count
                
                # Get final HTML and extract
                html = page.content()
                print(f"       [PlaywrightAds] Page HTML: {len(html)} chars, {html.count('ad_archive_id')} ad refs")
                
                # Check for login/block
                if 'login' in html[:2000].lower():
                    print("       [PlaywrightAds] WARNING: Facebook login page detected -- cookies may be expired")
                
                # Extract ads from embedded JSON
                ads = self._extract_ads_from_html(html, page_id)
                
                # Process captured XHR payloads to extract video/image URLs
                # FB loads these via GraphQL - they won't appear in static HTML
                if captured_payloads:
                    print(f"       [PlaywrightAds] Processing {len(captured_payloads)} XHR payloads for media URLs...")
                    
                    # Build map: ad_archive_id → {videos: [...], images: [...]}
                    media_map = {}  # ad_id → {"videos": [], "images": []}
                    
                    all_payload_text = "\n".join(captured_payloads)
                    
                    # Find all video URLs with their nearby ad_archive_id context
                    video_url_patterns = [
                        r'"video_hd_url":"(https://[^"]+)"',
                        r'"video_sd_url":"(https://[^"]+)"',
                        r'"playable_url_quality_hd":"(https://[^"]+)"',
                        r'"playable_url":"(https://[^"]+)"',
                        r'"browser_native_hd_url":"(https://[^"]+)"',
                    ]
                    
                    for payload in captured_payloads:
                        # Find ad_archive_id in this payload
                        ad_ids_in_payload = re.findall(r'"ad_archive_id":"(\d+)"', payload)
                        
                        for vp in video_url_patterns:
                            video_urls = re.findall(vp, payload)
                            if video_urls and ad_ids_in_payload:
                                for ad_id in ad_ids_in_payload:
                                    if ad_id not in media_map:
                                        media_map[ad_id] = {"videos": [], "images": []}
                                    media_map[ad_id]["videos"].extend(video_urls[:2])
                        
                        # Find image URLs (scontent CDN)
                        img_patterns = [
                            r'"original_image_url":"(https://[^"]+)"',
                            r'"resized_image_url":"(https://[^"]+)"',
                            r'"(https://scontent[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
                        ]
                        for ip in img_patterns:
                            img_urls = re.findall(ip, payload)
                            img_urls = [u for u in img_urls if "scontent" in u or "fbcdn" in u]
                            if img_urls and ad_ids_in_payload:
                                for ad_id in ad_ids_in_payload:
                                    if ad_id not in media_map:
                                        media_map[ad_id] = {"videos": [], "images": []}
                                    media_map[ad_id]["images"].extend(img_urls[:2])
                    
                    # Merge into extracted ads
                    for ad in ads:
                        ad_id = ad.get("ad_archive_id", "")
                        if ad_id in media_map:
                            mdata = media_map[ad_id]
                            if mdata["videos"] and not ad.get("videos"):
                                ad["videos"] = [{"hd_url": u} for u in mdata["videos"][:2]]
                                ad["display_format"] = "VIDEO"
                            elif mdata["images"] and not ad.get("images"):
                                ad["images"] = [{"url": u} for u in mdata["images"][:2]]
                                if ad.get("display_format", "UNKNOWN") == "UNKNOWN":
                                    ad["display_format"] = "IMAGE"
                    
                    media_count = sum(1 for a in ads if a.get("videos") or a.get("images"))
                    print(f"       [PlaywrightAds] XHR merge: {media_count}/{len(ads)} ads now have media URLs")
                
                # Filter to only this page's ads (should be all, but just in case)
                ads = [a for a in ads if str(a.get("page_id", "")) == str(page_id)]
                
                # Deduplicate by ad_archive_id
                seen = set()
                unique_ads = []
                for ad in ads:
                    if ad["ad_archive_id"] not in seen:
                        seen.add(ad["ad_archive_id"])
                        unique_ads.append(ad)
                ads = unique_ads[:limit]
                
                # Stats
                videos = sum(1 for a in ads if a.get("display_format") == "VIDEO")
                images = sum(1 for a in ads if a.get("display_format") == "IMAGE")
                with_body = sum(1 for a in ads if a.get("ad_body"))
                
                print(f"       [PlaywrightAds] Extracted {len(ads)} ads ({videos} videos, {images} images, {with_body} with body text)")
                
                browser.close()
                
        except Exception as e:
            print(f"       [PlaywrightAds] Error: {str(e)[:200]}")
        
        return ads
    
    async def scrape_page_ads(
        self,
        page_id: str,
        brand_name: str,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Async wrapper for scraping ads from a specific page.
        
        Args:
            page_id: Facebook page ID (numeric)
            brand_name: Brand name for context
            limit: Maximum ads to scrape
            
        Returns:
            List of ad data dicts compatible with the existing ad analyzer pipeline
        """
        print(f"    [PlaywrightAds] Scraping ads for {brand_name} (page_id={page_id}, limit={limit})...")
        
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            ads = await loop.run_in_executor(
                executor,
                self._scrape_ads_sync,
                page_id,
                brand_name,
                limit
            )
        
        print(f"    [PlaywrightAds] Total: {len(ads)} ads scraped for {brand_name}")
        return ads


# Singleton
_playwright_ad_scraper = None

def get_playwright_ad_scraper() -> PlaywrightAdScraper:
    global _playwright_ad_scraper
    if _playwright_ad_scraper is None:
        _playwright_ad_scraper = PlaywrightAdScraper()
    return _playwright_ad_scraper
