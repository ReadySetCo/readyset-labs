"""
Apify Scraper - Social media and review scraping using Apify actors.
Works with or without API key - when no key, methods return empty lists gracefully.
"""

from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime

from ...config import settings

# Try to import ApifyClient, but make it optional
try:
    from apify_client import ApifyClient
    APIFY_AVAILABLE = True
except ImportError:
    APIFY_AVAILABLE = False
    ApifyClient = None


class ApifyScraper:
    """
    Scraper using Apify actors for social media and reviews.
    
    Designed to work as a fallback when free scrapers fail.
    If no API key is configured, methods return empty lists gracefully.
    
    Pricing estimates (per 1000 items):
    - Twitter: ~$0.25
    - Instagram: ~$0.40
    - TikTok: ~$0.30
    - Amazon Reviews: ~$0.35
    - Google Reviews: ~$5-10 PER PLACE (very expensive! - disabled by default)
    - Facebook Posts: ~$0.60
    - Trustpilot: ~$0.40
    
    WARNING: Google Places (compass/crawler-google-places) is EXTREMELY expensive!
    It charges per place scraped, not per review. Can consume $50+ in a single run.
    """
    
    # Apify Actor IDs - Updated January 2026
    # NOTE: "twitter" key kept for backwards compatibility, but scraper supports X
    ACTORS = {
        # Social Media - Primary actors
        "twitter": "apidojo/twitter-scraper-lite",  # X (formerly Twitter) - $0.016/query + items
        "tiktok": "clockworks/free-tiktok-scraper",  # TikTok Data Extractor - $5/1000 items
        "instagram": "apify/instagram-profile-scraper",  # Instagram Profile - $2.30-2.60/1000
        "facebook": "apify/facebook-posts-scraper",  # Facebook Posts - pay per event
        "youtube": "bernardo/youtube-scraper",  # YouTube Scraper - videos + comments
        
        # Reviews
        "amazon_reviews": "junglee/amazon-reviews-scraper",  # $25-35/month + usage
        "google_reviews": "compass/crawler-google-places",  # WARNING: ~$5-10 PER PLACE! Disabled by default
        "trustpilot": "epctex/trustpilot-scraper",  # Trustpilot scraper
    }
    
    # Fallback actors if primary fails
    FALLBACK_ACTORS = {
        "twitter": ["quacker/twitter-scraper", "apidojo/tweet-scraper"],
        "tiktok": ["microworlds/tiktok-scraper", "sauerkirsch/tiktok-scraper"],
        "instagram": ["zuzka/instagram-scraper", "apify/instagram-scraper"],
        "youtube": ["apify/youtube-scraper", "streamers/youtube-channel-scraper"],
    }
    
    def __init__(self):
        self.api_token = settings.APIFY_API_TOKEN
        self.client = None
        self.max_items = settings.MAX_POSTS_PER_SOURCE
        self._has_key = False
        
        # DIAGNOSTIC: Print token status
        token_preview = f"{self.api_token[:8]}...{self.api_token[-4:]}" if self.api_token and len(self.api_token) > 12 else "NOT SET"
        print(f"    [Apify] ========================================")
        print(f"    [Apify] Token status: {token_preview}")
        print(f"    [Apify] apify-client installed: {APIFY_AVAILABLE}")
        
        # Only initialize client if Apify is available and token is set
        if APIFY_AVAILABLE and self.api_token:
            try:
                self.client = ApifyClient(self.api_token)
                self._has_key = True
                print(f"    [Apify] Client initialized SUCCESSFULLY")
                print(f"    [Apify] Available actors: {list(self.ACTORS.keys())}")
            except Exception as e:
                print(f"    [Apify] Client initialization FAILED: {e}")
                self.client = None
        else:
            if not APIFY_AVAILABLE:
                print("    [Apify] ERROR: apify-client not installed - run: pip install apify-client")
            elif not self.api_token:
                print("    [Apify] WARNING: No APIFY_API_TOKEN in .env - social media scraping disabled")
        print(f"    [Apify] ========================================")
    
    @property
    def has_key(self) -> bool:
        """Check if Apify API key is configured."""
        return self._has_key and self.client is not None
    
    @property
    def is_available(self) -> bool:
        """Check if Apify is available for use."""
        return self.has_key
    
    def _run_sync(self, coro):
        """Run async coroutine in sync context."""
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(None, lambda: asyncio.run(coro))
    
    async def _run_actor(
        self, 
        actor_id: str, 
        actor_input: Dict[str, Any],
        timeout_secs: int = 60  # Reduced from 300 to prevent hangs
    ) -> List[Dict[str, Any]]:
        """
        Generic method to run an Apify actor.
        
        Args:
            actor_id: The Apify actor ID
            actor_input: Input parameters for the actor
            timeout_secs: Timeout in seconds
            
        Returns:
            List of items from the actor's dataset
        """
        if not self.client:
            return []
        
        from ...utils.api_quota_tracker import get_quota_tracker
        tracker = get_quota_tracker()
        
        def run():
            try:
                run_result = self.client.actor(actor_id).call(
                    run_input=actor_input,
                    timeout_secs=timeout_secs
                )
                items = list(self.client.dataset(run_result["defaultDatasetId"]).iterate_items())
                tracker.record_request("apify", True)
                return items
            except Exception as e:
                error_msg = str(e)
                print(f"    [Apify] Actor {actor_id} error: {error_msg}")
                tracker.record_request("apify", False, error_msg)
                return []
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, run)
    
    async def _run_actor_with_fallback(
        self,
        platform: str,
        actor_input: Dict[str, Any],
        timeout_secs: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Run an actor with automatic fallback to alternatives if primary fails.
        
        Args:
            platform: Platform name (twitter, tiktok, instagram, youtube)
            actor_input: Input parameters for the actor
            timeout_secs: Timeout in seconds
            
        Returns:
            List of items from the actor's dataset
        """
        if not self.client:
            return []
        
        # Try primary actor first
        primary_actor = self.ACTORS.get(platform)
        if not primary_actor:
            print(f"    [Apify] Unknown platform: {platform}")
            return []
        
        print(f"       [Apify {platform}] Trying primary actor: {primary_actor}")
        result = await self._run_actor(primary_actor, actor_input, timeout_secs)
        
        if result:
            return result
        
        # Try fallback actors
        fallbacks = self.FALLBACK_ACTORS.get(platform, [])
        for fallback_actor in fallbacks:
            print(f"       [Apify {platform}] Trying fallback actor: {fallback_actor}")
            try:
                result = await self._run_actor(fallback_actor, actor_input, timeout_secs)
                if result:
                    print(f"       [Apify {platform}] Fallback succeeded: {len(result)} items")
                    return result
            except Exception as e:
                print(f"       [Apify {platform}] Fallback {fallback_actor} failed: {str(e)[:50]}")
                continue
        
        # All actors failed - try Firecrawl as last resort for some platforms
        if platform in ("twitter", "tiktok", "instagram"):
            print(f"       [Apify {platform}] All Apify actors failed, trying Firecrawl...")
            return await self._firecrawl_fallback(platform, actor_input)
        
        return []
    
    async def _firecrawl_fallback(
        self,
        platform: str,
        actor_input: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Fallback to Firecrawl for social media scraping.
        This is a last resort when all Apify actors fail.
        """
        try:
            from .firecrawl import FirecrawlScraper
            firecrawl = FirecrawlScraper()
            
            if not firecrawl.has_key:
                return []
            
            results = []
            
            # Extract search terms from actor input
            search_terms = []
            if "searchTerms" in actor_input:
                search_terms = actor_input["searchTerms"]
            elif "hashtags" in actor_input:
                search_terms = [f"#{h}" for h in actor_input["hashtags"]]
            elif "keywords" in actor_input:
                search_terms = actor_input["keywords"]
            elif "searchKeywords" in actor_input:
                search_terms = actor_input["searchKeywords"]
            
            if not search_terms:
                return []
            
            # Search using Firecrawl
            for term in search_terms[:3]:  # Limit to 3 terms
                site_filter = {
                    "twitter": "site:twitter.com OR site:x.com",
                    "tiktok": "site:tiktok.com",
                    "instagram": "site:instagram.com"
                }.get(platform, "")
                
                query = f'"{term}" {site_filter}'
                posts = await firecrawl.search_reddit(query)  # Reuse search method
                
                for post in posts[:10]:
                    results.append({
                        "url": post.get("source_url", ""),
                        "text": post.get("content", ""),
                        "title": post.get("title", ""),
                        "source": f"{platform}_firecrawl_fallback"
                    })
            
            if results:
                print(f"       [Firecrawl fallback] Found {len(results)} {platform} posts")
            
            return results
            
        except Exception as e:
            print(f"       [Firecrawl fallback] Error: {str(e)[:50]}")
            return []
    
    async def scrape_twitter(
        self, 
        queries: List[str], 
        track: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Scrape Twitter/X for tweets matching queries.
        
        Args:
            queries: List of search queries or hashtags
            track: 1 for brand mentions, 2 for segment research
            
        Returns:
            List of tweet data dicts
        """
        if not self.client:
            print("       [Apify Twitter] No client configured - skipping")
            return []
        
        print(f"       [Apify X/Twitter] Starting search for: {queries[:2]}...")
        results = []
        
        def run_actor():
            try:
                # Using apidojo/twitter-scraper-lite - reliable for 2024
                actor_input = {
                    "searchTerms": queries[:10],  # Increased from 5 to 10
                    "maxTweets": min(self.max_items, 100),  # Increased from 30 to 100
                    "addUserInfo": True,
                    "scrapeTweetReplies": False
                }
                
                actor_id = self.ACTORS["twitter"]
                print(f"       [Apify X/Twitter] Calling actor: {actor_id}")
                print(f"       [Apify X/Twitter] Input: {actor_input}")
                
                run = self.client.actor(actor_id).call(run_input=actor_input, timeout_secs=60)
                
                items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
                print(f"       [Apify X/Twitter] SUCCESS: Got {len(items)} tweets")
                return items
            except Exception as e:
                print(f"       [Apify X/Twitter] FAILED: {type(e).__name__}: {str(e)[:100]}")
                return []
        
        loop = asyncio.get_event_loop()
        items = await loop.run_in_executor(None, run_actor)
        
        for item in items:
            # Handle different response formats from various actors
            author_name = item.get("author", {}).get("userName") if isinstance(item.get("author"), dict) else item.get("user", {}).get("screen_name", "")
            results.append({
                "source_url": item.get("url", item.get("tweetUrl", "")),
                "title": None,
                "content": item.get("text", item.get("full_text", item.get("tweet", ""))),
                "author": author_name or item.get("screen_name", ""),
                "posted_at": self._parse_date(item.get("createdAt", item.get("created_at"))),
                "likes": item.get("likeCount", item.get("favorite_count", 0)),
                "comments_count": item.get("replyCount", item.get("reply_count", 0)),
                "shares": item.get("retweetCount", item.get("retweet_count", 0)),
                "raw_data": item
            })
        
        print(f"       [Apify X/Twitter] Processed {len(results)} tweets")
        return results
    
    async def scrape_tiktok(
        self, 
        queries: List[str], 
        track: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Scrape TikTok for videos matching queries/hashtags.
        
        Args:
            queries: List of search queries or hashtags
            track: 1 for brand mentions, 2 for segment research
            
        Returns:
            List of video data dicts
        """
        if not self.client:
            print("       [Apify TikTok] No client configured - skipping")
            return []
        
        print(f"       [Apify TikTok] Starting search for: {queries[:2]}...")
        results = []
        
        def run_actor():
            try:
                # Format hashtags - remove # prefix if present
                hashtags = []
                for q in queries:
                    tag = q.lstrip("#").strip()
                    if tag:
                        hashtags.append(tag)
                
                if not hashtags:
                    print("       [Apify TikTok] No valid hashtags provided")
                    return []
                
                # Using clockworks/free-tiktok-scraper with reduced timeout
                actor_input = {
                    "hashtags": hashtags[:5],  # Reduced to 5 for faster execution
                    "resultsPerPage": min(self.max_items, 30),  # Reduced for reliability
                    "shouldDownloadVideos": False,
                    "shouldDownloadCovers": False
                }
                
                actor_id = self.ACTORS["tiktok"]
                print(f"       [Apify TikTok] Calling actor: {actor_id}")
                print(f"       [Apify TikTok] Hashtags: {hashtags[:3]}")
                
                # Reduced timeout from 60 to 45 seconds for faster failure
                run = self.client.actor(actor_id).call(run_input=actor_input, timeout_secs=45)
                
                items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
                print(f"       [Apify TikTok] SUCCESS: Got {len(items)} videos")
                return items
            except Exception as e:
                error_msg = str(e)
                # Check for timeout-like errors
                if "timeout" in error_msg.lower() or "deadline" in error_msg.lower() or "timed out" in error_msg.lower():
                    print(f"       [Apify TikTok] TIMEOUT: Actor took too long")
                else:
                    print(f"       [Apify TikTok] FAILED: {type(e).__name__}: {error_msg[:100]}")
                return []
        
        loop = asyncio.get_event_loop()
        
        # Wrap with asyncio timeout as additional protection
        try:
            items = await asyncio.wait_for(
                loop.run_in_executor(None, run_actor),
                timeout=60.0  # 60 second outer timeout
            )
        except asyncio.TimeoutError:
            print(f"       [Apify TikTok] TIMEOUT: Outer asyncio timeout (60s)")
            items = []
        
        for item in items:
            # Handle various response formats
            author_name = item.get("authorMeta", {}).get("name") if isinstance(item.get("authorMeta"), dict) else item.get("author", "")
            video_url = item.get("webVideoUrl") or item.get("videoUrl") or item.get("video", {}).get("playAddr", "")
            
            results.append({
                "source_url": item.get("webVideoUrl", item.get("videoUrl", "")),
                "title": item.get("text", item.get("desc", ""))[:200],
                "content": item.get("text", item.get("desc", "")),
                "author": author_name,
                "posted_at": self._parse_date(item.get("createTime", item.get("createTimeISO"))),
                "likes": item.get("diggCount", item.get("likes", 0)),
                "comments_count": item.get("commentCount", item.get("comments", 0)),
                "shares": item.get("shareCount", item.get("shares", 0)),
                # Video-specific fields for Gemini analysis
                "is_video": True,
                "video_url": video_url,
                "video_duration": item.get("videoMeta", {}).get("duration", 0) if isinstance(item.get("videoMeta"), dict) else 0,
                "cover_url": item.get("coverUrl") or item.get("videoMeta", {}).get("cover", "") if isinstance(item.get("videoMeta"), dict) else "",
                "source_type": "tiktok",
                "raw_data": item
            })
        
        print(f"       [Apify TikTok] Processed {len(results)} videos")
        return results
    
    async def scrape_instagram(
        self, 
        queries: List[str], 
        track: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Scrape Instagram for posts matching queries/hashtags.
        
        Args:
            queries: List of search queries, hashtags, or usernames
            track: 1 for brand mentions, 2 for segment research
            
        Returns:
            List of post data dicts
        """
        if not self.client:
            print("       [Apify Instagram] No client configured - skipping")
            return []
        
        print(f"       [Apify Instagram] Starting search for: {queries[:2]}...")
        results = []
        
        def run_actor():
            try:
                # Process queries into usernames and hashtags
                usernames = []
                hashtags = []
                
                # Patterns that indicate a hashtag, not a username
                HASHTAG_PATTERNS = ['journey', 'results', 'review', 'transformation', 
                                    'glow', 'tips', 'check', 'tok', 'life', 'community']
                
                def is_likely_hashtag(name):
                    """Check if this looks like a hashtag pattern rather than a real username."""
                    name_lower = name.lower()
                    # If starts with 'my' and ends with common hashtag suffixes
                    if name_lower.startswith('my') and any(name_lower.endswith(p) for p in HASHTAG_PATTERNS):
                        return True
                    # If ends with common hashtag suffixes
                    if any(name_lower.endswith(p) for p in ['review', 'results', 'journey', 'transformation']):
                        return True
                    # Too long to be a real username (IG max is 30)
                    if len(name) > 30:
                        return True
                    return False
                
                for q in queries:
                    clean_q = q.strip()
                    if clean_q.startswith("@"):
                        username = clean_q[1:]
                        if not is_likely_hashtag(username):
                            usernames.append(username)
                    elif clean_q.startswith("#"):
                        hashtags.append(clean_q[1:])
                    else:
                        # Treat as username or search term
                        potential_username = clean_q.replace(" ", "").lower()
                        # Only add if it looks like a real username
                        if not is_likely_hashtag(potential_username):
                            usernames.append(potential_username)
                        else:
                            print(f"       [Apify Instagram] Skipping likely hashtag: {potential_username}")
                
                # If no usernames found but we have hashtags, use them as potential usernames
                # Many hashtags like #cashapp ARE valid usernames — worth trying
                if not usernames and hashtags:
                    for h in hashtags:
                        clean_h = h.lower().strip()
                        if len(clean_h) <= 30 and not is_likely_hashtag(clean_h):
                            usernames.append(clean_h)
                            print(f"       [Apify Instagram] Converting hashtag to username: #{clean_h} -> @{clean_h}")

                if not usernames:
                    print("       [Apify Instagram] No valid usernames to search - skipping")
                    return []
                
                # Using apify/instagram-profile-scraper - more reliable
                actor_input = {
                    "usernames": usernames[:10],  # Increased from 5 to 10
                    "resultsLimit": min(self.max_items, 50),  # Increased from 30 to 50
                    "addParentData": True
                }
                
                actor_id = self.ACTORS["instagram"]
                print(f"       [Apify Instagram] Calling actor: {actor_id}")
                print(f"       [Apify Instagram] Usernames: {usernames[:3]}")
                
                run = self.client.actor(actor_id).call(run_input=actor_input, timeout_secs=60)
                
                items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
                print(f"       [Apify Instagram] SUCCESS: Got {len(items)} posts")
                return items
            except Exception as e:
                print(f"       [Apify Instagram] FAILED: {type(e).__name__}: {str(e)[:100]}")
                return []
        
        loop = asyncio.get_event_loop()
        items = await loop.run_in_executor(None, run_actor)
        
        for item in items:
            # Handle various response formats
            results.append({
                "source_url": item.get("url", item.get("inputUrl", "")),
                "title": None,
                "content": item.get("caption", item.get("description", "")),
                "author": item.get("ownerUsername", item.get("username", "")),
                "posted_at": self._parse_date(item.get("timestamp", item.get("uploadedAt"))),
                "likes": item.get("likesCount", item.get("likes", 0)),
                "comments_count": item.get("commentsCount", item.get("comments", 0)),
                "raw_data": item
            })
        
        print(f"       [Apify Instagram] Processed {len(results)} posts")
        return results
    
    async def scrape_instagram_profile(
        self, 
        username: str,
        max_posts: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Scrape a specific Instagram profile (brand's account).
        
        This is for Track 1: Analyzing the brand's own Instagram content.
        The username should come from brand.social_media_urls["instagram"].
        
        Args:
            username: Instagram username (without @)
            max_posts: Maximum number of posts to scrape
            
        Returns:
            List of post data dicts with video URLs for Gemini analysis
        """
        if not self.client:
            print("       [Apify Instagram Profile] No client configured - skipping")
            return []
        
        # Clean username
        clean_username = username.strip().lstrip("@").lower()
        if not clean_username:
            print("       [Apify Instagram Profile] No username provided - skipping")
            return []
        
        # Also try to extract from full URL if that was passed
        if "instagram.com/" in clean_username:
            import re
            match = re.search(r'instagram\.com/([^/?\s]+)', clean_username)
            if match:
                clean_username = match.group(1)
        
        print(f"       [Apify Instagram Profile] Scraping profile: @{clean_username}...")
        results = []
        
        def run_actor():
            try:
                # Using apify/instagram-profile-scraper for profile data
                actor_input = {
                    "usernames": [clean_username],
                    "resultsLimit": min(max_posts, 100),
                    "addParentData": True  # Get profile metadata too
                }
                
                actor_id = self.ACTORS["instagram"]
                print(f"       [Apify Instagram Profile] Calling actor: {actor_id}")
                
                run = self.client.actor(actor_id).call(run_input=actor_input, timeout_secs=90)
                
                items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
                print(f"       [Apify Instagram Profile] SUCCESS: Got {len(items)} posts from @{clean_username}")
                return items
            except Exception as e:
                print(f"       [Apify Instagram Profile] FAILED: {type(e).__name__}: {str(e)[:100]}")
                return []
        
        loop = asyncio.get_event_loop()
        items = await loop.run_in_executor(None, run_actor)
        
        # The actor returns 1 item per profile (the full profile object).
        # Posts are nested inside as 'latestPosts'.
        for profile_item in items:
            # Extract profile metadata
            profile_meta = {
                "username": profile_item.get("username", clean_username),
                "fullName": profile_item.get("fullName", ""),
                "biography": profile_item.get("biography", ""),
                "followersCount": profile_item.get("followersCount", 0),
                "followsCount": profile_item.get("followsCount", 0),
                "postsCount": profile_item.get("postsCount", 0),
                "verified": profile_item.get("verified", False),
                "isBusinessAccount": profile_item.get("isBusinessAccount", False),
                "businessCategoryName": profile_item.get("businessCategoryName", ""),
                "profilePicUrl": profile_item.get("profilePicUrlHD") or profile_item.get("profilePicUrl", ""),
                "externalUrl": profile_item.get("externalUrl", ""),
            }
            
            # Extract posts from latestPosts array
            latest_posts = profile_item.get("latestPosts", [])
            
            if latest_posts:
                print(f"       [Apify Instagram Profile] Extracting {len(latest_posts)} posts from profile data")
                for post in latest_posts:
                    video_url = post.get("videoUrl") or post.get("video_url")
                    is_video = post.get("type", "").lower() == "video" or video_url is not None
                    
                    results.append({
                        "source_url": post.get("url", f"https://www.instagram.com/p/{post.get('shortCode', '')}/"),
                        "title": None,
                        "content": post.get("caption", post.get("description", "")),
                        "author": clean_username,
                        "posted_at": self._parse_date(post.get("timestamp", post.get("uploadedAt"))),
                        "likes": post.get("likesCount", post.get("likes", 0)),
                        "comments_count": post.get("commentsCount", post.get("comments", 0)),
                        # Additional fields for analysis
                        "is_video": is_video,
                        "video_url": video_url,
                        "video_view_count": post.get("videoViewCount", 0),
                        "display_url": post.get("displayUrl", post.get("imageUrl", "")),
                        "hashtags": post.get("hashtags", []),
                        "mentions": post.get("mentions", []),
                        "source_type": "instagram_profile",
                        "profile_meta": profile_meta,
                        "raw_data": post
                    })
            else:
                # Fallback: treat top-level items as individual posts (old actor format)
                video_url = profile_item.get("videoUrl") or profile_item.get("video_url")
                video_view_count = profile_item.get("videoViewCount", 0)
                is_video = profile_item.get("isVideo", False) or video_url is not None
                
                results.append({
                    "source_url": profile_item.get("url", profile_item.get("inputUrl", "")),
                    "title": None,
                    "content": profile_item.get("caption", profile_item.get("description", "")),
                    "author": clean_username,
                    "posted_at": self._parse_date(profile_item.get("timestamp", profile_item.get("uploadedAt"))),
                    "likes": profile_item.get("likesCount", profile_item.get("likes", 0)),
                    "comments_count": profile_item.get("commentsCount", profile_item.get("comments", 0)),
                    "is_video": is_video,
                    "video_url": video_url,
                    "video_view_count": video_view_count,
                    "display_url": profile_item.get("displayUrl", profile_item.get("imageUrl", "")),
                    "hashtags": profile_item.get("hashtags", []),
                    "mentions": profile_item.get("mentions", []),
                    "source_type": "instagram_profile",
                    "raw_data": profile_item
                })
        
        # Log summary
        video_count = sum(1 for r in results if r.get("is_video"))
        print(f"       [Apify Instagram Profile] Processed {len(results)} posts ({video_count} videos) from @{clean_username}")
        return results
    
    def analyze_instagram_feed(
        self,
        profile_posts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze Instagram feed from scraped profile data.
        
        This provides feed-level insights:
        - Content type distribution (photo/video/carousel)
        - Posting frequency estimates
        - Average engagement metrics
        - Hashtag patterns
        - Caption style analysis
        
        Args:
            profile_posts: List of posts from scrape_instagram_profile
            
        Returns:
            Dict with feed analysis
        """
        if not profile_posts:
            return {"error": "No posts to analyze"}
        
        # Content type distribution
        video_count = sum(1 for p in profile_posts if p.get("is_video"))
        photo_count = len(profile_posts) - video_count
        
        # Engagement metrics
        total_likes = sum(p.get("likes", 0) for p in profile_posts)
        total_comments = sum(p.get("comments_count", 0) for p in profile_posts)
        avg_likes = total_likes / len(profile_posts) if profile_posts else 0
        avg_comments = total_comments / len(profile_posts) if profile_posts else 0
        
        # Video view metrics
        video_views = [p.get("video_view_count", 0) for p in profile_posts if p.get("is_video")]
        avg_video_views = sum(video_views) / len(video_views) if video_views else 0
        
        # Hashtag analysis
        all_hashtags = []
        for p in profile_posts:
            hashtags = p.get("hashtags", [])
            if isinstance(hashtags, list):
                all_hashtags.extend(hashtags)
        
        # Count hashtag frequency
        hashtag_counts = {}
        for tag in all_hashtags:
            tag_lower = str(tag).lower().strip("#")
            hashtag_counts[tag_lower] = hashtag_counts.get(tag_lower, 0) + 1
        
        top_hashtags = sorted(hashtag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Caption analysis
        captions = [p.get("content", "") for p in profile_posts if p.get("content")]
        avg_caption_length = sum(len(c) for c in captions) / len(captions) if captions else 0
        
        # Estimate posting frequency from timestamps
        from datetime import datetime
        timestamps = []
        for p in profile_posts:
            posted_at = p.get("posted_at")
            if posted_at:
                if isinstance(posted_at, str):
                    try:
                        posted_at = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
                    except:
                        continue
                if isinstance(posted_at, datetime):
                    timestamps.append(posted_at)
        
        posting_frequency = "Unknown"
        if len(timestamps) >= 2:
            timestamps.sort()
            time_diffs = [(timestamps[i+1] - timestamps[i]).days for i in range(len(timestamps)-1)]
            avg_days_between = sum(time_diffs) / len(time_diffs) if time_diffs else 0
            if avg_days_between <= 1:
                posting_frequency = "Daily"
            elif avg_days_between <= 3:
                posting_frequency = "2-3x per week"
            elif avg_days_between <= 7:
                posting_frequency = "Weekly"
            elif avg_days_between <= 14:
                posting_frequency = "Bi-weekly"
            else:
                posting_frequency = "Monthly or less"
        
        return {
            "posts_analyzed": len(profile_posts),
            "content_distribution": {
                "videos": video_count,
                "photos": photo_count,
                "video_percentage": round(video_count / len(profile_posts) * 100, 1) if profile_posts else 0,
                "photo_percentage": round(photo_count / len(profile_posts) * 100, 1) if profile_posts else 0
            },
            "engagement_avg": {
                "likes": round(avg_likes),
                "comments": round(avg_comments),
                "video_views": round(avg_video_views) if video_views else "N/A"
            },
            "engagement_total": {
                "likes": total_likes,
                "comments": total_comments
            },
            "posting_frequency": posting_frequency,
            "hashtag_strategy": {
                "total_unique_hashtags": len(hashtag_counts),
                "avg_hashtags_per_post": round(len(all_hashtags) / len(profile_posts)) if profile_posts else 0,
                "top_hashtags": [{"tag": f"#{tag}", "count": count} for tag, count in top_hashtags]
            },
            "caption_style": {
                "avg_length_chars": round(avg_caption_length),
                "style": "Long-form" if avg_caption_length > 500 else "Medium" if avg_caption_length > 150 else "Short"
            }
        }
    
    async def scrape_amazon_reviews(
        self, 
        queries: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Scrape Amazon product reviews.
        
        Args:
            queries: List of product search terms or ASINs
            
        Returns:
            List of review data dicts
        """
        if not self.client:
            return []
        
        results = []
        
        def run_actor():
            try:
                actor_input = {
                    "keywords": queries,
                    "maxReviews": settings.MAX_REVIEWS_PER_SOURCE,
                    "sort": "recent"
                }
                
                run = self.client.actor(self.ACTORS["amazon_reviews"]).call(run_input=actor_input)
                
                items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
                return items
            except Exception as e:
                print(f"    Amazon actor error: {e}")
                return []
        
        loop = asyncio.get_event_loop()
        items = await loop.run_in_executor(None, run_actor)
        
        for item in items:
            results.append({
                "source_url": item.get("url", ""),
                "title": item.get("title", ""),
                "content": item.get("text", ""),
                "author": item.get("author"),
                "posted_at": self._parse_date(item.get("date")),
                "rating": item.get("rating"),
                "raw_data": item
            })
        
        return results
    
    async def scrape_google_reviews(
        self, 
        queries: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Scrape Google Maps/Business reviews.
        
        Args:
            queries: List of business names to search
            
        Returns:
            List of review data dicts
            
        WARNING: This actor is VERY EXPENSIVE (~$5-10 per place).
        Disabled by default. Set APIFY_ENABLE_GOOGLE_PLACES=true to enable.
        """
        # Cost control - check if enabled
        if not settings.APIFY_ENABLE_GOOGLE_PLACES:
            print("    [Google Places] SKIPPED - disabled in settings (cost control)")
            return []
        
        if not self.client:
            return []
        
        # Limit queries to control costs
        queries = queries[:settings.APIFY_MAX_GOOGLE_PLACES]
        print(f"    [Google Places] WARNING: This is expensive! Running {len(queries)} queries...")
        
        results = []
        
        def run_actor():
            try:
                actor_input = {
                    "searchStringsArray": queries,
                    "maxReviews": min(settings.MAX_REVIEWS_PER_SOURCE, 20),  # Limit reviews per place
                    "language": "en"
                }
                
                run = self.client.actor(self.ACTORS["google_reviews"]).call(run_input=actor_input)
                
                items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
                return items
            except Exception as e:
                print(f"    Google Reviews actor error: {e}")
                return []
        
        loop = asyncio.get_event_loop()
        items = await loop.run_in_executor(None, run_actor)
        
        for item in items:
            # Handle nested review structure
            reviews = item.get("reviews", [item])
            for review in reviews:
                results.append({
                    "source_url": item.get("url", ""),
                    "title": item.get("title", ""),
                    "content": review.get("text", ""),
                    "author": review.get("name"),
                    "posted_at": self._parse_date(review.get("publishedAtDate")),
                    "rating": review.get("stars"),
                    "raw_data": review
                })
        
        return results
    
    async def scrape_trustpilot(
        self, 
        brand_name: str
    ) -> List[Dict[str, Any]]:
        """
        Scrape Trustpilot reviews for a brand.
        Uses Firecrawl as primary method since Apify actors are unreliable.
        
        Args:
            brand_name: Name of the brand
            
        Returns:
            List of review data dicts
        """
        print(f"       [Trustpilot] Scraping reviews for: {brand_name}")
        
        # Use Firecrawl for Trustpilot (more reliable)
        try:
            from .firecrawl import FirecrawlScraper
            firecrawl = FirecrawlScraper()
            results = await firecrawl.scrape_trustpilot(brand_name)
            
            if results:
                print(f"       [Trustpilot] SUCCESS via Firecrawl: Got {len(results)} results")
                return results
            else:
                print(f"       [Trustpilot] No results from Firecrawl")
                return []
                
        except Exception as e:
            print(f"       [Trustpilot] Firecrawl error: {str(e)[:100]}")
            return []
    
    async def scrape_facebook(
        self, 
        queries: List[str],
        page_urls: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape Facebook posts from pages or search.
        
        Args:
            queries: List of search terms
            page_urls: Optional list of Facebook page URLs to scrape
            
        Returns:
            List of post data dicts
        """
        if not self.client:
            print("    [Apify] No client - skipping Facebook scraping")
            return []
        
        results = []
        
        def run_actor():
            try:
                actor_input = {
                    "startUrls": [{"url": url} for url in (page_urls or [])],
                    "searchTerms": queries if not page_urls else None,
                    "maxPosts": self.max_items,
                    "maxPostComments": 10,
                    "commentsMode": "RANKED_THREADED"
                }
                
                # Remove None values
                actor_input = {k: v for k, v in actor_input.items() if v is not None}
                
                run = self.client.actor(self.ACTORS["facebook"]).call(run_input=actor_input)
                
                items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
                return items
            except Exception as e:
                print(f"    [Apify] Facebook actor error: {e}")
                return []
        
        loop = asyncio.get_event_loop()
        items = await loop.run_in_executor(None, run_actor)
        
        for item in items:
            # Extract comments if available
            comments = item.get("comments", [])
            comment_texts = [c.get("text", "") for c in comments[:5]]
            
            results.append({
                "source_url": item.get("url", ""),
                "title": item.get("pageName", ""),
                "content": item.get("text", ""),
                "author": item.get("pageName") or item.get("user", {}).get("name"),
                "posted_at": self._parse_date(item.get("time")),
                "likes": item.get("likes", 0),
                "comments_count": item.get("commentsCount", 0),
                "shares": item.get("shares", 0),
                "top_comments": comment_texts,
                "source_type": "facebook",
                "raw_data": item
            })
        
        print(f"    [Apify] Facebook: Found {len(results)} posts")
        return results
    
    async def scrape_youtube(
        self,
        queries: List[str],
        track: int = 1,
        include_comments: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Scrape YouTube for videos and comments matching queries.
        
        Args:
            queries: List of search queries
            track: 1 for brand mentions, 2 for segment research
            include_comments: Whether to include video comments
            
        Returns:
            List of video data dicts with comments
        """
        if not self.client:
            print("       [Apify YouTube] No client configured - skipping")
            return []
        
        print(f"       [Apify YouTube] Starting search for: {queries[:2]}...")
        results = []
        
        def run_actor():
            try:
                # Using bernardo/youtube-scraper
                actor_input = {
                    "searchKeywords": queries[:5],
                    "maxResults": min(self.max_items, 30),
                    "maxResultsShorts": 5,
                    "maxResultStreams": 0,
                    "downloadSubtitles": False,
                    "saveSubsToKVS": False,
                    "maxComments": 20 if include_comments else 0
                }
                
                actor_id = self.ACTORS["youtube"]
                print(f"       [Apify YouTube] Calling actor: {actor_id}")
                
                run = self.client.actor(actor_id).call(run_input=actor_input, timeout_secs=60)
                
                items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
                print(f"       [Apify YouTube] SUCCESS: Got {len(items)} videos")
                return items
            except Exception as e:
                print(f"       [Apify YouTube] FAILED: {type(e).__name__}: {str(e)[:100]}")
                return []
        
        loop = asyncio.get_event_loop()
        items = await loop.run_in_executor(None, run_actor)
        
        for item in items:
            # Extract comments
            comments = item.get("comments", [])
            comment_texts = []
            for c in comments[:10]:
                if isinstance(c, dict):
                    comment_texts.append({
                        "text": c.get("text", ""),
                        "author": c.get("author", ""),
                        "likes": c.get("likes", 0)
                    })
                elif isinstance(c, str):
                    comment_texts.append({"text": c, "author": "", "likes": 0})
            
            results.append({
                "source_url": item.get("url", item.get("videoUrl", "")),
                "title": item.get("title", ""),
                "content": item.get("description", item.get("text", "")),
                "author": item.get("channelName", item.get("channelTitle", "")),
                "posted_at": self._parse_date(item.get("uploadDate", item.get("publishedAt"))),
                "likes": item.get("likes", item.get("likeCount", 0)),
                "comments_count": item.get("commentsCount", len(comments)),
                "views": item.get("viewCount", item.get("views", 0)),
                "duration": item.get("duration", ""),
                "top_comments": comment_texts,
                "source_type": "youtube",
                "raw_data": item
            })
        
        print(f"       [Apify YouTube] Processed {len(results)} videos with comments")
        return results
    
    # ==========================================
    # FALLBACK METHODS (when free scrapers fail)
    # ==========================================
    
    async def scrape_twitter_fallback(
        self,
        queries: List[str],
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Fallback Twitter scraper using Apify.
        Use when ntscraper fails.
        
        Args:
            queries: Search queries
            limit: Max tweets to return
            
        Returns:
            List of tweet data
        """
        if not self.client:
            return []
        
        print("    [Apify] Using Twitter fallback...")
        return await self.scrape_twitter(queries, track=1)
    
    async def scrape_instagram_fallback(
        self,
        hashtags: List[str],
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Fallback Instagram scraper using Apify.
        Use when instaloader fails.
        
        Args:
            hashtags: Hashtags to search
            limit: Max posts to return
            
        Returns:
            List of post data
        """
        if not self.client:
            return []
        
        print("    [Apify] Using Instagram fallback...")
        # Format hashtags for Apify
        formatted = ["#" + h.lstrip("#") for h in hashtags]
        return await self.scrape_instagram(formatted, track=1)
    
    async def scrape_tiktok_fallback(
        self,
        hashtags: List[str],
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Fallback TikTok scraper using Apify.
        Use when TikTokApi fails.
        
        Args:
            hashtags: Hashtags to search
            limit: Max videos to return
            
        Returns:
            List of video data
        """
        if not self.client:
            return []
        
        print("    [Apify] Using TikTok fallback...")
        # Format hashtags for Apify
        formatted = ["#" + h.lstrip("#") for h in hashtags]
        return await self.scrape_tiktok(formatted, track=1)
    
    def _parse_date(self, date_value: Any) -> Optional[datetime]:
        """Parse various date formats to datetime."""
        if not date_value:
            return None
        
        if isinstance(date_value, datetime):
            return date_value
        
        if isinstance(date_value, (int, float)):
            # Unix timestamp
            try:
                return datetime.fromtimestamp(date_value)
            except:
                return None
        
        if isinstance(date_value, str):
            # Try common formats
            formats = [
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
                "%B %d, %Y"
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(date_value, fmt)
                except:
                    continue
        
        return None

