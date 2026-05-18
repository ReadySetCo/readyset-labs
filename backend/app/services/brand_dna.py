"""
Brand DNA Extractor - Extracts brand identity from MULTIPLE sources (Pomelli-style).
Combines: Website, Google search, Brand Guidelines, Ad Library colors.
"""

import re
import json
import traceback
from typing import Dict, Any, List, Optional
import httpx

from ..config import settings
from .llm.client import get_llm_client


class BrandDNAExtractor:
    """
    Extracts brand identity ("Brand DNA") from multiple sources:
    1. Website branding (colors, fonts, logo, images)
    2. Google search for brand guidelines/colors
    3. Google Images for logo and brand assets
    4. Ad Library colors (from scraped ads)
    """
    
    def __init__(self):
        self.firecrawl_api_key = settings.FIRECRAWL_API_KEY
        self.firecrawl_base_url = settings.FIRECRAWL_BASE_URL
        self.llm = get_llm_client(task_type="strategy")
        self.timeout = 60.0
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.firecrawl_api_key}",
            "Content-Type": "application/json"
        }
    
    async def extract_brand_dna(
        self, 
        website_url: str, 
        brand_name: str,
        progress_callback: Optional[callable] = None,
        ad_library_data: Optional[Dict] = None,
        competitor_ads_data: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Extract complete brand DNA from MULTIPLE sources.
        
        Args:
            website_url: URL of the brand website
            brand_name: Name of the brand
            progress_callback: Optional callback for progress updates
            ad_library_data: Optional Ad Library data with colors from ads
            competitor_ads_data: Optional competitor ads data for reference
            
        Returns:
            Dict with all brand DNA fields
        """
        result = {
            # Core brand identity
            "brand_colors": [],
            "tagline": None,
            "brand_values": [],
            "brand_aesthetic": [],
            "tone_of_voice": [],
            "logo_url": None,
            "fonts": [],
            
            # NEW: Extended brand DNA from brandbook analysis
            "brand_manifesto": None,  # Long-form brand identity text
            "brand_mission": None,  # One-line mission statement
            "brand_pillars": [],  # Core brand pillars (e.g., Style, Comfort, Impact)
            "target_customer": None,  # Demographics + psychographics description
            "brand_personality": [],  # Personality traits (e.g., Magnetic, Social)
            "founding_story": None,  # How the brand was founded
            "product_categories": [],  # Types of products offered
            
            # NEW: For script generation context
            "alternative_solutions": [],  # What customers use instead (competitors, DIY, etc.)
            "usage_scenarios": [],  # Real-world contexts where product is used
            
            # Images and media
            "brand_images": [],
            "ad_thumbnails": [],  # Thumbnails from Ad Library
            "social_media_urls": {},
            
            # Legacy fields
            "product_descriptions": [],
            "business_overview": None,
            
            # Metadata
            "color_sources": [],  # Track where colors came from
            "image_sources": [],  # Track where images came from
            "website_content": None  # Raw markdown content for scraped_data
        }
        
        def update_progress(step: str):
            if progress_callback:
                progress_callback(step)
            print(f"    [Brand DNA] {step}")
        
        try:
            # Step 1: Scrape website with branding format
            update_progress("Pulling images from website...")
            website_data = await self._scrape_website_branding(website_url)
            
            # Step 2: Extract colors from MULTIPLE sources
            update_progress("Gathering colors from website...")
            website_colors = self._extract_colors_from_html(website_data) if website_data else []
            result["color_sources"].append({"source": "website", "colors": website_colors})
            
            # Store raw website content for scraped_data
            if website_data:
                result["website_content"] = {
                    "markdown": website_data.get("markdown", "")[:50000],  # Limit to 50k chars
                    "title": website_data.get("metadata", {}).get("title", ""),
                    "description": website_data.get("metadata", {}).get("description", "")
                }
            
            # Step 2b: Search for brand guidelines
            update_progress("Searching for brand guidelines...")
            guidelines_colors = await self._search_brand_guidelines(brand_name)
            if guidelines_colors:
                result["color_sources"].append({"source": "brand_guidelines", "colors": guidelines_colors})
            
            # Step 2c: Search Google for brand colors
            update_progress("Searching web for brand colors...")
            google_colors = await self._search_brand_colors_google(brand_name)
            if google_colors:
                result["color_sources"].append({"source": "google_search", "colors": google_colors})
            
            # Step 2d: Extract colors from Ad Library (if available)
            if ad_library_data:
                update_progress("Extracting colors from ads...")
                ad_colors = self._extract_colors_from_ads(ad_library_data)
                if ad_colors:
                    result["color_sources"].append({"source": "ad_library", "colors": ad_colors})
            
            # Step 2e: Use Vision AI to extract brand colors (HIGHEST PRIORITY)
            update_progress("Analyzing brand colors with AI vision...")
            vision_colors = await self._extract_colors_with_vision(website_url, brand_name)
            if vision_colors:
                # Vision colors have highest priority - insert at beginning
                result["color_sources"].insert(0, {"source": "vision_ai", "colors": vision_colors})
            
            # Combine all colors intelligently
            result["brand_colors"] = self._combine_colors(result["color_sources"])
            
            # Step 3: Extract fonts
            update_progress("Picking brand fonts...")
            result["fonts"] = self._extract_fonts(website_data) if website_data else []
            
            # Step 4: Find logo from multiple sources
            update_progress("Finding your logo...")
            result["logo_url"] = await self._find_logo_multi_source(website_data, brand_name)
            
            # Step 5: Extract images from website + Google (with logo first)
            update_progress("Gathering brand images...")
            result["brand_images"] = await self._extract_images_multi_source(
                website_data, brand_name, logo_url=result["logo_url"]
            )
            
            # Step 5b: Extract thumbnails from Ad Library
            if ad_library_data:
                update_progress("Extracting ad thumbnails...")
                ad_thumbnails = self._extract_ad_thumbnails(ad_library_data)
                result["ad_thumbnails"] = ad_thumbnails
                result["image_sources"].append({"source": "ad_library", "count": len(ad_thumbnails)})
            
            # Step 5c: Extract competitor ad images for reference
            if competitor_ads_data:
                update_progress("Analyzing competitor visuals...")
                competitor_images = self._extract_competitor_images(competitor_ads_data)
                result["image_sources"].append({"source": "competitors", "count": len(competitor_images)})
            
            # Step 6: Find social media links
            update_progress("Identifying social media...")
            result["social_media_urls"] = self._extract_social_links(website_data) if website_data else {}
            
            # Step 6b: If no Facebook found, search Google (critical for Ad Library)
            if "facebook" not in result["social_media_urls"]:
                print(f"    [Brand DNA] No Facebook link found on website, searching Google...")
                fb_url = await self._search_facebook_page(brand_name)
                if fb_url:
                    result["social_media_urls"]["facebook"] = fb_url
                    print(f"    [Brand DNA] Found Facebook via Google: {fb_url}")
            
            # Step 7: Use LLM to analyze brand identity
            update_progress("Studying your brand values...")
            llm_analysis = await self._analyze_with_llm(
                website_data, brand_name, progress_callback
            )
            
            if llm_analysis:
                # Core identity
                result["tagline"] = llm_analysis.get("tagline")
                result["brand_values"] = llm_analysis.get("brand_values", [])
                result["brand_aesthetic"] = llm_analysis.get("brand_aesthetic", [])
                result["tone_of_voice"] = llm_analysis.get("tone_of_voice", [])
                result["business_overview"] = llm_analysis.get("business_overview")
                result["product_descriptions"] = llm_analysis.get("product_descriptions", [])
                
                # NEW: Extended brand DNA fields
                result["brand_manifesto"] = llm_analysis.get("brand_manifesto")
                result["brand_mission"] = llm_analysis.get("brand_mission")
                result["brand_pillars"] = llm_analysis.get("brand_pillars", [])
                result["target_customer"] = llm_analysis.get("target_customer")
                result["brand_personality"] = llm_analysis.get("brand_personality", [])
                result["founding_story"] = llm_analysis.get("founding_story")
                result["product_categories"] = llm_analysis.get("product_categories", [])
                
                # NEW: For script generation context
                result["alternative_solutions"] = llm_analysis.get("alternative_solutions", [])
                result["usage_scenarios"] = llm_analysis.get("usage_scenarios", [])
            
            # ROBUST FALLBACK: If colors are empty after all attempts, try emergency fallbacks
            if not result["brand_colors"] or len(result["brand_colors"]) == 0:
                update_progress("No colors found, trying emergency fallbacks...")
                result["brand_colors"] = await self._emergency_color_fallback(
                    website_url, brand_name, website_data
                )
            
            # ROBUST FALLBACK: If brand values are empty, generate generic ones based on sector
            if not result["brand_values"] or len(result["brand_values"]) == 0:
                update_progress("Generating fallback brand values...")
                result["brand_values"] = self._generate_fallback_values(brand_name, website_data)
            
            # ROBUST FALLBACK: If tone of voice is empty, infer from content
            if not result["tone_of_voice"] or len(result["tone_of_voice"]) == 0:
                result["tone_of_voice"] = self._infer_tone_of_voice(website_data)
            
            # ROBUST FALLBACK: If aesthetic is empty, generate based on colors
            if not result["brand_aesthetic"] or len(result["brand_aesthetic"]) == 0:
                result["brand_aesthetic"] = self._infer_aesthetic_from_colors(result["brand_colors"])
            
            # Log what we got
            print(f"    [Brand DNA] FINAL: {len(result['brand_colors'])} colors, {len(result['brand_values'])} values")
            update_progress("Brand DNA extraction complete!")
            return result
            
        except Exception as e:
            print(f"    [!] Brand DNA extraction error: {e}")
            import traceback
            traceback.print_exc()
            
            # Even on error, try to return something useful
            if not result["brand_colors"]:
                result["brand_colors"] = ["#4A90D9", "#2C3E50"]  # Default blue/dark palette
            if not result["brand_values"]:
                result["brand_values"] = ["Quality", "Innovation", "Trust"]
            if not result["tone_of_voice"]:
                result["tone_of_voice"] = ["Professional", "Friendly"]
            
            return result
    
    async def _search_brand_guidelines(self, brand_name: str) -> List[str]:
        """Search for brand guidelines document and extract colors."""
        colors = []
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                # Search for brand guidelines
                response = await client.post(
                    f"{self.firecrawl_base_url}/search",
                    headers=self._get_headers(),
                    json={
                        "query": f'"{brand_name}" brand guidelines colors',
                        "limit": 5
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                for result in data.get("data", [])[:3]:
                    content = result.get("content", "") or result.get("description", "")
                    url = result.get("url", "")
                    
                    # Look for hex colors in the content
                    hex_colors = re.findall(r'#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b', content)
                    for color in hex_colors:
                        if len(color) == 3:
                            color = ''.join([c*2 for c in color])
                        hex_color = f"#{color.lower()}"
                        if hex_color not in colors and hex_color not in ['#ffffff', '#000000']:
                            colors.append(hex_color)
                    
                    # If we found a PDF brand guidelines, try to scrape it
                    if 'brand' in url.lower() and any(ext in url.lower() for ext in ['.pdf', 'guidelines', 'identity']):
                        try:
                            scrape_resp = await client.post(
                                f"{self.firecrawl_base_url}/scrape",
                                headers=self._get_headers(),
                                json={"url": url, "formats": ["markdown"]}
                            )
                            if scrape_resp.status_code == 200:
                                scrape_data = scrape_resp.json()
                                markdown = scrape_data.get("data", {}).get("markdown", "")
                                extra_colors = re.findall(r'#([0-9a-fA-F]{6})\b', markdown)
                                for c in extra_colors[:10]:
                                    hc = f"#{c.lower()}"
                                    if hc not in colors and hc not in ['#ffffff', '#000000']:
                                        colors.append(hc)
                        except:
                            pass
                
            except Exception as e:
                print(f"    [!] Brand guidelines search error: {e}")
        
        return colors[:10]
    
    async def _search_brand_colors_google(self, brand_name: str) -> List[str]:
        """Search Google for brand colors."""
        colors = []
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                # Search specifically for brand colors
                response = await client.post(
                    f"{self.firecrawl_base_url}/search",
                    headers=self._get_headers(),
                    json={
                        "query": f'"{brand_name}" brand colors hex palette',
                        "limit": 5
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                for result in data.get("data", []):
                    content = result.get("content", "") or result.get("description", "")
                    
                    # Look for hex colors
                    hex_colors = re.findall(r'#([0-9a-fA-F]{6})\b', content)
                    for color in hex_colors:
                        hex_color = f"#{color.lower()}"
                        if hex_color not in colors and hex_color not in ['#ffffff', '#000000', '#f5f5f5']:
                            colors.append(hex_color)
                    
                    # Also look for RGB mentions
                    rgb_pattern = r'rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)'
                    rgb_matches = re.findall(rgb_pattern, content, re.IGNORECASE)
                    for r, g, b in rgb_matches[:5]:
                        hex_color = f"#{int(r):02x}{int(g):02x}{int(b):02x}"
                        if hex_color not in colors and hex_color not in ['#ffffff', '#000000']:
                            colors.append(hex_color)
                
            except Exception as e:
                print(f"    [!] Google color search error: {e}")
        
        return colors[:8]
    
    def _extract_colors_from_ads(self, ad_library_data: Dict) -> List[str]:
        """Extract dominant colors from Ad Library ad images."""
        colors = []
        
        # Ad Library data might have color analysis from Gemini
        ads = ad_library_data.get("ads", [])
        
        for ad in ads[:10]:
            # Check if creative_analysis has color info
            analysis = ad.get("creative_analysis", {})
            
            # Get colors from visual analysis
            visual_style = analysis.get("visual_style", "")
            if isinstance(visual_style, str):
                # Look for hex colors mentioned in analysis
                hex_colors = re.findall(r'#([0-9a-fA-F]{6})\b', visual_style)
                for c in hex_colors:
                    hc = f"#{c.lower()}"
                    if hc not in colors:
                        colors.append(hc)
            
            # Check for explicit color fields
            ad_colors = analysis.get("colors", []) or analysis.get("dominant_colors", [])
            for c in ad_colors:
                if isinstance(c, str) and c.startswith('#'):
                    if c.lower() not in colors:
                        colors.append(c.lower())
        
        return colors[:6]
    
    def _combine_colors(self, color_sources: List[Dict]) -> List[str]:
        """Intelligently combine colors from multiple sources."""
        # Priority: Vision AI > Brand Guidelines > Google > Website > Ads
        priority_order = ["vision_ai", "brand_guidelines", "google_search", "website", "ad_library"]
        
        all_colors = []
        for priority in priority_order:
            for source in color_sources:
                if source["source"] == priority:
                    for color in source["colors"]:
                        if color not in all_colors:
                            all_colors.append(color)
        
        # Filter out very common colors
        filtered = [c for c in all_colors if c.lower() not in [
            '#ffffff', '#000000', '#f5f5f5', '#fafafa', '#e5e5e5', 
            '#333333', '#666666', '#999999', '#cccccc', '#eeeeee'
        ]]
        
        return filtered[:8]  # Return top 8 unique colors
    
    async def _find_logo_multi_source(self, website_data: Optional[Dict], brand_name: str) -> Optional[str]:
        """Find logo from website and Google Images."""
        # First try website
        if website_data:
            logo = self._extract_logo_from_website(website_data)
            if logo:
                return logo
        
        # Then try Google Images
        return await self._search_logo_google(brand_name)
    
    def _extract_logo_from_website(self, website_data: Dict) -> Optional[str]:
        """Extract logo URL from website data."""
        # Check branding data
        branding = website_data.get("branding", {})
        if branding and branding.get("logo"):
            return branding["logo"]
        
        # Check metadata
        metadata = website_data.get("metadata", {})
        og_image = metadata.get("og:image") or metadata.get("ogImage")
        if og_image:
            return og_image
        
        favicon = metadata.get("favicon")
        if favicon:
            return favicon
        
        # Search in HTML
        html = website_data.get("html", "") or website_data.get("rawHtml", "")
        logo_pattern = r'<img[^>]*(?:class|id|alt)=["\'][^"\']*logo[^"\']*["\'][^>]*src=["\']([^"\']+)["\']'
        match = re.search(logo_pattern, html, re.IGNORECASE)
        if match:
            return match.group(1)
        
        return None
    
    async def _search_logo_google(self, brand_name: str) -> Optional[str]:
        """Search Google Images for brand logo."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.firecrawl_base_url}/search",
                    headers=self._get_headers(),
                    json={
                        "query": f'"{brand_name}" logo official',
                        "limit": 5
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                for result in data.get("data", []):
                    # Check if result has an image
                    url = result.get("url", "")
                    if any(ext in url.lower() for ext in ['.png', '.svg', '.jpg', '.jpeg', '.webp']):
                        return url
                    
                    # Check metadata for images
                    og_image = result.get("og:image") or result.get("image")
                    if og_image:
                        return og_image
                
            except Exception as e:
                print(f"    [!] Logo search error: {e}")
        
        return None
    
    async def _extract_images_multi_source(self, website_data: Optional[Dict], brand_name: str, logo_url: Optional[str] = None) -> List[str]:
        """
        Extract brand images from website and Google.
        Prioritizes: Logo > Hero images > About page > Google brand images
        Excludes: Product images, thumbnails, icons
        """
        images = []
        
        # PRIORITY 1: Logo first (if available)
        if logo_url and logo_url not in images:
            images.append(logo_url)
        
        # PRIORITY 2: Hero/banner images from website
        if website_data:
            # Get og:image (usually the main brand image)
            metadata = website_data.get("metadata", {})
            og_image = metadata.get("og:image") or metadata.get("ogImage")
            if og_image and og_image not in images and og_image.startswith(('http://', 'https://')):
                images.append(og_image)
            
            # Get branding images
            branding = website_data.get("branding", {})
            branding_images = branding.get("images") if branding else []
            if branding_images and isinstance(branding_images, list):
                for img in branding_images[:5]:
                    if img and img not in images and self._is_brand_asset(img):
                        images.append(img)
            
            # Get larger images from links (likely hero/banner)
            website_images = self._extract_images_from_website(website_data)
            for img in website_images:
                if img not in images and self._is_brand_asset(img):
                    images.append(img)
        
        # PRIORITY 3: Google search for brand assets
        google_images = await self._search_brand_images_google(brand_name)
        for img in google_images:
            if img not in images:
                images.append(img)
        
        return images[:10]  # Limit to 10 brand images
    
    def _is_brand_asset(self, url: str) -> bool:
        """Check if URL is likely a brand asset vs product image."""
        if not url or not isinstance(url, str):
            return False
        
        # Must be a valid URL
        if not url.startswith(('http://', 'https://', '//')):
            return False
        
        url_lower = url.lower()
        
        # Exclude common product/thumbnail patterns
        exclude_patterns = [
            'product', 'thumb', 'thumbnail', 'icon', 'favicon',
            'cart', 'checkout', '50x', '100x', '150x', '200x',
            '/products/', '/cdn/shop/products', 'variant',
            'swatch', 'color-', 'size-'
        ]
        
        for pattern in exclude_patterns:
            if pattern in url_lower:
                return False
        
        # Prefer larger images
        if any(size in url_lower for size in ['1200', '1920', '2000', 'hero', 'banner', 'header']):
            return True
        
        return True  # Default to including
    
    def _extract_images_from_website(self, website_data: Dict) -> List[str]:
        """Extract images from website data."""
        images = []
        
        # Check branding data
        branding = website_data.get("branding", {})
        if branding and branding.get("images"):
            images.extend(branding["images"])
        
        # Get links that are images
        links = website_data.get("links", [])
        for link in links:
            url = link if isinstance(link, str) else link.get("url", "")
            if any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                if url not in images:
                    images.append(url)
        
        return images[:12]
    
    async def _search_brand_images_google(self, brand_name: str) -> List[str]:
        """Search Google for brand images."""
        images = []
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                # Search for brand products and marketing images
                queries = [
                    f'"{brand_name}" brand product',
                    f'"{brand_name}" marketing campaign',
                    f'"{brand_name}" official'
                ]
                
                for query in queries[:2]:  # Limit to 2 queries
                    try:
                        response = await client.post(
                            f"{self.firecrawl_base_url}/search",
                            headers=self._get_headers(),
                            json={
                                "query": query,
                                "limit": 5
                            }
                        )
                        response.raise_for_status()
                        data = response.json()
                        
                        for result in data.get("data", []):
                            # Check for og:image
                            og_image = result.get("og:image") or result.get("image")
                            if og_image and og_image not in images:
                                images.append(og_image)
                    except:
                        continue
                
            except Exception as e:
                print(f"    [!] Image search error: {e}")
        
        return images[:10]
    
    def _extract_ad_thumbnails(self, ad_library_data: Dict) -> List[Dict[str, Any]]:
        """Extract thumbnails from Ad Library ads."""
        thumbnails = []
        
        ads = ad_library_data.get("ads", [])
        
        for ad in ads[:20]:  # Get up to 20 ad thumbnails
            thumbnail = {}
            
            # Check for thumbnail_url
            if ad.get("thumbnail_url"):
                thumbnail["url"] = ad["thumbnail_url"]
                thumbnail["type"] = "thumbnail"
            elif ad.get("screenshot_url"):
                thumbnail["url"] = ad["screenshot_url"]
                thumbnail["type"] = "screenshot"
            elif ad.get("image_url"):
                thumbnail["url"] = ad["image_url"]
                thumbnail["type"] = "image"
            
            # Add metadata if we found an image
            if thumbnail.get("url"):
                thumbnail["ad_type"] = ad.get("ad_format", "unknown")
                thumbnail["media_type"] = ad.get("media_type", "unknown")
                
                # Get creative analysis info if available
                analysis = ad.get("creative_analysis", {})
                if analysis:
                    thumbnail["visual_style"] = analysis.get("visual_style", "")
                    thumbnail["hook_type"] = analysis.get("hook_type", "")
                
                thumbnails.append(thumbnail)
        
        print(f"    [Brand DNA] Extracted {len(thumbnails)} ad thumbnails")
        return thumbnails
    
    def _extract_competitor_images(self, competitor_ads_data: List[Dict]) -> List[Dict[str, Any]]:
        """Extract images from competitor ads for visual reference."""
        images = []
        
        for competitor in competitor_ads_data[:5]:  # Limit to 5 competitors
            competitor_name = competitor.get("competitor_name", "Unknown")
            ads = competitor.get("ads", [])
            
            for ad in ads[:3]:  # Get up to 3 images per competitor
                image = {}
                
                if ad.get("thumbnail_url"):
                    image["url"] = ad["thumbnail_url"]
                elif ad.get("image_url"):
                    image["url"] = ad["image_url"]
                
                if image.get("url"):
                    image["competitor"] = competitor_name
                    image["ad_format"] = ad.get("ad_format", "unknown")
                    images.append(image)
        
        print(f"    [Brand DNA] Extracted {len(images)} competitor ad images")
        return images
    
    async def _scrape_website_branding(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape website using Firecrawl with branding format."""
        print(f"    [Brand DNA] Starting website scrape: {url}")
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                # Use branding format to get colors, fonts, etc.
                print(f"    [Brand DNA] Calling Firecrawl /scrape (timeout={self.timeout}s)...")
                response = await client.post(
                    f"{self.firecrawl_base_url}/scrape",
                    headers=self._get_headers(),
                    json={
                        "url": url,
                        "formats": ["markdown", "html", "links", "branding"],
                        "onlyMainContent": False
                    }
                )
                print(f"    [Brand DNA] Firecrawl responded: {response.status_code}")
                response.raise_for_status()
                data = response.json()
                print(f"    [Brand DNA] Website scraped successfully: {len(str(data))} bytes")
                return data.get("data", {})
                
            except httpx.HTTPStatusError as e:
                print(f"    [Brand DNA] HTTP error: {e.response.status_code}")
                # Branding format might not be available, fallback
                if e.response.status_code == 400:
                    print(f"    [Brand DNA] Trying fallback without branding format...")
                    try:
                        response = await client.post(
                            f"{self.firecrawl_base_url}/scrape",
                            headers=self._get_headers(),
                            json={
                                "url": url,
                                "formats": ["markdown", "html", "links"],
                                "onlyMainContent": False
                            }
                        )
                        response.raise_for_status()
                        data = response.json()
                        print(f"    [Brand DNA] Fallback succeeded")
                        return data.get("data", {})
                    except Exception as ex:
                        print(f"    [Brand DNA] Fallback failed: {ex}")
                        pass
                print(f"    [!] Scrape error: {e}")
                return None
            except httpx.TimeoutException as e:
                print(f"    [Brand DNA] TIMEOUT after {self.timeout}s: {e}")
                return None
            except Exception as e:
                print(f"    [!] Scrape error: {type(e).__name__}: {e}")
                return None
    
    def _extract_colors_from_html(self, website_data: Dict) -> List[str]:
        """Extract brand colors from website HTML/CSS."""
        colors = []
        
        # Check if branding data is available
        branding = website_data.get("branding", {})
        if branding:
            colors.extend(branding.get("colors", []))
        
        # Fallback: Extract from HTML/CSS
        html = website_data.get("html", "") or website_data.get("rawHtml", "")
        
        # Find hex colors
        hex_pattern = r'#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b'
        found_colors = re.findall(hex_pattern, html)
        
        # Normalize and dedupe
        for color in found_colors[:20]:  # Limit to first 20
            if len(color) == 3:
                color = ''.join([c*2 for c in color])
            hex_color = f"#{color.lower()}"
            if hex_color not in colors and hex_color not in ['#ffffff', '#000000', '#fff', '#000']:
                colors.append(hex_color)
        
        # Limit to most likely brand colors (first 6)
        return colors[:6]
    
    async def _extract_colors_with_vision(self, website_url: str, brand_name: str) -> List[str]:
        """
        Use Gemini Vision to extract brand colors from website screenshot.
        This method distinguishes brand colors from product colors.
        """
        import google.generativeai as genai
        import asyncio
        import tempfile
        import os
        
        colors = []
        
        try:
            # Step 1: Get screenshot from Firecrawl
            print(f"    [Vision] Taking screenshot of {website_url}...")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.firecrawl_base_url}/scrape",
                    headers=self._get_headers(),
                    json={
                        "url": website_url,
                        "formats": ["screenshot"],
                        "waitFor": 3000
                    }
                )
                
                if response.status_code != 200:
                    print(f"    [!] Screenshot failed: {response.status_code}")
                    return colors
                
                data = response.json()
                screenshot_url = data.get("data", {}).get("screenshot")
                
                if not screenshot_url:
                    print(f"    [!] No screenshot returned")
                    return colors
                
                # Download screenshot
                print(f"    [Vision] Downloading screenshot...")
                img_response = await client.get(screenshot_url)
                if img_response.status_code != 200:
                    print(f"    [!] Screenshot download failed")
                    return colors
                
                # Save to temp file
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                    f.write(img_response.content)
                    temp_path = f.name
            
            # Step 2: Analyze with Gemini Vision
            print(f"    [Vision] Analyzing with Gemini Vision...")
            genai.configure(api_key=settings.GEMINI_API_KEY)
            
            image_file = genai.upload_file(temp_path)
            
            prompt = f"""Analyze this screenshot of the {brand_name} website and identify the distinctive BRAND colors.

IMPORTANT RULES:
1. BRAND COLORS are: accent colors used in logo, CTA buttons, highlights, decorative elements
2. EXCLUDE: Black (#000000), White (#FFFFFF), and grays - these are NOT brand colors, they are neutral UI colors
3. EXCLUDE: Colors from product photos or lifestyle images - only UI/branding colors
4. Look for: the distinctive color that makes this brand recognizable (pink, blue, orange, etc.)

Return ONLY a JSON object with:
{{
  "brand_colors": ["#hexcode1", "#hexcode2", ...],  // Max 5 DISTINCTIVE colors, NO black/white/gray
  "primary_color": "#hexcode",  // The MAIN brand accent color (NOT black or white)
  "secondary_color": "#hexcode",  // Second accent color if exists
  "confidence": "high/medium/low"
}}

Return ONLY valid JSON, no other text."""

            model = genai.GenerativeModel("gemini-3-flash-preview")
            
            response = await asyncio.wait_for(
                asyncio.to_thread(model.generate_content, [prompt, image_file]),
                timeout=30.0
            )
            
            # Parse response
            result_text = response.text.strip()
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            
            import json
            result = json.loads(result_text)
            
            brand_colors = result.get("brand_colors", [])
            if brand_colors:
                colors = brand_colors[:5]
                print(f"    [Vision] Extracted colors: {colors}")
            
            # Clean up
            try:
                genai.delete_file(image_file.name)
                os.unlink(temp_path)
            except:
                pass
                
        except asyncio.TimeoutError:
            print(f"    [!] Vision analysis timeout")
        except Exception as e:
            print(f"    [!] Vision analysis error: {type(e).__name__}: {e}")
            print(f"    [!] Vision analysis traceback:\n{traceback.format_exc()}")

        return colors
    
    def _extract_fonts(self, website_data: Dict) -> List[str]:
        """Extract fonts from website data."""
        fonts = []
        
        # Check branding data
        branding = website_data.get("branding", {})
        if branding:
            raw_fonts = branding.get("fonts", [])
            for font in raw_fonts:
                # Handle both string and dict formats
                if isinstance(font, str):
                    fonts.append(font)
                elif isinstance(font, dict):
                    # Firecrawl returns {family: ..., role: ...}
                    font_name = font.get("family") or font.get("name")
                    if font_name:
                        fonts.append(font_name)
            if fonts:
                return fonts[:5]
        
        # Fallback: Extract from HTML/CSS
        html = website_data.get("html", "") or website_data.get("rawHtml", "")
        
        # Common font-family patterns
        font_pattern = r'font-family:\s*["\']?([^;"\'\}]+)'
        found_fonts = re.findall(font_pattern, html, re.IGNORECASE)
        
        for font_str in found_fonts:
            # Split font stack and get first font
            first_font = font_str.split(',')[0].strip().strip('"\'')
            if first_font and first_font not in fonts and first_font.lower() not in ['inherit', 'initial', 'unset']:
                fonts.append(first_font)
        
        return fonts[:5]
    
    def _extract_logo(self, website_data: Dict) -> Optional[str]:
        """Extract logo URL from website data."""
        # Check branding data
        branding = website_data.get("branding", {})
        if branding and branding.get("logo"):
            return branding["logo"]
        
        # Check metadata
        metadata = website_data.get("metadata", {})
        
        # Try og:image first (often the logo)
        og_image = metadata.get("og:image") or metadata.get("ogImage")
        if og_image:
            return og_image
        
        # Try favicon
        favicon = metadata.get("favicon")
        if favicon:
            return favicon
        
        # Search in HTML for logo
        html = website_data.get("html", "") or website_data.get("rawHtml", "")
        
        # Look for img tags with logo in class, id, or alt
        logo_pattern = r'<img[^>]*(?:class|id|alt)=["\'][^"\']*logo[^"\']*["\'][^>]*src=["\']([^"\']+)["\']'
        logo_match = re.search(logo_pattern, html, re.IGNORECASE)
        if logo_match:
            return logo_match.group(1)
        
        # Reverse pattern (src before class)
        logo_pattern2 = r'<img[^>]*src=["\']([^"\']+)["\'][^>]*(?:class|id|alt)=["\'][^"\']*logo'
        logo_match2 = re.search(logo_pattern2, html, re.IGNORECASE)
        if logo_match2:
            return logo_match2.group(1)
        
        return None
    
    def _extract_images(self, website_data: Dict) -> List[str]:
        """Extract representative brand images."""
        images = []
        
        # Check branding data
        branding = website_data.get("branding", {})
        if branding and branding.get("images"):
            images.extend(branding["images"])
        
        # Get links that are images
        links = website_data.get("links", [])
        for link in links:
            url = link if isinstance(link, str) else link.get("url", "")
            if any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                if url not in images:
                    images.append(url)
        
        return images[:12]  # Limit to 12 images
    
    def _extract_social_links(self, website_data: Dict) -> Dict[str, str]:
        """Extract social media links."""
        social = {}
        
        links = website_data.get("links", [])
        html = website_data.get("html", "") or website_data.get("rawHtml", "")
        
        # All URLs to check
        all_urls = []
        for link in links:
            url = link if isinstance(link, str) else link.get("url", "")
            all_urls.append(url)
        
        # Also extract from HTML
        href_pattern = r'href=["\']([^"\']+)["\']'
        all_urls.extend(re.findall(href_pattern, html))
        
        # Social media patterns
        social_patterns = {
            "twitter": [r'twitter\.com/([^/\s"\'?]+)', r'x\.com/([^/\s"\'?]+)'],
            "instagram": [r'instagram\.com/([^/\s"\'?]+)'],
            "linkedin": [r'linkedin\.com/(?:company|in)/([^/\s"\'?]+)'],
            "facebook": [r'facebook\.com/([^/\s"\'?]+)'],
            "tiktok": [r'tiktok\.com/@?([^/\s"\'?]+)'],
            "youtube": [r'youtube\.com/(?:channel|c|@|user)/([^/\s"\'?]+)']
        }
        
        for url in all_urls:
            for platform, patterns in social_patterns.items():
                if platform in social:
                    continue
                for pattern in patterns:
                    match = re.search(pattern, url, re.IGNORECASE)
                    if match:
                        social[platform] = url if url.startswith('http') else f"https://{url}"
                        break
        
        return social
    
    async def _search_facebook_page(self, brand_name: str) -> Optional[str]:
        """Search Google for the brand's Facebook page."""
        try:
            query = f"{brand_name} facebook page site:facebook.com"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.firecrawl_base_url}/search",
                    headers=self._get_headers(),
                    json={"query": query, "limit": 3},
                )
                response.raise_for_status()
                data = response.json()
                results = data.get("data", []) or []

            for result in results:
                url = result.get("url", "")
                # Match official Facebook page URLs
                if re.match(r'https?://(?:www\.)?facebook\.com/[^/\s]+/?$', url):
                    # Skip generic pages like "facebook.com/search" or "facebook.com/help"
                    path = url.split('facebook.com/')[-1].rstrip('/')
                    if path and path not in ['search', 'help', 'login', 'ads', 'business']:
                        return url
            return None
        except Exception as e:
            print(f"    [!] Error searching for Facebook page: {e}")
            return None
    
    async def _analyze_with_llm(
        self, 
        website_data: Optional[Dict], 
        brand_name: str,
        progress_callback: Optional[callable] = None
    ) -> Optional[Dict[str, Any]]:
        """Use LLM to analyze brand identity."""
        
        def update_progress(step: str):
            if progress_callback:
                progress_callback(step)
            print(f"    [Brand DNA] {step}")
        
        # Handle None website_data
        if not website_data:
            print(f"    [Brand DNA] No website data available for LLM analysis")
            return None
        
        # Get content for analysis
        markdown = website_data.get("markdown", "")
        metadata = website_data.get("metadata", {})
        
        if not markdown:
            return None
        
        # Truncate if too long
        if len(markdown) > 10000:
            markdown = markdown[:10000] + "\n...[truncated]"
        
        update_progress("Learning your tone of voice...")
        
        prompt = f"""Analyze this website content for the brand "{brand_name}" and extract comprehensive brand identity elements.

WEBSITE CONTENT:
{markdown}

METADATA:
Title: {metadata.get('title', 'N/A')}
Description: {metadata.get('description', 'N/A')}

Extract the following in JSON format:

{{
    "tagline": "The brand's main tagline or slogan (short, memorable phrase)",
    "brand_values": ["Value1", "Value2", ...],  // 3-5 core brand values
    "brand_aesthetic": ["aesthetic1", "aesthetic2", ...],  // 3-6 visual/style descriptors
    "tone_of_voice": ["tone1", "tone2", ...],  // 3-5 tone descriptors
    "business_overview": "2-3 sentence description of what the business does",
    
    "brand_manifesto": "Extended brand statement (2-4 sentences) describing what the brand stands for and its purpose. Look for 'About Us', 'Our Story', or mission-type content.",
    
    "brand_mission": "One concise sentence capturing the brand's core mission/purpose",
    
    "brand_pillars": ["Pillar1", "Pillar2", "Pillar3"],  // 3-4 core brand pillars or key promises (e.g., 'Style', 'Comfort', 'Quality', 'Sustainability')
    
    "target_customer": "Description of the ideal customer - demographics (age, gender, income) and psychographics (lifestyle, values, interests). 2-3 sentences.",
    
    "brand_personality": ["Trait1", "Trait2", ...],  // 3-5 personality traits (e.g., 'Magnetic', 'Confident', 'Playful', 'Sophisticated')
    
    "founding_story": "Brief founding story if available (who founded it, when, why). Null if not found.",
    
    "product_categories": ["Category1", "Category2", ...],  // Types of products/services offered
    
    "alternative_solutions": [
        {{"name": "Alternative 1", "type": "competitor/DIY/substitute", "description": "Brief description"}},
        ...
    ],  // Up to 5 alternatives customers might use instead (competitors, DIY methods, substitutes)
    
    "usage_scenarios": [
        {{"scenario": "Scenario name", "environment": "Where", "activity": "What user is doing", "benefit": "Problem solved"}}
    ],  // Up to 5 real-world situations where the product is used
    
    "product_descriptions": [
        {{"name": "Product Name", "description": "Brief description"}},
        ...
    ]
}}

IMPORTANT:
- Extract REAL information from the content, don't make things up
- For tagline, find the actual tagline used (often in hero section or header)
- For manifesto, look for longer brand purpose statements in About/Mission pages
- For target_customer, infer from the messaging, imagery descriptions, and positioning
- For brand_pillars, identify the 3-4 main promises or value propositions
- Return ONLY valid JSON, no markdown formatting."""

        update_progress("Determining your visual aesthetic...")
        
        try:
            result = await self.llm.complete_json(
                prompt=prompt,
                temperature=0.3
            )
            
            update_progress("Writing your tagline...")
            update_progress("Summarizing your business...")
            
            return result
            
        except Exception as e:
            print(f"    [!] LLM analysis error: {e}")
            return None
    
    # ==========================================
    # FALLBACK METHODS - Ensure we always have data
    # ==========================================
    
    async def _emergency_color_fallback(
        self, 
        website_url: str, 
        brand_name: str, 
        website_data: Optional[Dict]
    ) -> List[str]:
        """
        Emergency fallback for colors when all other methods fail.
        Tries multiple strategies to find brand colors.
        """
        colors = []
        print(f"    [Brand DNA] Running emergency color fallback...")
        
        # Strategy 1: Deep CSS variable extraction from HTML
        if website_data:
            html = website_data.get("html", "") or website_data.get("rawHtml", "")
            
            # Look for CSS custom properties (--brand-color, --primary, etc.)
            css_var_patterns = [
                r'--(?:brand|primary|accent|main|theme)[\w-]*:\s*([#\w(),%\s]+)',
                r'--color-(?:primary|brand|accent)[\w-]*:\s*([#\w(),%\s]+)',
                r':root\s*\{[^}]*--[\w-]+:\s*(#[0-9a-fA-F]{3,6})[^}]*\}'
            ]
            
            for pattern in css_var_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                for match in matches[:5]:
                    hex_colors = re.findall(r'#([0-9a-fA-F]{6})', str(match))
                    for c in hex_colors:
                        hc = f"#{c.lower()}"
                        if hc not in colors and hc not in ['#ffffff', '#000000']:
                            colors.append(hc)
            
            # Strategy 2: Look at background-color and color properties
            style_patterns = [
                r'background(?:-color)?:\s*(#[0-9a-fA-F]{6})',
                r'(?<!background-)color:\s*(#[0-9a-fA-F]{6})',
                r'border(?:-color)?:\s*(#[0-9a-fA-F]{6})'
            ]
            
            for pattern in style_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                for match in matches[:10]:
                    hc = match.lower() if match.startswith('#') else f"#{match.lower()}"
                    if hc not in colors and hc not in ['#ffffff', '#000000', '#f5f5f5', '#eeeeee', '#cccccc']:
                        colors.append(hc)
        
        # Strategy 3: Search for "{brand} colors" online
        if len(colors) < 3:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        f"{self.firecrawl_base_url}/search",
                        headers=self._get_headers(),
                        json={
                            "query": f'"{brand_name}" brand colors palette hex',
                            "limit": 3
                        }
                    )
                    if response.status_code == 200:
                        data = response.json()
                        for result in data.get("data", []):
                            content = str(result.get("content", ""))
                            hex_matches = re.findall(r'#([0-9a-fA-F]{6})', content)
                            for c in hex_matches[:3]:
                                hc = f"#{c.lower()}"
                                if hc not in colors and hc not in ['#ffffff', '#000000']:
                                    colors.append(hc)
            except Exception as e:
                print(f"    [!] Color search fallback error: {e}")
        
        # Strategy 4: Industry-specific defaults based on brand name
        if len(colors) < 2:
            print(f"    [Brand DNA] Using industry default colors")
            brand_lower = brand_name.lower()
            
            # Tech/SaaS defaults
            if any(word in brand_lower for word in ['tech', 'ai', 'software', 'app', 'digital']):
                colors.extend(["#4A90D9", "#1E3A5F", "#00D4AA"])
            # Beauty/Fashion defaults
            elif any(word in brand_lower for word in ['beauty', 'fashion', 'style', 'cosmetic', 'skin']):
                colors.extend(["#E8A4B8", "#2C3E50", "#D4AF37"])
            # Health/Wellness defaults
            elif any(word in brand_lower for word in ['health', 'wellness', 'fit', 'gym', 'organic']):
                colors.extend(["#4CAF50", "#2E7D32", "#81C784"])
            # Finance defaults
            elif any(word in brand_lower for word in ['finance', 'bank', 'invest', 'money', 'fund']):
                colors.extend(["#1A237E", "#0D47A1", "#00897B"])
            # Food/Restaurant defaults
            elif any(word in brand_lower for word in ['food', 'restaurant', 'eat', 'cafe', 'cook']):
                colors.extend(["#FF5722", "#FFC107", "#795548"])
            else:
                # Generic professional defaults
                colors.extend(["#3B82F6", "#1E40AF", "#6366F1"])
        
        # Dedupe and limit
        seen = set()
        unique_colors = []
        for c in colors:
            if c.lower() not in seen:
                seen.add(c.lower())
                unique_colors.append(c)
        
        print(f"    [Brand DNA] Emergency fallback found {len(unique_colors)} colors")
        return unique_colors[:6]
    
    def _generate_fallback_values(self, brand_name: str, website_data: Optional[Dict]) -> List[str]:
        """Generate fallback brand values based on content analysis."""
        values = []
        
        # Try to infer from website content
        if website_data:
            markdown = website_data.get("markdown", "").lower()
            
            value_indicators = {
                "Innovation": ["innovate", "innovative", "cutting-edge", "breakthrough", "pioneering"],
                "Quality": ["quality", "premium", "finest", "best-in-class", "excellence"],
                "Trust": ["trust", "trusted", "reliable", "dependable", "integrity"],
                "Sustainability": ["sustainable", "eco", "green", "environment", "ethical"],
                "Customer First": ["customer first", "customer-centric", "for you", "your needs"],
                "Transparency": ["transparent", "honest", "open", "clear pricing"],
                "Expertise": ["expert", "specialist", "professional", "years of experience"],
                "Simplicity": ["simple", "easy", "effortless", "seamless"],
                "Community": ["community", "together", "connect", "belong"],
                "Empowerment": ["empower", "enable", "unlock", "potential"]
            }
            
            for value, keywords in value_indicators.items():
                if any(kw in markdown for kw in keywords):
                    values.append(value)
        
        # If still empty, use generic professional values
        if not values:
            values = ["Quality", "Innovation", "Customer Focus"]
        
        return values[:5]
    
    def _infer_tone_of_voice(self, website_data: Optional[Dict]) -> List[str]:
        """Infer tone of voice from website content."""
        if not website_data:
            return ["Professional", "Friendly"]
        
        markdown = website_data.get("markdown", "").lower()
        tones = []
        
        tone_indicators = {
            "Professional": ["we provide", "our services", "solutions", "expertise"],
            "Friendly": ["hey", "welcome", "we're here", "let's", "you're"],
            "Playful": ["fun", "exciting", "awesome", "amazing", "!"],
            "Authoritative": ["leading", "industry", "proven", "research shows"],
            "Empathetic": ["we understand", "we know", "we've been there", "challenging"],
            "Bold": ["disrupt", "revolutionary", "game-changing", "never before"],
            "Minimalist": website_data.get("markdown", "") and len(website_data.get("markdown", "")) < 2000,
            "Luxurious": ["luxury", "exclusive", "premium", "bespoke", "artisan"]
        }
        
        for tone, indicators in tone_indicators.items():
            if isinstance(indicators, bool):
                if indicators:
                    tones.append(tone)
            elif any(ind in markdown for ind in indicators):
                tones.append(tone)
        
        return tones[:4] if tones else ["Professional", "Approachable"]
    
    def _infer_aesthetic_from_colors(self, colors: List[str]) -> List[str]:
        """Infer brand aesthetic from colors."""
        if not colors:
            return ["Modern", "Clean"]
        
        aesthetics = []
        
        # Analyze color properties
        for color in colors[:3]:
            try:
                # Remove # and parse
                hex_val = color.lstrip('#')
                r = int(hex_val[0:2], 16)
                g = int(hex_val[2:4], 16)
                b = int(hex_val[4:6], 16)
                
                brightness = (r * 299 + g * 587 + b * 114) / 1000
                saturation = max(r, g, b) - min(r, g, b)
                
                # Bright colors = vibrant
                if saturation > 150:
                    if "Vibrant" not in aesthetics:
                        aesthetics.append("Vibrant")
                
                # Dark colors = sophisticated
                if brightness < 100:
                    if "Sophisticated" not in aesthetics:
                        aesthetics.append("Sophisticated")
                
                # Light colors = airy/clean
                if brightness > 200:
                    if "Light & Airy" not in aesthetics:
                        aesthetics.append("Light & Airy")
                
                # Warm colors
                if r > g and r > b:
                    if "Warm" not in aesthetics:
                        aesthetics.append("Warm")
                
                # Cool colors
                if b > r and b > g:
                    if "Cool" not in aesthetics:
                        aesthetics.append("Cool")
                        
            except:
                pass
        
        # Add default if nothing inferred
        if not aesthetics:
            aesthetics = ["Modern", "Clean"]
        
        return aesthetics[:4]
