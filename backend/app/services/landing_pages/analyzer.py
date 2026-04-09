"""
Landing Page Analyzer - Scrapes and analyzes landing pages from ads.
"""

import re
from typing import Dict, Any, List, Optional
import httpx

from ...config import settings
from ..llm.client import get_llm_client


class LandingPageAnalyzer:
    """Analyzes landing pages linked from ads."""
    
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
    
    async def analyze_landing_page(self, url: str) -> Dict[str, Any]:
        """
        Scrape and analyze a landing page.
        
        Args:
            url: URL of the landing page
            
        Returns:
            Dict with extracted landing page elements
        """
        print(f"    -> Analyzing LP: {url[:50]}...")
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                # Scrape the landing page
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
                    return {"url": url, "error": "Scrape failed"}
                
                content = data.get("data", {}).get("markdown", "")
                metadata = data.get("data", {}).get("metadata", {})
                
                # Extract elements manually
                elements = self._extract_lp_elements(content, metadata)
                elements["url"] = url
                
                # Use LLM for deeper analysis
                llm_analysis = await self._analyze_with_llm(content, url)
                if llm_analysis:
                    elements.update(llm_analysis)
                
                return elements
                
            except Exception as e:
                print(f"    [!] LP analysis error: {e}")
                return {"url": url, "error": str(e)}
    
    def _extract_lp_elements(self, content: str, metadata: Dict) -> Dict[str, Any]:
        """Extract landing page elements from content."""
        elements = {
            "title": metadata.get("title", ""),
            "description": metadata.get("description", ""),
        }
        
        # Extract headline (first H1 or large text)
        h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if h1_match:
            elements["headline"] = h1_match.group(1).strip()
        
        # Extract subheadline (first H2)
        h2_match = re.search(r'^##\s+(.+)$', content, re.MULTILINE)
        if h2_match:
            elements["subheadline"] = h2_match.group(1).strip()
        
        # Extract CTAs
        cta_patterns = [
            r'\[([^\]]*(?:Get Started|Sign Up|Buy Now|Shop Now|Learn More|Try Free|Start|Subscribe)[^\]]*)\]',
            r'>\s*([^<]*(?:Get Started|Sign Up|Buy Now|Shop Now|Learn More|Try Free|Start|Subscribe)[^<]*)<',
        ]
        ctas = []
        for pattern in cta_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            ctas.extend(matches)
        elements["ctas"] = list(set(ctas))[:5]
        
        # Extract prices
        price_matches = re.findall(r'\$[\d,]+(?:\.\d{2})?(?:/\w+)?', content)
        elements["prices"] = list(set(price_matches))[:5]
        
        # Extract social proof indicators
        social_proof = []
        if re.search(r'\d+[,\s]*(?:customers|users|people|members)', content, re.IGNORECASE):
            match = re.search(r'(\d+[,\d]*)\s*(?:customers|users|people|members)', content, re.IGNORECASE)
            if match:
                social_proof.append(f"{match.group(1)} customers/users")
        if re.search(r'\d+(?:\.\d)?\s*(?:stars?|rating)', content, re.IGNORECASE):
            social_proof.append("Rating displayed")
        if re.search(r'(?:featured in|as seen on|trusted by)', content, re.IGNORECASE):
            social_proof.append("Trust badges")
        elements["social_proof"] = social_proof
        
        # Check for form
        elements["has_form"] = bool(re.search(r'(?:email|name|phone|submit)', content, re.IGNORECASE))
        
        # Check for video
        elements["has_video"] = bool(re.search(r'(?:youtube|vimeo|video|watch)', content, re.IGNORECASE))
        
        # Extract testimonials indicator
        elements["has_testimonials"] = bool(re.search(
            r'(?:testimonial|review|said|says|customer stor)', content, re.IGNORECASE
        ))
        
        return elements
    
    async def _analyze_with_llm(self, content: str, url: str) -> Optional[Dict[str, Any]]:
        """Use LLM to extract deeper insights from landing page."""
        prompt = f"""Analyze this landing page content and extract key marketing elements.

URL: {url}

Content:
{content[:4000]}

Return a JSON object with:
{{
    "main_headline": "The primary headline",
    "value_proposition": "The main value proposition",
    "key_benefits": ["Benefit 1", "Benefit 2", "Benefit 3"],
    "target_audience_signals": "Who this page seems to target",
    "urgency_elements": ["Any urgency/scarcity elements"],
    "trust_elements": ["Trust badges, testimonials, guarantees"],
    "primary_cta": "The main call-to-action",
    "offer_details": "Any specific offer or pricing",
    "objection_handlers": ["How they address common objections"],
    "tone": "The overall tone (professional, casual, urgent, etc.)",
    "effectiveness_notes": "What works well and what could improve"
}}"""

        try:
            result = await self.llm.complete_json(prompt=prompt, temperature=0.3)
            return result
        except Exception as e:
            print(f"    [!] LLM LP analysis error: {e}")
            return None
    
    async def analyze_multiple(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Analyze multiple landing pages."""
        results = []
        for url in urls:
            if url and url.startswith('http'):
                result = await self.analyze_landing_page(url)
                results.append(result)
        return results
    
    async def compare_landing_pages(
        self, 
        brand_lps: List[Dict], 
        competitor_lps: List[Dict]
    ) -> Dict[str, Any]:
        """
        Compare brand landing pages vs competitor landing pages.
        
        Returns comparison insights.
        """
        comparison = {
            "brand_patterns": self._aggregate_lp_patterns(brand_lps),
            "competitor_patterns": self._aggregate_lp_patterns(competitor_lps),
            "differences": [],
            "opportunities": []
        }
        
        # Generate comparison insights with LLM
        prompt = f"""Compare these landing page patterns:

BRAND:
{comparison['brand_patterns']}

COMPETITORS:
{comparison['competitor_patterns']}

Identify:
1. Key differences in approach
2. What competitors do better
3. Opportunities for the brand
4. Best practices to adopt

Return JSON:
{{
    "key_differences": ["difference 1", "difference 2"],
    "competitor_advantages": ["what they do better"],
    "brand_opportunities": ["opportunities to improve"],
    "best_practices_to_adopt": ["specific tactics to try"]
}}"""

        try:
            insights = await self.llm.complete_json(prompt=prompt, temperature=0.4)
            comparison.update(insights)
        except:
            pass
        
        return comparison
    
    def _aggregate_lp_patterns(self, lps: List[Dict]) -> Dict[str, Any]:
        """Aggregate patterns across multiple landing pages."""
        patterns = {
            "headlines": [],
            "ctas": [],
            "has_video_count": 0,
            "has_form_count": 0,
            "has_testimonials_count": 0,
            "social_proof_types": [],
            "tones": []
        }
        
        for lp in lps:
            if lp.get("main_headline"):
                patterns["headlines"].append(lp["main_headline"])
            if lp.get("primary_cta"):
                patterns["ctas"].append(lp["primary_cta"])
            if lp.get("has_video"):
                patterns["has_video_count"] += 1
            if lp.get("has_form"):
                patterns["has_form_count"] += 1
            if lp.get("has_testimonials"):
                patterns["has_testimonials_count"] += 1
            if lp.get("social_proof"):
                patterns["social_proof_types"].extend(lp["social_proof"])
            if lp.get("tone"):
                patterns["tones"].append(lp["tone"])
        
        return patterns




