"""
Free Social Media Scrapers - SIMPLIFIED VERSION.
Most free scrapers are broken or unreliable in 2024:
- ntscraper: Nitter instances are mostly down
- instaloader: Instagram now requires login for hashtag search (we support login now!)
- TikTokApi: Playwright doesn't work properly on Windows with asyncio

This module provides graceful fallbacks and logging.
"""

import asyncio
from typing import Dict, Any, List
from datetime import datetime

from ...config import settings


class SocialFreeScraper:
    """
    Unified interface for free social media scrapers.
    Most methods will return empty results with logging since
    free scrapers are largely non-functional in 2024.
    """
    
    def __init__(self):
        self.twitter_available = False
        self.instagram_available = False
        self.instagram_logged_in = False
        self.tiktok_available = False
        self.youtube_available = False
        self._instaloader = None
        
        # Check what's available
        self._check_availability()
    
    def _check_availability(self):
        """Check which scrapers are available."""
        # Twitter/ntscraper - Usually broken due to Nitter being down
        try:
            from ntscraper import Nitter
            # Don't initialize - just check import
            self.twitter_available = True
        except ImportError:
            pass
        
        # YouTube comments - This one usually works
        try:
            from youtube_comment_downloader import YoutubeCommentDownloader
            self.youtube_available = True
        except ImportError:
            pass
        
        # Instagram - Check if we have credentials
        try:
            import instaloader
            self.instagram_available = True
            
            # Try to login if credentials are provided
            if settings.INSTAGRAM_USERNAME and settings.INSTAGRAM_PASSWORD:
                self._init_instagram_with_login()
        except ImportError:
            pass
        
        # TikTok is disabled due to Windows issues
        self.tiktok_available = False
    
    def _init_instagram_with_login(self):
        """Initialize Instagram with login credentials."""
        try:
            import instaloader
            self._instaloader = instaloader.Instaloader()
            self._instaloader.login(settings.INSTAGRAM_USERNAME, settings.INSTAGRAM_PASSWORD)
            self.instagram_logged_in = True
            print("    [Instagram] Logged in successfully")
        except Exception as e:
            print(f"    [Instagram] Login failed: {str(e)[:80]}")
            self.instagram_logged_in = False
    
    async def scrape_twitter(
        self, 
        queries: List[str], 
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Attempt to scrape Twitter using ntscraper.
        WARNING: Nitter instances are often down.
        """
        if not self.twitter_available:
            print("       [!] Twitter free scraper not available (ntscraper not installed)")
            return []
        
        all_results = []
        
        try:
            from ntscraper import Nitter
            scraper = Nitter()
            
            for query in queries[:3]:  # Limit queries
                try:
                    loop = asyncio.get_event_loop()
                    
                    # Clean query
                    clean_query = query.lstrip('@#')
                    
                    tweets = await loop.run_in_executor(
                        None,
                        lambda q=clean_query: scraper.get_tweets(q, mode='term', number=limit)
                    )
                    
                    if tweets and 'tweets' in tweets:
                        for tweet in tweets['tweets'][:limit]:
                            all_results.append({
                                "source_url": tweet.get('link', ''),
                                "title": f"Tweet by @{tweet.get('user', {}).get('username', 'unknown')}",
                                "content": tweet.get('text', ''),
                                "author": tweet.get('user', {}).get('username'),
                                "date": tweet.get('date'),
                                "likes": tweet.get('stats', {}).get('likes', 0),
                                "source_type": "twitter",
                                "raw_data": tweet
                            })
                except Exception as e:
                    error_msg = str(e)
                    if "empty sequence" in error_msg.lower():
                        print("       [!] Twitter: All Nitter instances are down")
                        break  # Don't try more queries
                    else:
                        print(f"       [!] Twitter query '{query}' error: {error_msg[:100]}")
                    continue
                    
        except Exception as e:
            print(f"       [!] Twitter scraper init error: {str(e)[:100]}")
        
        return all_results
    
    async def scrape_instagram_hashtags(
        self, 
        hashtags: List[str], 
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Instagram hashtag scraping - requires login.
        If credentials are configured, will use instaloader with login.
        """
        if not self.instagram_available:
            print("       [!] Instagram: instaloader not installed")
            return []
        
        if not self.instagram_logged_in:
            print("       [!] Instagram: Requires login (set INSTAGRAM_USERNAME/PASSWORD in .env)")
            return []
        
        results = []
        
        try:
            import instaloader
            loop = asyncio.get_event_loop()
            
            def get_hashtag_posts():
                posts = []
                try:
                    for tag in hashtags[:3]:  # Limit hashtags
                        tag = tag.lstrip('#')
                        ht = instaloader.Hashtag.from_name(self._instaloader.context, tag)
                        count = 0
                        for post in ht.get_posts():
                            posts.append({
                                "source_url": f"https://www.instagram.com/p/{post.shortcode}/",
                                "title": f"Post by @{post.owner_username}",
                                "content": (post.caption or "")[:500],
                                "author": post.owner_username,
                                "date": post.date_utc.isoformat() if post.date_utc else None,
                                "likes": post.likes,
                                "comments_count": post.comments,
                                "source_type": "instagram",
                            })
                            count += 1
                            if count >= limit // len(hashtags[:3]):
                                break
                except Exception as e:
                    print(f"       [!] Instagram hashtag error: {str(e)[:80]}")
                return posts
            
            results = await loop.run_in_executor(None, get_hashtag_posts)
            
            if results:
                print(f"       [+] Instagram: Found {len(results)} posts")
                
        except Exception as e:
            print(f"       [!] Instagram error: {str(e)[:80]}")
        
        return results
    
    async def scrape_tiktok_hashtags(
        self, 
        hashtags: List[str], 
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        TikTok scraping via TikTokApi is broken on Windows.
        Returns empty list.
        """
        print("       [!] TikTok: Not supported on Windows (Playwright async issue)")
        return []
    
    async def scrape_youtube_comments(
        self, 
        video_url: str, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Scrape YouTube comments from a video.
        This one usually works reliably.
        """
        if not self.youtube_available:
            print("       [!] YouTube comments scraper not available")
            return []
        
        results = []
        
        try:
            from youtube_comment_downloader import YoutubeCommentDownloader
            downloader = YoutubeCommentDownloader()
            
            loop = asyncio.get_event_loop()
            
            def fetch_comments():
                comments = []
                try:
                    for comment in downloader.get_comments_from_url(video_url):
                        comments.append(comment)
                        if len(comments) >= limit:
                            break
                except Exception as e:
                    print(f"       [!] Comment fetch error: {str(e)[:100]}")
                return comments
            
            comments = await loop.run_in_executor(None, fetch_comments)
            
            for comment in comments:
                results.append({
                    "source_url": video_url,
                    "title": "YouTube Comment",
                    "content": comment.get('text', ''),
                    "author": comment.get('author', ''),
                    "date": comment.get('time', ''),
                    "likes": comment.get('votes', 0),
                    "source_type": "youtube_comment",
                    "raw_data": comment
                })
            
            if results:
                print(f"       [+] YouTube: Found {len(results)} comments")
                
        except Exception as e:
            print(f"       [!] YouTube comments error: {str(e)[:100]}")
        
        return results
    
    def get_status(self) -> Dict[str, bool]:
        """Get availability status of all scrapers."""
        return {
            "twitter": self.twitter_available,
            "instagram": self.instagram_available,
            "tiktok": self.tiktok_available,
            "youtube_comments": self.youtube_available
        }


# Legacy compatibility
def get_free_scrapers() -> Dict[str, Any]:
    """Get instances of all free scrapers."""
    scraper = SocialFreeScraper()
    return {
        "main": scraper,
        "status": scraper.get_status()
    }
