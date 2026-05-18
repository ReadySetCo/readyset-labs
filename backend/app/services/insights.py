"""
Insights Generator Service - Generates Creative Dimensions from scraped data.
Enhanced for deeper analysis with competitor insights, verbatim quotes, and actionable recommendations.
"""

import asyncio
from typing import Dict, Any, List
import json

from .llm.client import get_llm_client
from .llm.prompts import INSIGHTS_SYSTEM, INSIGHTS_GENERATION_PROMPT


class InsightsGeneratorService:
    """Service for generating insights and Creative Dimensions from scraped data."""
    
    def __init__(self):
        self.llm = get_llm_client(task_type="strategy")
    
    async def generate(
        self,
        brand_name: str,
        brand_info: Dict[str, Any],
        scraped_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive insights from scraped data.
        
        Args:
            brand_name: Name of the brand
            brand_info: Brand discovery info (sector, vertical, etc.)
            scraped_data: List of all scraped data items
            
        Returns:
            Dict with all insights and Creative Dimensions
        """
        # Separate data by track
        track1_data = [d for d in scraped_data if d.get("track") == 1]
        track2_data = [d for d in scraped_data if d.get("track") == 2]
        
        # Format data for prompt
        track1_formatted = self._format_data_for_prompt(track1_data, "Brand Mentions")
        track2_formatted = self._format_data_for_prompt(track2_data, "Segment Research")
        
        # Generate insights with LLM
        prompt = INSIGHTS_GENERATION_PROMPT.format(
            brand_name=brand_name,
            sector=brand_info.get("sector", "Unknown"),
            vertical=brand_info.get("vertical", "Unknown"),
            track1_data=track1_formatted,
            track2_data=track2_formatted
        )
        
        try:
            # 300s timeout: the insights prompt is the largest one in the pipeline
            # (full track1 + track2 data, ~20-30K input tokens) and gpt-5.4 strategy
            # calls regularly take 40-90s. 120s was tight for Gemini and insufficient
            # for gpt-5.4 — observed in benchmark session 139.
            # max_tokens=16000: the insights response is a large JSON with
            # icps, pain_points, messaging_angles, verbatim_quotes, objections,
            # plus the 4 strategic-angle arrays. gpt-5.x reasoning tokens
            # count against max_completion_tokens, so 8192 default was getting
            # truncated and producing invalid JSON (None from complete_json).
            insights = await asyncio.wait_for(
                self.llm.complete_json(
                    prompt=prompt,
                    system_prompt=INSIGHTS_SYSTEM,
                    temperature=0.4,
                    max_tokens=16000,
                ),
                timeout=300.0
            )
        except asyncio.TimeoutError:
            print("    [!] Insights LLM timeout after 300s, using defaults")
            insights = {}
        except Exception as e:
            import traceback
            print(f"    [!] Insights LLM error: {type(e).__name__}: {e}")
            print(f"    [!] Traceback:\n{traceback.format_exc()}")
            insights = {}

        # complete_json() returns None on JSON parse failure (e.g. gpt-5.4
        # occasionally emits truncated markdown-wrapped JSON). Normalise to
        # an empty dict so _validate_insights can populate defaults rather
        # than crashing on `key not in None`.
        if not isinstance(insights, dict):
            print(f"    [!] Insights LLM returned non-dict ({type(insights).__name__}), using defaults")
            insights = {}

        # Ensure all required fields exist
        insights = self._validate_insights(insights)
        
        # Generate full markdown report
        insights["full_report"] = self._generate_markdown_report(
            brand_name=brand_name,
            brand_info=brand_info,
            insights=insights,
            data_counts={
                "track1": len(track1_data),
                "track2": len(track2_data),
                "by_source": self._count_by_source(scraped_data),
                "by_mention_type": self._count_by_mention_type(scraped_data)
            }
        )
        
        return insights
    
    def _format_data_for_prompt(
        self, 
        data: List[Dict[str, Any]], 
        track_name: str
    ) -> str:
        """Format scraped data for the prompt with better structure."""
        if not data:
            return f"No {track_name} data collected."
        
        # Group by source and mention type
        by_source: Dict[str, List] = {}
        for item in data:
            source = item.get("source_type", "unknown")
            mention_type = item.get("mention_type", "unknown")
            key = f"{source}_{mention_type}"
            if key not in by_source:
                by_source[key] = []
            by_source[key].append(item)
        
        formatted_parts = []
        
        for key, items in by_source.items():
            source, mention_type = key.rsplit("_", 1)
            formatted_parts.append(f"\n### {source.upper()} - {mention_type} ({len(items)} items)")
            
            for i, item in enumerate(items[:40]):  # Increased from 15 to 40 per source
                title = item.get("title", "")
                content = (item.get("content") or "")[:800]
                rating = item.get("rating")
                likes = item.get("likes")
                source_url = item.get("source_url", "")
                sentiment = item.get("sentiment")
                sentiment_score = item.get("sentiment_score")

                entry = f"\n[{i+1}]"
                if title:
                    entry += f" **{title}**"
                if rating:
                    entry += f" (Rating: {rating}/5)"
                if likes:
                    entry += f" ({likes} likes)"
                if sentiment and sentiment_score is not None:
                    entry += f" [Sentiment: {sentiment} ({sentiment_score:+.2f})]"
                entry += f"\n{content}"
                if source_url:
                    entry += f"\nSource: {source_url[:50]}..."

                formatted_parts.append(entry)
        
        return "\n".join(formatted_parts)
    
    def _count_by_source(self, data: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count items by source type."""
        counts: Dict[str, int] = {}
        for item in data:
            source = item.get("source_type", "unknown")
            counts[source] = counts.get(source, 0) + 1
        return counts
    
    def _count_by_mention_type(self, data: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count items by mention type."""
        counts: Dict[str, int] = {}
        for item in data:
            mention_type = item.get("mention_type", "unknown")
            counts[mention_type] = counts.get(mention_type, 0) + 1
        return counts
    
    def _validate_insights(self, insights: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure all required fields exist in insights."""
        defaults = {
            "brand_summary": "",
            "sentiment_score": None,
            "total_mentions": 0,
            "top_positives": [],
            "top_negatives": [],
            "competitors_mentioned": [],
            "market_pain_points": [],
            "customer_language": [],
            "customer_desires": [],
            "trending_topics": [],
            "icps": [],
            "pain_points": [],
            "value_props": [],
            "messaging_angles": [],
            "tone_emotions": [],
            "content_insights": [],
            # New enhanced fields
            "competitor_analysis": {},
            "purchase_triggers": [],
            "objections": [],
            "decision_factors": [],
            "verbatim_quotes": [],
            "content_opportunities": [],
            "recommended_hooks": [],
            "price_sensitivity": {},
            "feature_requests": []
        }
        
        for key, default in defaults.items():
            if key not in insights or insights[key] is None:
                insights[key] = default
        
        return insights
    
    def _generate_markdown_report(
        self,
        brand_name: str,
        brand_info: Dict[str, Any],
        insights: Dict[str, Any],
        data_counts: Dict[str, Any]
    ) -> str:
        """Generate a comprehensive markdown report with all insights."""
        
        report = f"""# Brand Intelligence Report: {brand_name}

## Executive Summary
- **Sector:** {brand_info.get('sector', 'Unknown')}
- **Vertical:** {brand_info.get('vertical', 'Unknown')}
- **Sentiment Score:** {insights.get('sentiment_score', 'N/A')}/5
- **Total Data Points:** {data_counts.get('track1', 0) + data_counts.get('track2', 0)}

{insights.get('brand_summary', 'No summary available.')}

---

## Data Sources Summary

### By Source
| Source | Items |
|--------|-------|
"""
        for source, count in data_counts.get("by_source", {}).items():
            report += f"| {source.capitalize()} | {count} |\n"
        
        report += """
### By Mention Type
| Type | Items |
|------|-------|
"""
        for mtype, count in data_counts.get("by_mention_type", {}).items():
            report += f"| {mtype.replace('_', ' ').title()} | {count} |\n"
        
        report += """
---

## Track 1: Brand Perception

### What People Love
"""
        for item in insights.get("top_positives", []):
            report += f"- {item}\n"
        
        report += """
### Common Concerns
"""
        for item in insights.get("top_negatives", []):
            report += f"- {item}\n"
        
        report += """
### Competitors Mentioned
"""
        for item in insights.get("competitors_mentioned", []):
            report += f"- {item}\n"
        
        # Competitor Analysis Section
        comp_analysis = insights.get("competitor_analysis", {})
        if comp_analysis:
            report += f"""
---

## Competitive Analysis

**Main Competitors:** {', '.join(comp_analysis.get('main_competitors', []))}

### Our Advantages
"""
            for item in comp_analysis.get("our_advantages", []):
                report += f"- {item}\n"
            
            report += """
### Their Advantages
"""
            for item in comp_analysis.get("their_advantages", []):
                report += f"- {item}\n"
            
            if comp_analysis.get("positioning_opportunity"):
                report += f"""
### Positioning Opportunity
{comp_analysis.get('positioning_opportunity')}
"""
        
        report += """
---

## Track 2: Market & Segment Research

### Market Pain Points
"""
        for item in insights.get("market_pain_points", []):
            report += f"- {item}\n"
        
        report += """
### Customer Language (Verbatims)
"""
        for item in insights.get("customer_language", []):
            report += f'- "{item}"\n'
        
        report += """
### What Customers Want
"""
        for item in insights.get("customer_desires", []):
            report += f"- {item}\n"
        
        report += """
### Trending Topics
"""
        for item in insights.get("trending_topics", []):
            report += f"- {item}\n"
        
        report += """
---

## Creative Dimensions

### ICPs (Ideal Customer Profiles)
"""
        for icp in insights.get("icps", []):
            if isinstance(icp, dict):
                report += f"""
**{icp.get('name', 'Unknown')}**
- {icp.get('description', '')}
- Age: {icp.get('age_range', 'N/A')}
- Characteristics: {', '.join(icp.get('characteristics', []))}
- Pain Points: {', '.join(icp.get('pain_points', []))}
- Motivations: {', '.join(icp.get('motivations', []))}
"""
            else:
                report += f"- {icp}\n"
        
        report += """
### Pain Points (for Ad Messaging)
"""
        for item in insights.get("pain_points", []):
            report += f"- {item}\n"
        
        report += """
### Value Props (to Highlight)
"""
        for item in insights.get("value_props", []):
            report += f"- {item}\n"
        
        report += """
### Messaging Angles
"""
        for angle in insights.get("messaging_angles", []):
            if isinstance(angle, dict):
                report += f"""
**{angle.get('name', 'Unknown')}**
- Hook: "{angle.get('hook', '')}"
- {angle.get('description', '')}
- Evidence: {angle.get('supporting_evidence', 'N/A')}
"""
            else:
                report += f"- {angle}\n"
        
        report += """
### Tone/Emotion Journey
"""
        for item in insights.get("tone_emotions", []):
            report += f"- {item}\n"
        
        # New Enhanced Sections
        report += """
---

## Purchase Psychology

### Purchase Triggers
What makes people decide to buy:
"""
        for item in insights.get("purchase_triggers", []):
            report += f"- {item}\n"
        
        report += """
### Objections to Address
"""
        for obj in insights.get("objections", []):
            if isinstance(obj, dict):
                report += f"""
- **{obj.get('objection', '')}** ({obj.get('frequency', 'unknown')} frequency)
  - Counter: {obj.get('counter_messaging', 'N/A')}
"""
            else:
                report += f"- {obj}\n"
        
        report += """
### Decision Factors
Key factors people consider (ranked):
"""
        for i, item in enumerate(insights.get("decision_factors", []), 1):
            report += f"{i}. {item}\n"
        
        # Price Sensitivity
        price = insights.get("price_sensitivity", {})
        if price:
            report += f"""
### Price Sensitivity
- **Overall Sensitivity:** {price.get('overall_sensitivity', 'Unknown')}
- **Value Perception:** {price.get('value_perception', 'Unknown')}
- **Price Complaints:** {', '.join(price.get('price_complaints', []))}
"""
        
        report += """
---

## Verbatim Quotes (for Ads)
Real quotes from customers:
"""
        for quote in insights.get("verbatim_quotes", []):
            if isinstance(quote, dict):
                report += f"""
> "{quote.get('quote', '')}"
> - Context: {quote.get('context', '')}
> - Use: {quote.get('use_case', '')}

"""
            else:
                report += f'> "{quote}"\n\n'
        
        report += """
---

## Recommended Hooks
"""
        for hook in insights.get("recommended_hooks", []):
            if isinstance(hook, dict):
                report += f"""
**{hook.get('type', 'Unknown').upper()}:** "{hook.get('hook', '')}"
- Target: {hook.get('target_persona', 'General')}
- Reasoning: {hook.get('reasoning', '')}

"""
            else:
                report += f"- {hook}\n"
        
        report += """
---

## Content Opportunities
"""
        for item in insights.get("content_opportunities", []):
            report += f"- {item}\n"
        
        report += """
### Feature Requests
What users are asking for:
"""
        for item in insights.get("feature_requests", []):
            report += f"- {item}\n"
        
        report += """
---

*Report generated by Brand Intelligence Scraper*
*Powered by GPT-5.1 + Firecrawl*
"""
        
        return report
    
    async def analyze_single_text(self, text: str) -> Dict[str, Any]:
        """
        Analyze a single piece of text for quick insights.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict with sentiment and extracted pain points
        """
        prompt = f"""Analyze this customer text and extract:
1. Sentiment (positive/negative/neutral)
2. Any pain points mentioned
3. Any product features praised or criticized

Text: {text}

Return JSON:
{{
    "sentiment": "positive/negative/neutral",
    "sentiment_score": 0-5,
    "pain_points": [],
    "praises": [],
    "criticisms": []
}}"""
        
        return await self.llm.complete_json(prompt=prompt, temperature=0.3)
