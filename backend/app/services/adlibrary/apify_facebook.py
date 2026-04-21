"""
Apify integration for Facebook Ad Library scraping.
Uses curious_coder~facebook-ads-library-scraper actor.
Cost: ~$0.75 per 1000 results.

Input: urls (array of {url: string}), limitPerSource (int)
Output: ads with snapshot structure (page_name, page_id, snapshot.videos, snapshot.images, etc.)
"""

import httpx
import asyncio
from typing import Dict, Any, Optional, List
from ...config import settings


class ApifyFacebookAdsService:
    """Service to scrape Facebook Ad Library using Apify (curious_coder actor)."""

    ACTOR_ID = "curious_coder~facebook-ads-library-scraper"
    BASE_URL = "https://api.apify.com/v2"

    def __init__(self):
        self.api_token = settings.APIFY_API_TOKEN
        self.timeout = 300.0

    # ------------------------------------------------------------------
    # Core: run any Ad Library / FB page URL through the actor
    # ------------------------------------------------------------------

    async def _run_actor(self, url: str, limit: int) -> List[Dict[str, Any]]:
        """Run the curious_coder actor with a single URL and return raw ads.

        Payload is aligned with the actor's official input schema:
          - urls: [{url}]           — page or Ad Library URLs
          - limitPerSource: int     — cap per input URL
          - count: int              — total records target (the actor can
                                      deliver slightly more than this)
          - scrapeAdDetails: true   — pull per-ad EU Reach / transparency info
          - scrapePageAds.*         — when the URL is a page, control the
                                      time window / active status / sort / country
          - proxy: residential      — required by the actor's docs; without
                                      a proxy Meta's rate limiter returns
                                      error records for many pages (this was
                                      the root cause of the Il Makiage failure).
        """
        if not self.api_token:
            print("    [!] Apify token not configured")
            return []

        actor_input = {
            "urls": [{"url": url}],
            "limitPerSource": limit,
            "count": limit,
            "scrapeAdDetails": True,
            "scrapePageAds.activeStatus": "all",
            "scrapePageAds.countryCode": "ALL",
            "scrapePageAds.sortBy": "most_recent",
            "proxy": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"],
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                run_url = f"{self.BASE_URL}/acts/{self.ACTOR_ID}/runs?token={self.api_token}"
                response = await client.post(run_url, json=actor_input)
                response.raise_for_status()

                run_id = response.json().get("data", {}).get("id")
                if not run_id:
                    print("    [!] Failed to start Apify actor")
                    return []

                print(f"    [Apify] Actor started (run {run_id})")

                # Poll for completion
                status_url = f"{self.BASE_URL}/actor-runs/{run_id}?token={self.api_token}"
                wait = 0
                while wait < 300:
                    await asyncio.sleep(5)
                    wait += 5
                    sr = await client.get(status_url)
                    sd = sr.json().get("data", {})
                    status = sd.get("status")
                    if wait % 15 == 0:
                        print(f"    [Apify] {status} ({wait}s)")
                    if status == "SUCCEEDED":
                        cost = sd.get("usageTotalUsd", 0)
                        print(f"    [Apify] Done in {wait}s (${cost:.4f})")
                        break
                    if status in ("FAILED", "ABORTED", "TIMED-OUT"):
                        print(f"    [!] Apify actor {status}")
                        return []

                if wait >= 300:
                    print("    [!] Apify actor timed out (5 min)")
                    return []

                # Fetch results
                dataset_id = sd.get("defaultDatasetId")
                if not dataset_id:
                    print("    [!] No dataset ID in actor run response")
                    return []
                ds_url = f"{self.BASE_URL}/datasets/{dataset_id}/items?token={self.api_token}"
                dr = await client.get(ds_url)
                dr.raise_for_status()
                raw_text = dr.text.strip()
                if not raw_text:
                    print(f"    [!] Empty dataset response (dataset_id={dataset_id})")
                    return []
                ads = dr.json()
                print(f"    [Apify] Retrieved {len(ads)} records")

                # Explicit error-record detection.
                # The actor returns records shaped like
                #   {"error": "...", "errorCode": "...", "url": "..."}
                # when it can't reach a given page (e.g. proxy / rate-limit /
                # region restriction). Filter them out and log so we know WHY.
                if isinstance(ads, list):
                    errors = [a for a in ads if isinstance(a, dict) and (a.get("error") or a.get("errorCode"))]
                    if errors:
                        first_err = errors[0]
                        print(
                            f"    [Apify][!] {len(errors)} error record(s) filtered. "
                            f"First: code={first_err.get('errorCode')!r}, "
                            f"msg={str(first_err.get('error'))[:120]!r}"
                        )
                        ads = [
                            a for a in ads
                            if not (isinstance(a, dict) and (a.get("error") or a.get("errorCode")))
                        ]
                        print(f"    [Apify] {len(ads)} records remaining after error filter")
                return ads

        except Exception as e:
            print(f"    [!] Apify error: {e}")
            return []

    # ------------------------------------------------------------------
    # Public API: high-level methods used by the pipeline
    # ------------------------------------------------------------------

    async def scrape_by_facebook_url(
        self, facebook_page_url: str, limit: int = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape all ads from a Facebook page URL (e.g. facebook.com/Huel).
        Most reliable method — returns only that page's ads + gives us page_id.
        """
        if limit is None:
            limit = settings.AD_LIBRARY_MAX_ADS
        print(f"    [Apify] Strategy: Facebook page URL → {facebook_page_url}")
        return await self._run_actor(facebook_page_url, limit)

    async def scrape_by_page_id(
        self, page_id: str, limit: int = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape all ads from a specific page using view_all_page_id.
        100% precision — returns only that advertiser's ads.
        """
        if limit is None:
            limit = settings.AD_LIBRARY_MAX_ADS
        url = (
            f"https://www.facebook.com/ads/library/"
            f"?active_status=active&ad_type=all&country=ALL"
            f"&media_type=all&search_type=page&view_all_page_id={page_id}"
        )
        print(f"    [Apify] Strategy: view_all_page_id={page_id}")
        return await self._run_actor(url, limit)

    async def scrape_by_page_name(
        self, brand_name: str, limit: int = None
    ) -> List[Dict[str, Any]]:
        """
        Search Ad Library by page name (search_type=page).
        Good fallback — returns ads from pages matching the name.
        May include results from other pages with similar names.
        """
        if limit is None:
            limit = settings.AD_LIBRARY_MAX_ADS
        from urllib.parse import quote
        url = (
            f"https://www.facebook.com/ads/library/"
            f"?active_status=active&ad_type=all&country=ALL"
            f"&q={quote(brand_name)}&search_type=page&media_type=all"
        )
        print(f"    [Apify] Strategy: page name search '{brand_name}'")
        return await self._run_actor(url, limit)

    # ------------------------------------------------------------------
    # Helpers: extract media URLs from curious_coder snapshot structure
    # ------------------------------------------------------------------

    @staticmethod
    def extract_video_url(ad_data: Dict[str, Any]) -> Optional[str]:
        """Extract the best video URL from ad data (curious_coder snapshot format)."""
        snapshot = ad_data.get("snapshot") or {}
        for key in ("videos", "extra_videos", "extraVideos"):
            videos = snapshot.get(key, [])
            if videos:
                v = videos[0]
                url = (v.get("video_hd_url") or v.get("videoHdUrl") or
                       v.get("video_sd_url") or v.get("videoSdUrl"))
                if url:
                    return url
        return None

    @staticmethod
    def extract_image_url(ad_data: Dict[str, Any]) -> Optional[str]:
        """Extract the best image URL from ad data."""
        snapshot = ad_data.get("snapshot") or {}
        images = snapshot.get("images", [])
        if images:
            img = images[0]
            if isinstance(img, dict):
                return (img.get("original_image_url") or img.get("original_url") or
                        img.get("originalImageUrl") or
                        img.get("resized_image_url") or img.get("resized_url") or
                        img.get("resizedImageUrl") or
                        img.get("url"))
            elif isinstance(img, str):
                return img
        return None

    @staticmethod
    def extract_thumbnail_url(ad_data: Dict[str, Any]) -> Optional[str]:
        """Extract video thumbnail URL."""
        snapshot = ad_data.get("snapshot") or {}
        videos = snapshot.get("videos", [])
        if videos:
            return (videos[0].get("video_preview_image_url") or
                    videos[0].get("videoPreviewImageUrl"))
        return None

    @staticmethod
    def get_page_id_from_results(ads: List[Dict[str, Any]]) -> Optional[str]:
        """Extract the most common page_id from a set of results.
        Useful when scraping by FB URL — gives us the page_id for free."""
        from collections import Counter
        ids = Counter(str(a.get("page_id")) for a in ads if a.get("page_id"))
        if ids:
            top_id, _ = ids.most_common(1)[0]
            return top_id
        return None

    @staticmethod
    def filter_by_page_name(ads: List[Dict[str, Any]], brand_name: str) -> List[Dict[str, Any]]:
        """Filter ads to keep only those from pages matching the brand name."""
        brand_lower = brand_name.lower().strip()
        filtered = [
            a for a in ads
            if brand_lower in (a.get("page_name") or "").lower()
        ]
        if filtered:
            print(f"    [Apify] Name filter: kept {len(filtered)}/{len(ads)} ads matching '{brand_name}'")
            return filtered
        print(f"    [Apify] Name filter: no match for '{brand_name}' — keeping all {len(ads)}")
        return ads


# Singleton
_apify_fb_service: Optional[ApifyFacebookAdsService] = None

def get_apify_facebook_service() -> ApifyFacebookAdsService:
    global _apify_fb_service
    if _apify_fb_service is None:
        _apify_fb_service = ApifyFacebookAdsService()
    return _apify_fb_service
