"""
Playwright-based Ad Library search to find page_id by clicking on advertisers dropdown.
Uses browser automation where Firecrawl can't interact with JS elements.

NOTE: Uses sync_api with run_in_executor to avoid Windows asyncio subprocess issues.
"""

import asyncio
import re
import time
import concurrent.futures
from typing import Optional, List
from pathlib import Path
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page


class AdLibraryPlaywrightSearch:
    """Use Playwright to find page_id by searching and clicking advertisers."""
    
    def __init__(self):
        self.cookies_path = Path(__file__).parent.parent.parent.parent / "facebook_cookies.txt"
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    
    @staticmethod
    def _pick_best_candidate(candidates: list, search_term: str) -> dict:
        """
        When multiple dropdown items match the search, pick the best one.
        Scoring: exact @handle match > higher followers > has both FB+IG.
        """
        search_lower = search_term.lower()

        def _score(c):
            s = 0
            text = (c.get('text') or '').lower()
            # Exact @handle match is strongest signal
            if f'@{search_lower}' in text:
                s += 100_000
            # Higher follower count is a strong proxy for the "real" page
            s += int(c.get('followers') or 0)
            # Having both platforms is a mild positive signal
            if c.get('hasFB') and c.get('hasIG'):
                s += 50
            return s

        return max(candidates, key=_score)

    def _load_cookies_sync(self, context: BrowserContext) -> bool:
        """Load Facebook cookies from Netscape format file (sync version)."""
        if not self.cookies_path.exists():
            print(f"       [Playwright] No cookies file found at {self.cookies_path}")
            return False
        
        try:
            cookies = []
            with open(self.cookies_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split('\t')
                    if len(parts) >= 7:
                        domain = parts[0]
                        cookie = {
                            "name": parts[5],
                            "value": parts[6],
                            "domain": domain if domain.startswith('.') else f".{domain}",
                            "path": parts[2],
                            "secure": parts[3].upper() == "TRUE",
                            "httpOnly": False
                        }
                        if "facebook.com" in domain:
                            cookies.append(cookie)
            
            if cookies:
                context.add_cookies(cookies)
                print(f"       [Playwright] Loaded {len(cookies)} Facebook cookies")
                return True
            return False
        except Exception as e:
            print(f"       [Playwright] Error loading cookies: {e}")
            return False

    def _find_page_id_sync(
        self,
        usernames_to_try: List[str]
    ) -> Optional[str]:
        """
        Synchronous version of page_id search - runs in executor thread.
        Tries multiple usernames sequentially until a match is found.
        """
        # Deduplicate while preserving order, remove empty strings
        seen = set()
        clean_usernames = []
        for u in usernames_to_try:
            if u and u.lower() not in seen:
                seen.add(u.lower())
                clean_usernames.append(u)
        
        usernames_to_try = clean_usernames
        
        if not usernames_to_try:
            print("       [Playwright] No username provided for search")
            return None
        
        print(f"       [Playwright] Will try usernames in order: {usernames_to_try}")
        
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox']
                )
                
                context = browser.new_context(
                    viewport={'width': 1280, 'height': 720},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                
                self._load_cookies_sync(context)
                
                page = context.new_page()
                
                ad_library_url = "https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&media_type=all"
                print(f"       [Playwright] Opening Ad Library...")
                
                page.goto(ad_library_url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(3)
                
                # STEP 1: Click category dropdown and select "All ads"
                print(f"       [Playwright] Selecting 'All ads' category...")
                
                try:
                    category_result = page.evaluate('''
                        () => {
                            const elements = Array.from(document.querySelectorAll('div[role="combobox"]'));
                            const categoryDiv = elements.find(el => 
                                el.textContent.includes('Ad category') || 
                                el.textContent.includes('Categoria de anuncio') ||
                                el.textContent.includes('Categoría de anuncio')
                            );
                            if (categoryDiv) {
                                categoryDiv.click();
                                return "clicked";
                            }
                            return "not_found";
                        }
                    ''')
                    
                    if category_result == "clicked":
                        time.sleep(1)
                        page.evaluate('''
                            () => {
                                const options = Array.from(document.querySelectorAll('span'));
                                const allAds = options.find(el => 
                                    el.textContent.includes('All ads') || 
                                    el.textContent.includes('Todos los anuncios')
                                );
                                if (allAds) allAds.click();
                            }
                        ''')
                        time.sleep(1)
                except Exception as e:
                    print(f"       [Playwright] Category selection skipped: {str(e)[:50]}")
                
                # STEP 2: Find and focus the search input
                print(f"       [Playwright] Finding search input...")
                
                search_input = None
                selectors = [
                    'input[placeholder*="Search"]',
                    'input[placeholder*="Buscar"]',
                    'input[placeholder*="keyword"]',
                    'input[placeholder*="palabra clave"]',
                    'input[placeholder*="advertiser"]',
                    'input[placeholder*="anunciante"]',
                    'input[aria-label*="Search"]',
                    'input[type="search"]',
                ]
                
                for selector in selectors:
                    try:
                        search_input = page.wait_for_selector(selector, timeout=2000)
                        if search_input:
                            print(f"       [Playwright] Found search input with: {selector}")
                            break
                    except:
                        continue
                
                if not search_input:
                    try:
                        page.evaluate('''
                            () => {
                                const input = document.querySelector('input[placeholder*="Buscar"]') || 
                                              document.querySelector('input[placeholder*="Search"]');
                                if (input) {
                                    input.click();
                                    input.focus();
                                }
                            }
                        ''')
                        time.sleep(0.5)
                        search_input = page.query_selector('input:focus')
                    except:
                        pass
                
                if not search_input:
                    print("       [Playwright] FAILED: Could not find search input")
                    browser.close()
                    return None
                
                # STEP 3+4: Try each username sequentially
                for attempt_idx, username_to_search in enumerate(usernames_to_try):
                    print(f"       [Playwright] Attempt {attempt_idx + 1}/{len(usernames_to_try)}: Searching '{username_to_search}'...")
                    
                    search_input.click()
                    time.sleep(0.3)
                    search_input.fill("")
                    time.sleep(0.3)
                    search_input.fill(username_to_search)
                    print(f"       [Playwright] Typed: {username_to_search}")
                    
                    time.sleep(2.5)
                    
                    print(f"       [Playwright] Looking for advertiser suggestions...")
                    
                    page_id = None
                    
                    try:
                        result = page.evaluate('''
                            (searchUsername) => {
                                const items = document.querySelectorAll('li[role="option"][id^="pageID:"]');
                                if (items.length === 0) return [];
                                const results = [];
                                for (const item of items) {
                                    const pageId = item.id.replace('pageID:', '');
                                    const rawText = item.textContent || '';
                                    const text = rawText.toLowerCase();
                                    const hasMatchingHandle = text.includes('@' + searchUsername.toLowerCase()) ||
                                                              text.includes(searchUsername.toLowerCase());
                                    // Extract follower count: patterns like "5,000 followers", "5K followers", "426 seguidores"
                                    let followers = 0;
                                    const fMatch = rawText.match(/([\d,]+(?:\.\d+)?)\s*[Kk]?\s*(?:followers|seguidores|likes|me gusta)/i);
                                    if (fMatch) {
                                        let num = parseFloat(fMatch[1].replace(/,/g, ''));
                                        if (fMatch[0].match(/[Kk]/)) num *= 1000;
                                        followers = num;
                                    }
                                    const hasFB = text.includes('facebook');
                                    const hasIG = text.includes('instagram');
                                    results.push({
                                        pageId, text: rawText.substring(0, 150), matches: hasMatchingHandle,
                                        followers, hasFB, hasIG
                                    });
                                }
                                return results;
                            }
                        ''', username_to_search)
                        
                        if result and len(result) > 0:
                            print(f"       [Playwright] Found {len(result)} dropdown items")
                            for r in result:
                                print(f"         -> pageID={r['pageId']} followers={r.get('followers',0)} match={r['matches']} text='{r['text'][:60]}'")

                            matching = [r for r in result if r.get('matches')]
                            
                            if len(matching) == 1:
                                page_id = matching[0]['pageId']
                                print(f"       [Playwright] Single match: {matching[0]['text'][:50]}")
                            elif len(matching) > 1:
                                best = self._pick_best_candidate(matching, username_to_search)
                                page_id = best['pageId']
                                print(f"       [Playwright] Best of {len(matching)} matches (followers={best.get('followers',0)}): {best['text'][:50]}")
                            elif attempt_idx == len(usernames_to_try) - 1:
                                # Last resort on final attempt
                                first_text = result[0].get('text', '').lower()
                                search_lower = username_to_search.lower()
                                word_match = re.search(r'(^|\s)' + re.escape(search_lower) + r'(\s|$|@)', first_text)
                                if word_match:
                                    page_id = result[0].get('pageId')
                                    print(f"       [Playwright] Last-resort word match: {result[0].get('text','')[:50]}")
                                else:
                                    print(f"       [Playwright] No word match in '{result[0].get('text','')[:50]}' for '{search_lower}'")
                        
                    except Exception as e:
                        print(f"       [Playwright] Error extracting from dropdown: {str(e)[:50]}")
                    
                    # Fallback: Find pageID in HTML
                    if not page_id:
                        try:
                            content = page.content()
                            match = re.search(r'pageID:(\d+)', content)
                            if match:
                                page_id = match.group(1)
                                print(f"       [Playwright] Found page_id in content: {page_id}")
                        except:
                            pass
                    
                    if page_id:
                        print(f"       [Playwright] SUCCESS! Found page_id: {page_id} (via '{username_to_search}')")
                        browser.close()
                        return page_id
                    else:
                        print(f"       [Playwright] No match for '{username_to_search}', trying next...")
                
                # All usernames exhausted
                print(f"       [Playwright] Could not find page_id for any of: {usernames_to_try}")
                browser.close()
                return None
                
        except Exception as e:
            print(f"       [Playwright] Error: {str(e)[:100]}")
            return None

    async def find_page_id_by_clicking_advertiser(
        self,
        usernames_to_try: List[str]
    ) -> Optional[str]:
        """
        Search Ad Library and click on the first advertiser matching a username.
        Tries elements in the usernames_to_try list in order.
        
        This is an async wrapper that runs the sync Playwright code in an executor
        to avoid Windows asyncio subprocess issues.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._find_page_id_sync,
            usernames_to_try
        )


# Singleton instance
_playwright_search = None


async def get_playwright_search() -> AdLibraryPlaywrightSearch:
    """Get singleton instance of AdLibraryPlaywrightSearch."""
    global _playwright_search
    if _playwright_search is None:
        _playwright_search = AdLibraryPlaywrightSearch()
    return _playwright_search
