"""
Brand Discovery Service - Discovers brand information from website and web search.
"""

from typing import Dict, Any, Optional
import httpx

from ..config import settings
from .llm.client import get_llm_client
from .llm.prompts import BRAND_DISCOVERY_SYSTEM, BRAND_DISCOVERY_PROMPT
from .scrapers.firecrawl import FirecrawlScraper


class BrandDiscoveryService:
    """Service for discovering brand information."""
    
    def __init__(self):
        self.llm = get_llm_client(task_type="strategy")
        self.firecrawl = FirecrawlScraper()
    
    async def discover(
        self,
        brand_name: str,
        website_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Discover brand information.
        
        1. If website URL provided, scrape it
        2. Otherwise, search for the brand and find website
        3. Analyze with LLM to extract brand info
        
        Args:
            brand_name: Name of the brand
            website_url: Optional website URL
            
        Returns:
            Dict with brand information
        """
        website_content = ""
        
        # Step 1: Get website content
        if website_url:
            print(f"    Scraping website: {website_url}")
            website_content = await self.firecrawl.scrape_website(website_url)
        else:
            # Search for brand website
            print(f"    Searching for brand: {brand_name}")
            search_result = await self.firecrawl.search_brand(brand_name)
            
            if search_result.get("website_url"):
                website_url = search_result["website_url"]
                print(f"    Found website: {website_url}")
                website_content = await self.firecrawl.scrape_website(website_url)
            else:
                # Use search results as content
                website_content = search_result.get("content", "")
        
        # Step 2: Analyze with LLM
        print("    Analyzing brand with LLM...")
        
        # Truncate content if too long
        if len(website_content) > 15000:
            website_content = website_content[:15000] + "\n\n[Content truncated...]"
        
        prompt = BRAND_DISCOVERY_PROMPT.format(
            brand_name=brand_name,
            website_url=website_url or "Not provided",
            website_content=website_content or "No content available"
        )
        
        result = await self.llm.complete_json(
            prompt=prompt,
            system_prompt=BRAND_DISCOVERY_SYSTEM,
            temperature=0.3
        )
        
        # Handle None result
        if result is None:
            print("    [!] LLM returned None, using defaults")
            result = {
                "description": f"Brand: {brand_name}",
                "sector": "Unknown",
                "vertical": "Unknown",
                "products": [],
                "target_audience": "Unknown",
                "value_propositions": [],
                "competitors": [],
                "price_positioning": "unknown",
                "unique_differentiators": []
            }
        
        # Add website URL to result
        result["website_url"] = website_url
        result["website_content_summary"] = website_content[:500] if website_content else ""
        
        return result
    
    async def quick_search(self, brand_name: str) -> Dict[str, Any]:
        """
        Quick search for basic brand info without deep analysis.
        
        Args:
            brand_name: Name of the brand
            
        Returns:
            Dict with basic brand information
        """
        search_result = await self.firecrawl.search_brand(brand_name)
        
        return {
            "brand_name": brand_name,
            "website_url": search_result.get("website_url"),
            "description": search_result.get("description", ""),
            "search_results": search_result.get("results", [])
        }
