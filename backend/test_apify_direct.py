# -*- coding: utf-8 -*-
"""
Diagnostic tool to probe the Apify Ad Library actor directly.

Runs each of the URL formats the pipeline uses and reports how many ads
come back, so we can tell whether the actor genuinely has no data for a
brand vs. whether our pipeline is misusing it.

Usage (from backend/ with .env loaded):
    python test_apify_direct.py "Il Makiage" ilmakiage
"""

import asyncio
import os
import sys
from urllib.parse import quote
import httpx

# Load .env
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    for line in open(env_path):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

APIFY_TOKEN = os.environ.get("APIFY_API_TOKEN", "")
ACTOR_ID = "curious_coder~facebook-ads-library-scraper"
BASE_URL = "https://api.apify.com/v2"


async def run_actor(url: str, limit: int = 20) -> list:
    """Run the Apify actor with a given URL and return raw ads."""
    if not APIFY_TOKEN:
        print("  [!] APIFY_API_TOKEN not set")
        return []

    actor_input = {"urls": [{"url": url}], "limitPerSource": limit}

    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(
            f"{BASE_URL}/acts/{ACTOR_ID}/runs?token={APIFY_TOKEN}",
            json=actor_input,
        )
        resp.raise_for_status()
        run_id = resp.json().get("data", {}).get("id")
        print(f"  Actor run: {run_id}")

        # Poll for completion
        status_url = f"{BASE_URL}/actor-runs/{run_id}?token={APIFY_TOKEN}"
        for waited in range(0, 300, 5):
            await asyncio.sleep(5)
            sr = await client.get(status_url)
            sd = sr.json().get("data", {})
            status = sd.get("status")
            if waited % 15 == 0:
                print(f"    {waited}s: {status}")
            if status == "SUCCEEDED":
                dataset_id = sd.get("defaultDatasetId")
                dr = await client.get(
                    f"{BASE_URL}/datasets/{dataset_id}/items?token={APIFY_TOKEN}"
                )
                dr.raise_for_status()
                ads = dr.json() if dr.text.strip() else []
                return ads
            if status in ("FAILED", "ABORTED", "TIMED-OUT"):
                print(f"    Actor {status}")
                return []
    return []


def analyze_ads(ads: list, label: str) -> None:
    print(f"\n  === {label} ===")
    print(f"  Total raw records: {len(ads)}")
    if not ads:
        return
    with_archive_id = [a for a in ads if a.get("ad_archive_id") or a.get("adArchiveID")]
    print(f"  Records with ad_archive_id: {len(with_archive_id)}")
    print(f"  Records WITHOUT ad_archive_id (garbage): {len(ads) - len(with_archive_id)}")
    for ad in ads[:3]:
        keys = sorted(ad.keys())[:10]
        print(f"    sample ad keys: {keys}")
        page_name = ad.get("page_name") or ad.get("snapshot", {}).get("pageName")
        print(f"    page_name={page_name}")


async def main(brand_name: str, handle: str):
    print(f"\n{'='*60}")
    print(f"  Probing Apify for: {brand_name!r} (handle={handle!r})")
    print(f"{'='*60}")

    test_cases = [
        (
            "A. Direct FB page URL (what Strategy 1 uses)",
            f"https://www.facebook.com/{handle}",
        ),
        (
            "B. Ad Library search by brand name (what Strategy 4 uses)",
            f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&q={quote(brand_name)}&search_type=page&media_type=all",
        ),
    ]

    for label, url in test_cases:
        print(f"\n[{label}]")
        print(f"  URL: {url}")
        try:
            ads = await run_actor(url, limit=20)
            analyze_ads(ads, label)
        except Exception as e:
            print(f"  [!] Error: {type(e).__name__}: {e}")


if __name__ == "__main__":
    brand = sys.argv[1] if len(sys.argv) > 1 else "Il Makiage"
    hdl = sys.argv[2] if len(sys.argv) > 2 else "ilmakiage"
    asyncio.run(main(brand, hdl))
