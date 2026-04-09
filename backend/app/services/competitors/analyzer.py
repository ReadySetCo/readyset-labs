"""
Competitor Analyzer - Deep competitive analysis.
"""

from typing import Dict, Any, List, Optional
import httpx

from ...config import settings
from ..llm.client import get_llm_client


class CompetitorAnalyzer:
    """Performs deep competitive analysis."""
    
    def __init__(self):
        self.api_key = settings.FIRECRAWL_API_KEY
        self.base_url = settings.FIRECRAWL_BASE_URL
        self.llm = get_llm_client()
        self.timeout = 60.0
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def identify_competitors(
        self, 
        brand_name: str, 
        sector: str, 
        vertical: str,
        known_competitors: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Identify and research competitors.
        """
        print(f"    -> Identifying competitors for {brand_name}...")
        
        competitors = []
        search_context = []  # Collect search results for LLM context
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Search queries to find competitors
            search_queries = [
                f'"{brand_name}" competitors alternatives',
                f'best {vertical} brands companies',
                f'{sector} {vertical} top brands comparison',
            ]
            
            for query in search_queries:
                try:
                    response = await client.post(
                        f"{self.base_url}/search",
                        headers=self._get_headers(),
                        json={"query": query, "limit": 5}
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    for item in data.get("data", []):
                        title = item.get("title", "")
                        description = item.get("description", "")
                        url = item.get("url", "")
                        
                        # Collect context for LLM
                        if title and description:
                            search_context.append(f"- {title}: {description[:200]}")
                        
                except Exception as e:
                    print(f"    [!] Search error: {e}")
                    continue
        
        # Build context from search results
        context_text = "\n".join(search_context[:15]) if search_context else "No search results found."
        
        # Use LLM with search context to identify competitors
        prompt = f"""Identify the top 5 direct competitors for this brand based on the research below:

BRAND: {brand_name}
SECTOR: {sector}  
VERTICAL: {vertical}
KNOWN COMPETITORS: {', '.join(known_competitors or ['none specified'])}

SEARCH RESULTS (for context):
{context_text}

Based on this information, identify REAL competitor companies.
Return a JSON array:
[
    {{
        "name": "Competitor Name",
        "website": "https://competitor.com",
        "positioning": "How they position themselves",
        "estimated_size": "startup/mid-size/enterprise",
        "key_differentiator": "What makes them unique"
    }}
]

IMPORTANT: 
- Only include REAL companies that actually exist
- If you can't find specific competitors from the search, use your knowledge of the {sector} {vertical} space
- Include at least 3 competitors"""

        try:
            competitor_list = await self.llm.complete_json(prompt=prompt, temperature=0.3)
            print(f"       [Competitors] LLM returned: {type(competitor_list).__name__}")
            
            if competitor_list is None:
                print(f"       [Competitors] LLM returned None - will use fallback")
            elif isinstance(competitor_list, list):
                for comp in competitor_list[:7]:
                    if comp.get("name"):
                        competitors.append(comp)
                        print(f"       Found: {comp.get('name')}")
            elif isinstance(competitor_list, dict):
                # Handle wrapped response - try multiple keys
                found_key = None
                for key in ["competitors", "data", "results", "companies"]:
                    if key in competitor_list and isinstance(competitor_list[key], list):
                        found_key = key
                        for comp in competitor_list[key][:7]:
                            if comp.get("name"):
                                competitors.append(comp)
                                print(f"       Found: {comp.get('name')}")
                        break
                if not found_key:
                    print(f"       [Competitors] Dict but keys not recognized: {list(competitor_list.keys())[:5]}")
            else:
                print(f"       [Competitors] Unexpected type: {str(competitor_list)[:100]}")
        except Exception as e:
            print(f"    [!] LLM competitor identification error: {type(e).__name__}: {str(e)[:100]}")
        
        # Fallback: If no competitors found, use known competitors from brand discovery
        if not competitors and known_competitors:
            print(f"       [Competitors] Using known competitors from discovery: {known_competitors}")
            for name in known_competitors[:5]:
                competitors.append({
                    "name": name,
                    "website": "",
                    "positioning": "Competitor in similar space",
                    "estimated_size": "unknown",
                    "key_differentiator": "To be researched"
                })
        
        print(f"       [Competitors] Total found: {len(competitors)}")
        
        # Research each competitor's website (limited to 3 to avoid timeout)
        for i, comp in enumerate(competitors[:3]):
            if comp.get("website"):
                details = await self._scrape_competitor_site(comp["website"])
                competitors[i].update(details)
        
        return competitors
    
    async def _scrape_competitor_site(self, url: str) -> Dict[str, Any]:
        """Scrape a competitor's website for key information."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
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
                
                if not data.get("success"):
                    return {}
                
                content = data.get("data", {}).get("markdown", "")[:5000]
                
                # Extract info with LLM
                prompt = f"""Analyze this competitor website and extract:

{content}

Return JSON:
{{
    "tagline": "Their main tagline/slogan",
    "value_props": ["Key value propositions"],
    "products": ["Main products/services"],
    "target_audience": "Who they target",
    "pricing_model": "How they price (subscription, one-time, freemium, etc.)",
    "key_features": ["Standout features they highlight"],
    "trust_signals": ["Awards, customers, press mentions"],
    "messaging_tone": "Professional/casual/technical/etc.",
    "social_media_urls": {{
        "facebook": "Facebook page URL if found (e.g., facebook.com/brandname)",
        "instagram": "Instagram URL if found",
        "twitter": "Twitter/X URL if found",
        "tiktok": "TikTok URL if found",
        "linkedin": "LinkedIn URL if found",
        "youtube": "YouTube channel URL if found"
    }}
}}

Look for social media links in the footer, header, or anywhere on the page.
For social_media_urls, only include platforms where you found actual URLs."""

                result = await self.llm.complete_json(prompt=prompt, temperature=0.3)
                return result or {}
                
            except Exception as e:
                return {}
    
    async def generate_competitive_matrix(
        self,
        brand_info: Dict[str, Any],
        competitors: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate a competitive comparison matrix.
        
        Args:
            brand_info: Information about the brand
            competitors: List of competitor profiles
            
        Returns:
            Competitive matrix with comparisons
        """
        prompt = f"""Create a competitive analysis matrix.

OUR BRAND:
Name: {brand_info.get('name')}
Products: {brand_info.get('products')}
Value Props: {brand_info.get('value_propositions')}
Target: {brand_info.get('target_audience')}

COMPETITORS:
{competitors}

Generate a comprehensive competitive matrix as JSON:
{{
    "comparison_dimensions": [
        {{
            "dimension": "Pricing",
            "our_brand": "Our approach",
            "competitors": {{"Comp1": "Their approach", "Comp2": "Their approach"}}
        }},
        {{
            "dimension": "Target Audience",
            "our_brand": "...",
            "competitors": {{...}}
        }}
    ],
    "our_strengths": ["Where we win"],
    "our_weaknesses": ["Where we lose"],
    "opportunities": ["Market gaps we can exploit"],
    "threats": ["Competitive threats to address"],
    "positioning_recommendation": "How to position against competitors",
    "messaging_differentiation": ["Messages that set us apart"]
}}

Include dimensions: Pricing, Target Audience, Key Features, Trust/Credibility, 
User Experience, Brand Perception, Market Presence"""

        try:
            matrix = await self.llm.complete_json(prompt=prompt, temperature=0.4)
            return matrix or {}
        except Exception as e:
            print(f"    [!] Matrix generation error: {e}")
            return {}
    
    async def analyze_competitor_messaging(
        self,
        competitor_ads: List[Dict[str, Any]],
        competitor_lps: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze competitor messaging patterns from their ads and LPs.
        
        Returns messaging insights and patterns.
        """
        # Aggregate ad copy
        ad_copies = []
        for ad in competitor_ads:
            if ad.get("ad_copy"):
                ad_copies.append(ad["ad_copy"])
        
        # Aggregate LP headlines
        headlines = []
        for lp in competitor_lps:
            if lp.get("main_headline"):
                headlines.append(lp["main_headline"])
            if lp.get("headline"):
                headlines.append(lp["headline"])
        
        prompt = f"""Analyze competitor messaging patterns:

AD COPIES:
{ad_copies[:10]}

LANDING PAGE HEADLINES:
{headlines[:10]}

Extract messaging patterns as JSON:
{{
    "common_themes": ["Themes that appear repeatedly"],
    "power_words": ["Frequently used power words"],
    "claims_made": ["Types of claims (speed, savings, quality, etc.)"],
    "emotional_appeals": ["Emotions they target"],
    "proof_types": ["How they build credibility"],
    "cta_patterns": ["Common CTA styles"],
    "messaging_gaps": ["What they don't talk about (opportunity for us)"],
    "overused_messages": ["Messages that are saturated/cliche"],
    "differentiation_opportunities": ["How to stand out from these messages"]
}}"""

        try:
            return await self.llm.complete_json(prompt=prompt, temperature=0.4)
        except:
            return {}
    
    async def generate_swot(
        self,
        brand_info: Dict[str, Any],
        competitors: List[Dict[str, Any]],
        market_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate SWOT analysis."""
        prompt = f"""Generate a SWOT analysis for this brand vs its competitors.

BRAND:
{brand_info}

COMPETITORS:
{competitors}

MARKET DATA:
{market_data or 'No additional market data'}

Return detailed SWOT as JSON:
{{
    "strengths": [
        {{"point": "Strength description", "evidence": "Supporting evidence", "leverage_how": "How to leverage"}}
    ],
    "weaknesses": [
        {{"point": "Weakness description", "evidence": "Supporting evidence", "mitigate_how": "How to mitigate"}}
    ],
    "opportunities": [
        {{"point": "Opportunity description", "evidence": "Supporting evidence", "capture_how": "How to capture"}}
    ],
    "threats": [
        {{"point": "Threat description", "evidence": "Supporting evidence", "defend_how": "How to defend"}}
    ],
    "strategic_priorities": ["Top 3 strategic priorities based on SWOT"]
}}"""

        try:
            return await self.llm.complete_json(prompt=prompt, temperature=0.4)
        except Exception as e:
            print(f"    [!] SWOT generation error: {e}")
            return {}




