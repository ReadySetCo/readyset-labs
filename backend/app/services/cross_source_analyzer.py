"""
Cross-Source Analyzer - Validates insights across multiple data sources.
Creates confidence scores by cross-referencing pain points, themes, and sentiments.
"""

import re
import json
import asyncio
from collections import Counter, defaultdict
from typing import Dict, Any, List, Optional, Tuple
import google.generativeai as genai

from ..config import settings


class CrossSourceAnalyzer:
    """
    Analyzes and validates insights across multiple data sources.
    Provides:
    - Pain point validation with source count
    - Engagement-weighted confidence scores
    - Messaging gap analysis
    - Competitor intelligence aggregation
    """
    
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if self.api_key:
            genai.configure(api_key=self.api_key)
        self.model_id = "models/gemini-3-flash-preview"
    
    async def analyze_cross_source(
        self,
        all_insights: Dict[str, Any],
        brand_name: str = ""
    ) -> Dict[str, Any]:
        """
        Cross-reference insights from all sources.
        
        Args:
            all_insights: Dict containing insights from each source type
                {
                    "youtube_insights": {...},
                    "twitter_insights": {...},
                    "reddit_insights": {...},
                    "review_insights": {...},
                    "ad_insights": {...}
                }
            brand_name: Brand name for context
            
        Returns:
            Validated and confidence-scored insights
        """
        # Step 1: Extract all pain points with source tracking
        pain_points = self._extract_all_pain_points(all_insights)
        
        # Step 2: Validate pain points (count sources)
        validated_pain_points = self._validate_pain_points(pain_points)
        
        # Step 3: Extract all themes/topics
        themes = self._extract_all_themes(all_insights)
        
        # Step 4: Messaging gap analysis
        messaging_gaps = self._analyze_messaging_gaps(all_insights)
        
        # Step 5: Competitor intelligence aggregation
        competitor_intel = self._aggregate_competitor_intel(all_insights)
        
        # Step 6: Overall sentiment across sources
        cross_sentiment = self._calculate_cross_sentiment(all_insights)
        
        # Step 7: LLM synthesis for high-level insights
        llm_synthesis = {}
        if self.api_key:
            try:
                llm_synthesis = await self._synthesize_with_llm(all_insights, brand_name)
            except Exception as e:
                print(f"       [CrossSource] LLM synthesis error: {e}")
        
        return {
            "validated_pain_points": validated_pain_points,
            "validated_themes": themes,
            "messaging_gaps": messaging_gaps,
            "competitor_intelligence": competitor_intel,
            "cross_source_sentiment": cross_sentiment,
            # LLM-enhanced
            "key_opportunities": llm_synthesis.get("key_opportunities", []),
            "strategic_recommendations": llm_synthesis.get("strategic_recommendations", []),
            "ad_angle_suggestions": llm_synthesis.get("ad_angle_suggestions", []),
            "strongest_proof_points": llm_synthesis.get("strongest_proof_points", [])
        }
    
    def _extract_all_pain_points(self, all_insights: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract pain points from all sources with tracking."""
        pain_points = []
        
        # YouTube insights
        yt = all_insights.get("youtube_insights", {})
        for pp in yt.get("pain_points", []):
            pain_points.append({
                "text": pp if isinstance(pp, str) else pp.get("text", str(pp)),
                "source": "youtube",
                "engagement": yt.get("total_analyzed", 0)
            })
        
        # Twitter insights
        tw = all_insights.get("twitter_insights", {})
        for topic, count in tw.get("topics", {}).items():
            if topic in ["problem", "support", "pricing"]:
                pain_points.append({
                    "text": f"Issues with {topic}",
                    "source": "twitter",
                    "engagement": count * 10  # Weight by mention count
                })
        
        # Reddit insights
        rd = all_insights.get("reddit_insights", {})
        for pp in rd.get("pain_points", []):
            pain_points.append({
                "text": pp if isinstance(pp, str) else pp.get("text", str(pp)),
                "source": "reddit",
                "engagement": 50  # Base engagement for Reddit
            })
        for wish in rd.get("wish_patterns", []):
            pain_points.append({
                "text": wish.get("quote", str(wish)) if isinstance(wish, dict) else str(wish),
                "source": "reddit_wish",
                "engagement": wish.get("score", 10) if isinstance(wish, dict) else 10
            })
        for complaint in rd.get("recurring_complaints", []):
            pain_points.append({
                "text": complaint if isinstance(complaint, str) else str(complaint),
                "source": "reddit",
                "engagement": 30
            })
        
        # Review insights
        rv = all_insights.get("review_insights", {})
        for complaint in rv.get("top_complaints", []):
            pain_points.append({
                "text": complaint.get("quote", str(complaint))[:100] if isinstance(complaint, dict) else str(complaint)[:100],
                "source": "reviews",
                "engagement": 20
            })
        for db in rv.get("deal_breakers", []):
            pain_points.append({
                "text": db if isinstance(db, str) else str(db),
                "source": "reviews",
                "engagement": 50  # Deal breakers are high impact
            })
        
        return pain_points
    
    def _validate_pain_points(self, pain_points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate pain points by counting sources and calculating confidence."""
        # Group similar pain points
        grouped = defaultdict(lambda: {"sources": set(), "total_engagement": 0, "mentions": []})
        
        for pp in pain_points:
            text = pp["text"].lower()[:50]  # Normalize for grouping
            key = self._normalize_text(text)
            
            grouped[key]["sources"].add(pp["source"])
            grouped[key]["total_engagement"] += pp.get("engagement", 0)
            grouped[key]["mentions"].append(pp["text"])
        
        # Calculate confidence scores
        validated = []
        for key, data in grouped.items():
            source_count = len(data["sources"])
            engagement = data["total_engagement"]
            
            # Confidence formula: sources * 20 + log(engagement) * 10
            import math
            confidence = min(100, (source_count * 20) + (math.log(engagement + 1) * 10))
            
            validated.append({
                "pain_point": data["mentions"][0],  # Use first mention as representative
                "source_count": source_count,
                "sources": list(data["sources"]),
                "total_engagement": engagement,
                "confidence_score": round(confidence, 1),
                "validation_status": "Validated" if source_count >= 2 else "Single-Source"
            })
        
        # Sort by confidence
        return sorted(validated, key=lambda x: x["confidence_score"], reverse=True)[:15]
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        # Remove common words and punctuation
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "it", "that", "this", "with", "for", "to", "of"}
        words = re.findall(r'\w+', text.lower())
        filtered = [w for w in words if w not in stop_words and len(w) > 2]
        return " ".join(sorted(filtered[:5]))
    
    def _extract_all_themes(self, all_insights: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract and validate themes across sources."""
        themes = Counter()
        theme_sources = defaultdict(set)
        
        # Twitter topics/hashtags
        tw = all_insights.get("twitter_insights", {})
        for topic in tw.get("topics", {}).keys():
            themes[topic] += 1
            theme_sources[topic].add("twitter")
        for tag in list(tw.get("hashtags", {}).keys())[:10]:
            themes[tag] += 1
            theme_sources[tag].add("twitter")
        
        # Reddit themes
        rd = all_insights.get("reddit_insights", {})
        for theme in rd.get("recurring_themes", []) if isinstance(rd.get("recurring_themes"), list) else []:
            theme_str = theme if isinstance(theme, str) else str(theme)
            themes[theme_str] += 1
            theme_sources[theme_str].add("reddit")
        
        # Review themes
        rv = all_insights.get("review_insights", {})
        for theme in rv.get("recurring_themes", []) if isinstance(rv.get("recurring_themes"), list) else []:
            theme_str = theme if isinstance(theme, str) else str(theme)
            themes[theme_str] += 1
            theme_sources[theme_str].add("reviews")
        
        result = []
        for theme, count in themes.most_common(12):
            result.append({
                "theme": theme,
                "mention_count": count,
                "sources": list(theme_sources[theme]),
                "cross_validated": len(theme_sources[theme]) >= 2
            })
        
        return result
    
    def _analyze_messaging_gaps(self, all_insights: Dict[str, Any]) -> Dict[str, Any]:
        """Identify messaging gaps between ads and customer voice."""
        ad_insights = all_insights.get("ad_insights", {})
        customer_insights = {
            **all_insights.get("reddit_insights", {}),
            **all_insights.get("review_insights", {}),
            **all_insights.get("youtube_insights", {})
        }
        
        # What ads emphasize (if available)
        ad_themes = set()
        if ad_insights:
            for theme in ad_insights.get("key_messages", []):
                ad_themes.add(theme.lower() if isinstance(theme, str) else "")
        
        # What customers discuss
        customer_themes = set()
        for pp in customer_insights.get("pain_points", []):
            customer_themes.add(str(pp).lower()[:30])
        for theme in customer_insights.get("recurring_themes", []):
            customer_themes.add(str(theme).lower()[:30])
        
        return {
            "promoted_but_not_valued": list(ad_themes - customer_themes)[:5],
            "valued_but_not_promoted": list(customer_themes - ad_themes)[:5],
            "aligned_messaging": list(ad_themes & customer_themes)[:5]
        }
    
    def _aggregate_competitor_intel(self, all_insights: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Aggregate competitor mentions across sources."""
        competitors = Counter()
        competitor_context = defaultdict(list)
        
        # Reddit competitor mentions
        rd = all_insights.get("reddit_insights", {})
        for comp in rd.get("competitor_mentions", []):
            if isinstance(comp, dict):
                name = comp.get("competitor", "")
                competitors[name] += comp.get("mention_count", 1)
                if comp.get("sample_context"):
                    competitor_context[name].append(comp["sample_context"])
            elif isinstance(comp, str):
                competitors[comp] += 1
        
        # Twitter influencer mentions might include competitors
        tw = all_insights.get("twitter_insights", {})
        for inf in tw.get("influencer_mentions", []):
            if isinstance(inf, dict) and not inf.get("is_content_creator"):
                name = inf.get("username", "")
                competitors[name] += inf.get("mention_count", 1)
        
        result = []
        for name, count in competitors.most_common(8):
            if name and count > 1:
                result.append({
                    "competitor": name,
                    "total_mentions": count,
                    "context_samples": competitor_context.get(name, [])[:2]
                })
        
        return result
    
    def _calculate_cross_sentiment(self, all_insights: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate weighted sentiment across all sources."""
        sentiments = []
        
        for source_key in ["youtube_insights", "twitter_insights", "reddit_insights", "review_insights"]:
            insight = all_insights.get(source_key, {})
            
            sentiment = insight.get("sentiment") or insight.get("overall_sentiment") or insight.get("sentiment_summary", {})
            if isinstance(sentiment, dict):
                overall = sentiment.get("overall", "Neutral")
                positive = sentiment.get("positive_pct", 50)
            elif isinstance(sentiment, str):
                overall = sentiment
                positive = 70 if "pos" in overall.lower() else 30 if "neg" in overall.lower() else 50
            else:
                continue
            
            sentiments.append({
                "source": source_key.replace("_insights", ""),
                "overall": overall,
                "positive_pct": positive
            })
        
        if not sentiments:
            return {"overall": "Unknown", "by_source": []}
        
        avg_positive = sum(s["positive_pct"] for s in sentiments) / len(sentiments)
        
        return {
            "overall": "Positive" if avg_positive >= 60 else "Negative" if avg_positive <= 40 else "Mixed",
            "avg_positive_pct": round(avg_positive, 1),
            "by_source": sentiments
        }
    
    async def _synthesize_with_llm(
        self, 
        all_insights: Dict[str, Any],
        brand_name: str
    ) -> Dict[str, Any]:
        """Use LLM to synthesize cross-source insights."""
        # Prepare summary of insights
        summary_parts = []
        
        for source, insights in all_insights.items():
            if insights and isinstance(insights, dict):
                summary_parts.append(f"## {source.replace('_', ' ').title()}")
                for key, value in list(insights.items())[:5]:
                    if value and not isinstance(value, (list, dict)) or (isinstance(value, list) and value):
                        summary_parts.append(f"- {key}: {str(value)[:150]}")
        
        insights_summary = "\n".join(summary_parts[:40])
        
        prompt = f"""Based on cross-source research{f' for {brand_name}' if brand_name else ''}, synthesize actionable insights.

CROSS-SOURCE DATA:
{insights_summary}

Return a JSON object with:

## OPPORTUNITIES
- "key_opportunities": [list of 3-5 high-confidence opportunities backed by multiple sources]

## STRATEGIC RECOMMENDATIONS
- "strategic_recommendations": [list of 3-5 specific actions based on the data]

## AD ANGLES
- "ad_angle_suggestions": [list of 5-7 ad angles that would resonate, based on validated pain points and customer language]

## PROOF POINTS
- "strongest_proof_points": [list of 3-5 claims that can be backed by customer testimonials/data from multiple sources]

Return ONLY valid JSON."""

        try:
            model = genai.GenerativeModel(self.model_id)
            response = await asyncio.wait_for(
                asyncio.to_thread(model.generate_content, prompt),
                timeout=60.0
            )
            return self._extract_json(response.text) or {}
        except Exception as e:
            print(f"       [CrossSource LLM] Error: {e}")
            return {}
    
    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from response text."""
        if not text:
            return None
        try:
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                return json.loads(match.group(0))
        except:
            pass
        try:
            clean = text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean)
        except:
            pass
        return None
