"""
Firecrawl Scraper - Web scraping using Firecrawl API.
Includes rate limiting with semaphore to avoid 429 errors.
"""

import httpx
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from ...config import settings


# Global semaphore to limit concurrent Firecrawl requests
# Firecrawl allows ~3-5 requests per second, we limit to 2 concurrent
_firecrawl_semaphore = asyncio.Semaphore(2)
_request_lock = asyncio.Lock()
_last_request_time = 0
_request_queue = []  # Track pending requests for better scheduling


class FirecrawlScraper:
    """Scraper using Firecrawl API for web content with robust rate limiting."""
    
    # Rate limiting settings - MORE AGGRESSIVE
    MIN_REQUEST_INTERVAL = 1.5  # Minimum seconds between ANY requests (reduced from 2)
    MAX_RETRIES = 5  # Increased from 3
    INITIAL_RETRY_DELAY = 3.0  # Initial delay before exponential backoff
    MAX_RETRY_DELAY = 60.0  # Maximum delay cap for exponential backoff
    
    def __init__(self):
        self.api_key = settings.FIRECRAWL_API_KEY
        self.base_url = settings.FIRECRAWL_BASE_URL
        # Use structured timeout: connect=5s, read=15s, total=20s
        self.timeout = httpx.Timeout(
            timeout=settings.SCRAPE_TIMEOUT,  # Total timeout
            connect=5.0,  # Connection timeout
            read=15.0,  # Read timeout
            write=10.0  # Write timeout
        )
    
    @property
    def has_key(self) -> bool:
        """Check if Firecrawl API key is configured."""
        return bool(self.api_key)
    
    async def _rate_limited_request(
        self, 
        client: httpx.AsyncClient, 
        method: str, 
        url: str, 
        operation_name: str = "request",
        **kwargs
    ) -> Optional[httpx.Response]:
        """
        Make a rate-limited request using global semaphore with exponential backoff.
        
        Args:
            client: HTTP client
            method: HTTP method (GET or POST)
            url: URL to request
            operation_name: Name of operation for logging
            **kwargs: Additional arguments for the request
            
        Returns:
            Response or None if failed after all retries
        """
        global _last_request_time
        
        async with _firecrawl_semaphore:
            # Ensure minimum interval between requests globally
            async with _request_lock:
                import time
                now = time.time()
                elapsed = now - _last_request_time
                if elapsed < self.MIN_REQUEST_INTERVAL:
                    wait_time = self.MIN_REQUEST_INTERVAL - elapsed
                    await asyncio.sleep(wait_time)
                _last_request_time = time.time()
            
            # Try request with exponential backoff
            for attempt in range(self.MAX_RETRIES + 1):
                try:
                    if method == "POST":
                        response = await client.post(url, headers=self._get_headers(), **kwargs)
                    else:
                        response = await client.get(url, headers=self._get_headers(), **kwargs)
                    
                    # Handle rate limiting with exponential backoff
                    if response.status_code in (429, 503):
                        if attempt < self.MAX_RETRIES:
                            # Exponential backoff: 3s, 6s, 12s, 24s, 48s (capped at 60s)
                            delay = min(
                                self.INITIAL_RETRY_DELAY * (2 ** attempt),
                                self.MAX_RETRY_DELAY
                            )
                            # Add jitter to avoid thundering herd
                            import random
                            jitter = random.uniform(0, delay * 0.2)
                            wait_time = delay + jitter
                            print(f"       [Firecrawl {response.status_code}] {operation_name} retry {attempt+1}/{self.MAX_RETRIES} in {wait_time:.1f}s...")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            print(f"       [Firecrawl] {operation_name}: Rate limit exceeded after {self.MAX_RETRIES} retries")
                            return None
                    
                    response.raise_for_status()
                    
                    # Track successful request
                    from ...utils.api_quota_tracker import get_quota_tracker
                    get_quota_tracker().record_request("firecrawl", True)
                    
                    return response
                    
                except httpx.HTTPStatusError as e:
                    status = e.response.status_code
                    
                    # Retryable errors: 429 (rate limit), 403 (temp block), 502/503/504 (server issues)
                    if status in (429, 403, 502, 503, 504) and attempt < self.MAX_RETRIES:
                        # Exponential backoff with multiplier for 403 (abuse detection)
                        multiplier = 2.0 if status == 403 else 1.0
                        delay = min(
                            self.INITIAL_RETRY_DELAY * (2 ** attempt) * multiplier,
                            self.MAX_RETRY_DELAY
                        )
                        import random
                        jitter = random.uniform(0, delay * 0.2)
                        wait_time = delay + jitter
                        print(f"       [Firecrawl {status}] {operation_name} retry {attempt+1}/{self.MAX_RETRIES} in {wait_time:.1f}s...")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    # Non-retryable error or max retries reached
                    from ...utils.api_quota_tracker import get_quota_tracker
                    error_msg = f"HTTP {status}: {str(e)[:100]}"
                    
                    # Check for quota-related errors
                    if status == 402:
                        error_msg = "Insufficient credits (quota exhausted)"
                    elif status == 429:
                        error_msg = f"Rate limit exceeded after {self.MAX_RETRIES} retries"
                    
                    get_quota_tracker().record_request("firecrawl", False, error_msg)
                    
                    if status in (429, 403, 502, 503, 504):
                        print(f"       [Firecrawl] {operation_name}: Failed after {self.MAX_RETRIES} retries (HTTP {status})")
                    else:
                        print(f"       [Firecrawl] {operation_name}: HTTP {status} - {str(e)[:50]}")
                    return None
                    
                except httpx.TimeoutException:
                    if attempt < self.MAX_RETRIES:
                        delay = self.INITIAL_RETRY_DELAY * (attempt + 1)
                        print(f"       [Firecrawl] {operation_name}: Timeout, retry {attempt+1}/{self.MAX_RETRIES} in {delay:.0f}s...")
                        await asyncio.sleep(delay)
                        continue
                    print(f"       [Firecrawl] {operation_name}: Timeout after {self.MAX_RETRIES} retries")
                    return None
                    
                except httpx.ConnectError as e:
                    print(f"       [Firecrawl] {operation_name}: Connection error - {str(e)[:50]}")
                    return None
                    
                except Exception as e:
                    print(f"       [Firecrawl] {operation_name}: {type(e).__name__} - {str(e)[:50]}")
                    return None
            
            return None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get API headers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def scrape_website(self, url: str) -> str:
        """
        Scrape a website and return its content as markdown.
        
        Args:
            url: Website URL to scrape
            
        Returns:
            Website content as markdown string
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await self._rate_limited_request(
                    client, "POST",
                    f"{self.base_url}/scrape",
                    json={
                        "url": url,
                        "formats": ["markdown"],
                        "onlyMainContent": True
                    }
                )
                
                if response is None:
                    return ""
                    
                data = response.json()
                
                if data.get("success"):
                    return data.get("data", {}).get("markdown", "")
                return ""
                
            except Exception as e:
                print(f"       [Firecrawl] Scrape error: {str(e)[:50]}")
                return ""
    
    async def search_brand(self, brand_name: str) -> Dict[str, Any]:
        """
        Search for a brand and find its website.
        
        Args:
            brand_name: Name of the brand to search
            
        Returns:
            Dict with website_url, description, and search results
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await self._rate_limited_request(
                    client, "POST",
                    f"{self.base_url}/search",
                    json={
                        "query": f"{brand_name} official website",
                        "limit": 5
                    }
                )
                
                if response is None:
                    return {"website_url": None, "description": "", "results": []}
                
                data = response.json()
                results = data.get("data", [])
                
                # Find the most likely official website
                website_url = None
                description = ""
                
                if results:
                    first = results[0]
                    website_url = first.get("url")
                    description = first.get("description", "")
                
                return {
                    "website_url": website_url,
                    "description": description,
                    "results": results,
                    "content": "\n\n".join([
                        f"**{r.get('title', '')}**\n{r.get('description', '')}"
                        for r in results
                    ])
                }
                
            except Exception as e:
                print(f"       [Firecrawl] Search error: {str(e)[:50]}")
                return {"website_url": None, "description": "", "results": []}
    
    async def search_reddit(self, query: str) -> List[Dict[str, Any]]:
        """
        Search Reddit for posts matching a query.
        
        Args:
            query: Search query
            
        Returns:
            List of post data dicts
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await self._rate_limited_request(
                    client, "POST",
                    f"{self.base_url}/search",
                    json={
                        "query": f"{query} site:reddit.com",
                        "limit": settings.MAX_POSTS_PER_SOURCE  # Use full config value
                    }
                )
                
                if response is None:
                    print(f"       [Firecrawl Reddit] Rate limited or failed for: {query[:30]}...")
                    return []
                
                data = response.json()
                
                results = []
                for item in data.get("data", []):
                    results.append({
                        "source_url": item.get("url"),
                        "title": item.get("title"),
                        "content": item.get("description") or item.get("markdown", ""),
                        "raw_data": item
                    })
                
                print(f"       [Firecrawl Reddit] Found {len(results)} results for: {query[:30]}...")
                return results
                
            except Exception as e:
                print(f"       [Firecrawl Reddit] Error for '{query[:30]}...': {str(e)[:50]}")
                return []
    
    async def scrape_subreddit(self, subreddit: str) -> List[Dict[str, Any]]:
        """
        Scrape top posts from a subreddit.
        
        Args:
            subreddit: Subreddit name (e.g., 'r/hairloss' or just 'hairloss')
            
        Returns:
            List of post data dicts
        """
        # Normalize subreddit name
        if subreddit.startswith("r/"):
            subreddit = subreddit[2:]
        
        url = f"https://www.reddit.com/r/{subreddit}/top/?t=month"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                # Scrape the subreddit page with rate limiting
                response = await self._rate_limited_request(
                    client, "POST",
                    f"{self.base_url}/scrape",
                    operation_name=f"subreddit r/{subreddit}",
                    json={
                        "url": url,
                        "formats": ["markdown", "links"]
                    }
                )
                
                if response is None:
                    return []
                    
                data = response.json()
                
                if not data.get("success"):
                    return []
                
                content = data.get("data", {}).get("markdown", "")
                links = data.get("data", {}).get("links", [])
                
                # Extract post links and scrape them
                results = []
                post_links = [
                    l for l in links 
                    if "/comments/" in l and "reddit.com" in l
                ][:10]  # Limit to 10 posts
                
                for link in post_links:
                    post_data = await self._scrape_reddit_post(link)
                    if post_data:
                        results.append(post_data)
                
                # If no individual posts, return the main content
                if not results and content:
                    results.append({
                        "source_url": url,
                        "title": f"r/{subreddit} - Top Posts",
                        "content": content,
                        "raw_data": {"subreddit": subreddit}
                    })
                
                return results
                
            except Exception as e:
                print(f"Subreddit scrape error: {e}")
                return []
    
    async def _scrape_reddit_post(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape a single Reddit post."""
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/scrape",
                    headers=self._get_headers(),
                    json={
                        "url": url,
                        "formats": ["markdown"],
                        "onlyMainContent": True
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                if data.get("success"):
                    content = data.get("data", {}).get("markdown", "")
                    metadata = data.get("data", {}).get("metadata", {})
                    
                    return {
                        "source_url": url,
                        "title": metadata.get("title", ""),
                        "content": content,
                        "author": metadata.get("author"),
                        "raw_data": data.get("data", {})
                    }
                return None
                
            except Exception as e:
                print(f"Reddit post scrape error: {e}")
                return None
    
    async def search_forums(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for forum discussions.
        
        Args:
            query: Search query
            
        Returns:
            List of forum post data dicts
        """
        # Search for forum content
        search_query = f"{query} (forum OR discussion OR community)"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/search",
                    headers=self._get_headers(),
                    json={
                        "query": search_query,
                        "limit": settings.MAX_POSTS_PER_SOURCE
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                results = []
                for item in data.get("data", []):
                    # Filter out non-forum results
                    url = item.get("url", "")
                    if any(x in url.lower() for x in ["forum", "community", "discuss", "board"]):
                        results.append({
                            "source_url": url,
                            "title": item.get("title"),
                            "content": item.get("description") or item.get("markdown", ""),
                            "raw_data": item
                        })
                
                return results
                
            except Exception as e:
                print(f"Forum search error: {e}")
                return []
    
    async def map_website(self, url: str) -> List[str]:
        """
        Map all URLs on a website.
        
        Args:
            url: Base URL to map
            
        Returns:
            List of discovered URLs
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/map",
                    headers=self._get_headers(),
                    json={
                        "url": url,
                        "limit": 100
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                return data.get("links", [])
                
            except Exception as e:
                print(f"Website map error: {e}")
                return []
    
    # ============ NEW METHODS FOR EXPANDED SCRAPING ============
    
    async def search_reviews(self, brand_name: str) -> List[Dict[str, Any]]:
        """
        Search for reviews of a brand across multiple review sites.
        
        Args:
            brand_name: Name of the brand
            
        Returns:
            List of review data dicts
        """
        review_sites = [
            f'"{brand_name}" reviews site:trustpilot.com',
            f'"{brand_name}" reviews site:g2.com',
            f'"{brand_name}" reviews site:capterra.com',
            f'"{brand_name}" customer reviews',
        ]
        
        all_results = []
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for query in review_sites:
                try:
                    response = await client.post(
                        f"{self.base_url}/search",
                        headers=self._get_headers(),
                        json={
                            "query": query,
                            "limit": 10
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    for item in data.get("data", []):
                        all_results.append({
                            "source_url": item.get("url"),
                            "title": item.get("title"),
                            "content": item.get("description", ""),
                            "source_type": self._identify_review_source(item.get("url", "")),
                            "raw_data": item
                        })
                except Exception as e:
                    print(f"    [!] Review search error for '{query}': {e}")
                    continue
        
        return all_results
    
    def _identify_review_source(self, url: str) -> str:
        """Identify the review source from URL."""
        url_lower = url.lower()
        if "trustpilot" in url_lower:
            return "trustpilot"
        elif "g2.com" in url_lower:
            return "g2"
        elif "capterra" in url_lower:
            return "capterra"
        elif "amazon" in url_lower:
            return "amazon"
        elif "yelp" in url_lower:
            return "yelp"
        return "other_review"
    
    async def scrape_trustpilot(self, brand_name: str) -> List[Dict[str, Any]]:
        """
        Scrape Trustpilot reviews for a brand.
        
        Args:
            brand_name: Name of the brand
            
        Returns:
            List of review data dicts
        """
        # First search for the Trustpilot page
        search_query = f"{brand_name} site:trustpilot.com"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                # Find the Trustpilot page
                response = await client.post(
                    f"{self.base_url}/search",
                    headers=self._get_headers(),
                    json={
                        "query": search_query,
                        "limit": 3
                    }
                )
                response.raise_for_status()
                search_data = response.json()
                
                trustpilot_url = None
                for item in search_data.get("data", []):
                    url = item.get("url", "")
                    if "trustpilot.com/review/" in url.lower():
                        trustpilot_url = url
                        break
                
                if not trustpilot_url:
                    return []
                
                # Scrape the Trustpilot page
                response = await client.post(
                    f"{self.base_url}/scrape",
                    headers=self._get_headers(),
                    json={
                        "url": trustpilot_url,
                        "formats": ["markdown"]
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                if not data.get("success"):
                    return []
                
                content = data.get("data", {}).get("markdown", "")
                
                return [{
                    "source_url": trustpilot_url,
                    "title": f"Trustpilot Reviews - {brand_name}",
                    "content": content,
                    "source_type": "trustpilot",
                    "raw_data": data.get("data", {})
                }]
                
            except Exception as e:
                print(f"    [!] Trustpilot scrape error: {e}")
                return []
    
    async def search_news_mentions(self, brand_name: str) -> List[Dict[str, Any]]:
        """
        Search for news articles and blog posts mentioning the brand.
        
        Args:
            brand_name: Name of the brand
            
        Returns:
            List of news/blog data dicts
        """
        queries = [
            f'"{brand_name}" news',
            f'"{brand_name}" review blog',
            f'"{brand_name}" announcement',
        ]
        
        all_results = []
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for query in queries:
                try:
                    response = await client.post(
                        f"{self.base_url}/search",
                        headers=self._get_headers(),
                        json={
                            "query": query,
                            "limit": 10
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    for item in data.get("data", []):
                        url = item.get("url", "").lower()
                        # Filter out social media and forums (we get those separately)
                        if not any(x in url for x in ["reddit.com", "twitter.com", "facebook.com", "instagram.com"]):
                            all_results.append({
                                "source_url": item.get("url"),
                                "title": item.get("title"),
                                "content": item.get("description", ""),
                                "source_type": "news_blog",
                                "raw_data": item
                            })
                except Exception as e:
                    print(f"    [!] News search error: {e}")
                    continue
        
        # Deduplicate by URL
        seen_urls = set()
        unique_results = []
        for item in all_results:
            if item["source_url"] not in seen_urls:
                seen_urls.add(item["source_url"])
                unique_results.append(item)
        
        return unique_results[:20]  # Limit to 20 results
    
    async def search_competitors(self, brand_name: str, sector: str, competitors: List[str] = None) -> List[Dict[str, Any]]:
        """
        Search for competitor information and comparisons.
        
        Args:
            brand_name: Name of the brand
            sector: Industry sector
            competitors: Optional list of known competitors
            
        Returns:
            List of competitor-related data dicts
        """
        queries = [
            f'"{brand_name}" vs alternatives',
            f'"{brand_name}" competitors comparison',
            f'best {sector} alternatives to "{brand_name}"',
        ]
        
        # Add specific competitor comparisons if provided
        if competitors:
            for comp in competitors[:3]:
                queries.append(f'"{brand_name}" vs "{comp}"')
        
        all_results = []
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for query in queries:
                try:
                    response = await client.post(
                        f"{self.base_url}/search",
                        headers=self._get_headers(),
                        json={
                            "query": query,
                            "limit": 10
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    for item in data.get("data", []):
                        all_results.append({
                            "source_url": item.get("url"),
                            "title": item.get("title"),
                            "content": item.get("description", ""),
                            "source_type": "competitor_comparison",
                            "raw_data": item
                        })
                except Exception as e:
                    print(f"    [!] Competitor search error: {e}")
                    continue
        
        return all_results[:15]
    
    async def scrape_competitor_site(self, competitor_url: str) -> Dict[str, Any]:
        """
        Scrape a competitor's website for analysis.
        
        Args:
            competitor_url: URL of competitor website
            
        Returns:
            Dict with competitor website data
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/scrape",
                    headers=self._get_headers(),
                    json={
                        "url": competitor_url,
                        "formats": ["markdown"],
                        "onlyMainContent": True
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                if data.get("success"):
                    return {
                        "url": competitor_url,
                        "content": data.get("data", {}).get("markdown", ""),
                        "metadata": data.get("data", {}).get("metadata", {})
                    }
                return {}
                
            except Exception as e:
                print(f"    [!] Competitor scrape error: {e}")
                return {}
    
    async def deep_search_segment(self, keywords: List[str], sector: str) -> List[Dict[str, Any]]:
        """
        Deep search for segment/market discussions beyond just Reddit.
        
        Args:
            keywords: List of relevant keywords
            sector: Industry sector
            
        Returns:
            List of segment discussion data
        """
        all_results = []
        
        # Different search strategies
        search_strategies = []
        
        for keyword in keywords[:5]:
            search_strategies.extend([
                f'"{keyword}" discussion forum',
                f'"{keyword}" community advice',
                f'"{keyword}" experience review',
                f'"{keyword}" tips recommendations',
            ])
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for query in search_strategies[:15]:  # Limit total searches
                try:
                    response = await client.post(
                        f"{self.base_url}/search",
                        headers=self._get_headers(),
                        json={
                            "query": query,
                            "limit": 5
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    for item in data.get("data", []):
                        all_results.append({
                            "source_url": item.get("url"),
                            "title": item.get("title"),
                            "content": item.get("description", ""),
                            "search_query": query,
                            "source_type": "segment_discussion",
                            "raw_data": item
                        })
                except Exception as e:
                    continue
        
        # Deduplicate
        seen_urls = set()
        unique_results = []
        for item in all_results:
            if item["source_url"] not in seen_urls:
                seen_urls.add(item["source_url"])
                unique_results.append(item)
        
        return unique_results
    
    # ============ ADDITIONAL SOURCES ============
    
    async def search_youtube_comments(self, brand_name: str) -> List[Dict[str, Any]]:
        """
        Search for YouTube videos and comments about the brand.
        
        Args:
            brand_name: Name of the brand
            
        Returns:
            List of YouTube content data
        """
        queries = [
            f'"{brand_name}" review site:youtube.com',
            f'"{brand_name}" honest opinion site:youtube.com',
            f'"{brand_name}" unboxing site:youtube.com',
        ]
        
        all_results = []
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for query in queries:
                try:
                    response = await client.post(
                        f"{self.base_url}/search",
                        headers=self._get_headers(),
                        json={
                            "query": query,
                            "limit": 5
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    for item in data.get("data", []):
                        url = item.get("url", "")
                        if "youtube.com" in url.lower() or "youtu.be" in url.lower():
                            all_results.append({
                                "source_url": url,
                                "title": item.get("title"),
                                "content": item.get("description", ""),
                                "source_type": "youtube",
                                "raw_data": item
                            })
                except Exception as e:
                    print(f"    [!] YouTube search error: {e}")
                    continue
        
        return all_results[:10]
    
    async def search_quora(self, brand_name: str, keywords: List[str] = None) -> List[Dict[str, Any]]:
        """
        Search Quora for questions about the brand or related topics.
        
        Args:
            brand_name: Name of the brand
            keywords: Optional related keywords
            
        Returns:
            List of Quora data
        """
        queries = [
            f'"{brand_name}" site:quora.com',
            f'Is "{brand_name}" worth it site:quora.com',
            f'"{brand_name}" review experience site:quora.com',
        ]
        
        # Add keyword-based queries
        if keywords:
            for kw in keywords[:3]:
                queries.append(f'{kw} site:quora.com')
        
        all_results = []
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for query in queries[:6]:
                try:
                    response = await client.post(
                        f"{self.base_url}/search",
                        headers=self._get_headers(),
                        json={
                            "query": query,
                            "limit": 5
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    for item in data.get("data", []):
                        url = item.get("url", "")
                        if "quora.com" in url.lower():
                            all_results.append({
                                "source_url": url,
                                "title": item.get("title"),
                                "content": item.get("description", ""),
                                "source_type": "quora",
                                "raw_data": item
                            })
                except Exception as e:
                    print(f"    [!] Quora search error: {e}")
                    continue
        
        # Deduplicate
        seen_urls = set()
        unique = []
        for item in all_results:
            if item["source_url"] not in seen_urls:
                seen_urls.add(item["source_url"])
                unique.append(item)
        
        return unique[:15]
    
    async def search_product_hunt(self, brand_name: str) -> List[Dict[str, Any]]:
        """
        Search Product Hunt for the brand or product.
        
        Args:
            brand_name: Name of the brand
            
        Returns:
            List of Product Hunt data
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/search",
                    headers=self._get_headers(),
                    json={
                        "query": f'"{brand_name}" site:producthunt.com',
                        "limit": 5
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                results = []
                for item in data.get("data", []):
                    url = item.get("url", "")
                    if "producthunt.com" in url.lower():
                        results.append({
                            "source_url": url,
                            "title": item.get("title"),
                            "content": item.get("description", ""),
                            "source_type": "product_hunt",
                            "raw_data": item
                        })
                
                # If found Product Hunt page, try to scrape it for more details
                if results:
                    try:
                        scrape_resp = await client.post(
                            f"{self.base_url}/scrape",
                            headers=self._get_headers(),
                            json={
                                "url": results[0]["source_url"],
                                "formats": ["markdown"]
                            }
                        )
                        if scrape_resp.status_code == 200:
                            scrape_data = scrape_resp.json()
                            if scrape_data.get("success"):
                                results[0]["content"] = scrape_data.get("data", {}).get("markdown", "")[:5000]
                    except:
                        pass
                
                return results
                
            except Exception as e:
                print(f"    [!] Product Hunt search error: {e}")
                return []
    
    async def search_app_store_reviews(self, brand_name: str) -> List[Dict[str, Any]]:
        """
        Search for App Store and Play Store reviews.
        
        Args:
            brand_name: Name of the brand/app
            
        Returns:
            List of app store review data
        """
        queries = [
            f'"{brand_name}" app review site:apps.apple.com',
            f'"{brand_name}" app review site:play.google.com',
            f'"{brand_name}" app store reviews',
        ]
        
        all_results = []
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for query in queries:
                try:
                    response = await client.post(
                        f"{self.base_url}/search",
                        headers=self._get_headers(),
                        json={
                            "query": query,
                            "limit": 5
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    for item in data.get("data", []):
                        url = item.get("url", "")
                        source_type = "app_store"
                        if "play.google.com" in url:
                            source_type = "play_store"
                        elif "apps.apple.com" in url:
                            source_type = "app_store"
                        
                        all_results.append({
                            "source_url": url,
                            "title": item.get("title"),
                            "content": item.get("description", ""),
                            "source_type": source_type,
                            "raw_data": item
                        })
                except Exception as e:
                    print(f"    [!] App store search error: {e}")
                    continue
        
        return all_results[:10]
    
    async def search_medium_articles(self, brand_name: str, keywords: List[str] = None) -> List[Dict[str, Any]]:
        """
        Search Medium for articles about the brand.
        
        Args:
            brand_name: Name of the brand
            keywords: Optional related keywords
            
        Returns:
            List of Medium article data
        """
        queries = [
            f'"{brand_name}" site:medium.com',
        ]
        
        if keywords:
            for kw in keywords[:2]:
                queries.append(f'{kw} site:medium.com')
        
        all_results = []
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for query in queries[:4]:
                try:
                    response = await client.post(
                        f"{self.base_url}/search",
                        headers=self._get_headers(),
                        json={
                            "query": query,
                            "limit": 5
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    for item in data.get("data", []):
                        url = item.get("url", "")
                        if "medium.com" in url.lower():
                            all_results.append({
                                "source_url": url,
                                "title": item.get("title"),
                                "content": item.get("description", ""),
                                "source_type": "medium",
                                "raw_data": item
                            })
                except Exception as e:
                    print(f"    [!] Medium search error: {e}")
                    continue
        
        # Deduplicate
        seen_urls = set()
        unique = []
        for item in all_results:
            if item["source_url"] not in seen_urls:
                seen_urls.add(item["source_url"])
                unique.append(item)
        
        return unique[:10]
    
    async def search_linkedin_posts(self, brand_name: str) -> List[Dict[str, Any]]:
        """
        Search for public LinkedIn posts mentioning the brand.
        
        Args:
            brand_name: Name of the brand
            
        Returns:
            List of LinkedIn data
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/search",
                    headers=self._get_headers(),
                    json={
                        "query": f'"{brand_name}" site:linkedin.com',
                        "limit": 10
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                results = []
                for item in data.get("data", []):
                    url = item.get("url", "")
                    if "linkedin.com" in url.lower():
                        results.append({
                            "source_url": url,
                            "title": item.get("title"),
                            "content": item.get("description", ""),
                            "source_type": "linkedin",
                            "raw_data": item
                        })
                
                return results[:10]
                
            except Exception as e:
                print(f"    [!] LinkedIn search error: {e}")
                return []
    
    async def scrape_google_reviews(self, queries: List[str]) -> List[Dict[str, Any]]:
        """
        Search for business reviews using Firecrawl.
        This is a FREE alternative to the expensive Apify Google Places actor.
        Searches multiple review sites: Yelp, Google, BBB, Consumer Affairs, etc.
        
        Args:
            queries: List of business names to search for
            
        Returns:
            List of review data dicts
        """
        if not self.has_key:
            return []
        
        print(f"    [Firecrawl] Searching business reviews for {len(queries)} queries...")
        results = []
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for query in queries[:5]:  # Limit to 5 queries to save API usage
                try:
                    # Simple search for reviews - Firecrawl will find relevant pages
                    search_query = f'{query} reviews'
                    
                    response = await self._rate_limited_request(
                        client,
                        "POST",
                        f"{self.base_url}/search",
                        operation_name="business_reviews",
                        json={
                            "query": search_query,
                            "limit": 15
                        }
                    )
                    
                    if response and response.status_code == 200:
                        data = response.json()
                        items = data.get("data", [])
                        
                        for item in items:
                            content = item.get("markdown", "") or item.get("description", "")
                            if content and len(content) > 30:
                                results.append({
                                    "source_url": item.get("url", ""),
                                    "title": item.get("title", query),
                                    "content": content[:2000],  # Limit content size
                                    "author": None,
                                    "posted_at": None,
                                    "rating": None,
                                    "raw_data": item
                                })
                        
                        print(f"       -> {query}: {len(items)} results")
                    elif response:
                        print(f"       -> {query}: HTTP {response.status_code}")
                    else:
                        print(f"       -> {query}: No response")
                        
                except Exception as e:
                    print(f"       -> {query}: Error - {str(e)[:50]}")
                    continue
        
        print(f"    [Firecrawl] Total business reviews: {len(results)}")
        return results

