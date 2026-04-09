"""
Keyword Generator Service - Generates search queries for both research tracks.
"""

from typing import Dict, Any, List

from .llm.client import get_llm_client
from .llm.prompts import KEYWORD_GENERATION_SYSTEM, KEYWORD_GENERATION_PROMPT


class KeywordGeneratorService:
    """Service for generating search queries and identifying communities."""
    
    def __init__(self):
        self.llm = get_llm_client()
    
    async def generate(
        self,
        brand_name: str,
        sector: str,
        vertical: str,
        products: List[str],
        target_audience: str
    ) -> Dict[str, Any]:
        """
        Generate search queries for both tracks.
        
        Track 1: Brand Mentions - Find discussions about the brand
        Track 2: Segment Research - Find discussions about the market/problem
        
        Args:
            brand_name: Name of the brand
            sector: Industry sector
            vertical: Specific vertical
            products: List of products/services
            target_audience: Description of target audience
            
        Returns:
            Dict with brand_queries and segment_queries
        """
        prompt = KEYWORD_GENERATION_PROMPT.format(
            brand_name=brand_name,
            sector=sector or "Unknown",
            vertical=vertical or "Unknown",
            products=", ".join(products) if products else "Unknown",
            target_audience=target_audience or "Unknown"
        )
        
        result = await self.llm.complete_json(
            prompt=prompt,
            system_prompt=KEYWORD_GENERATION_SYSTEM,
            temperature=0.5
        )
        
        # Validate and clean up the result
        result = self._validate_queries(result, brand_name)
        
        return result
    
    def _validate_queries(self, queries: Dict[str, Any], brand_name: str) -> Dict[str, Any]:
        """Validate and ensure all required query fields exist."""
        
        # Handle None input
        if queries is None:
            queries = {}
        
        # Ensure brand_queries structure
        if "brand_queries" not in queries:
            queries["brand_queries"] = {}
        
        brand_q = queries["brand_queries"]
        
        # Default brand queries if missing
        defaults = {
            "reddit": [f'"{brand_name}"', f"{brand_name} review", f"{brand_name} experience", f"{brand_name} worth it"],
            "twitter": [brand_name, f"#{brand_name.replace(' ', '')}", f"tried {brand_name}"],
            "tiktok": [f"#{brand_name.replace(' ', '').lower()}", f"#{brand_name.replace(' ', '').lower()}review"],
            "instagram": [brand_name.replace(' ', '').lower(), f"#{brand_name.replace(' ', '').lower()}"],
            "amazon": [brand_name],
            "google": [f"{brand_name} reviews", f"{brand_name} reddit", f"{brand_name} trustpilot"],
            "trustpilot": [brand_name],
            "news": [f"{brand_name} news", f"{brand_name} launch"]
        }
        
        for key, default in defaults.items():
            if key not in brand_q or not brand_q[key]:
                brand_q[key] = default
        
        # Ensure segment_queries structure
        if "segment_queries" not in queries:
            queries["segment_queries"] = {}
        
        segment_q = queries["segment_queries"]
        
        # Ensure all segment query fields exist (including new ones)
        segment_defaults = {
            "subreddits": [],
            "reddit_searches": [],  # NEW - general problem searches for Reddit
            "twitter_hashtags": [],
            "twitter_problem_searches": [],
            "tiktok_hashtags": [],
            "instagram_hashtags": [],
            "forums": [],
            "keywords": [],
            "problems": [],
            "solution_journey": [],
            "amazon_products": [],
            "google_business": [],
            "quora_questions": []  # NEW - questions for Quora
        }
        
        for key, default in segment_defaults.items():
            if key not in segment_q:
                segment_q[key] = default
        
        return queries
    
    async def generate_additional_queries(
        self,
        base_queries: Dict[str, Any],
        discovered_topics: List[str]
    ) -> Dict[str, Any]:
        """
        Generate additional queries based on discovered topics.
        
        This can be used iteratively to expand research based on findings.
        
        Args:
            base_queries: Existing queries
            discovered_topics: New topics discovered during research
            
        Returns:
            Updated queries dict
        """
        prompt = f"""Based on these discovered topics from market research:
{discovered_topics}

Generate additional search queries to explore these topics deeper.

Current queries:
{base_queries}

Add NEW queries (don't repeat existing ones) in the same JSON structure:
{{
    "brand_queries": {{}},
    "segment_queries": {{
        "subreddits": [],
        "twitter_hashtags": [],
        "tiktok_hashtags": [],
        "instagram_hashtags": [],
        "forums": [],
        "keywords": []
    }}
}}"""
        
        additional = await self.llm.complete_json(
            prompt=prompt,
            system_prompt=KEYWORD_GENERATION_SYSTEM,
            temperature=0.6
        )
        
        # Merge with base queries
        return self._merge_queries(base_queries, additional)
    
    def _merge_queries(self, base: Dict, additional: Dict) -> Dict:
        """Merge two query dicts, avoiding duplicates."""
        result = {
            "brand_queries": {},
            "segment_queries": {}
        }
        
        # Merge brand queries
        for key in set(list(base.get("brand_queries", {}).keys()) + 
                       list(additional.get("brand_queries", {}).keys())):
            base_list = base.get("brand_queries", {}).get(key, [])
            add_list = additional.get("brand_queries", {}).get(key, [])
            result["brand_queries"][key] = list(set(base_list + add_list))
        
        # Merge segment queries
        for key in set(list(base.get("segment_queries", {}).keys()) + 
                       list(additional.get("segment_queries", {}).keys())):
            base_list = base.get("segment_queries", {}).get(key, [])
            add_list = additional.get("segment_queries", {}).get(key, [])
            result["segment_queries"][key] = list(set(base_list + add_list))
        
        return result

