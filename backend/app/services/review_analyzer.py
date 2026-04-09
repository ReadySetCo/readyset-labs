"""
Review Analyzer - Deep analysis of reviews from Trustpilot, Google, App Store.
Extracts rating distributions, phrases by rating, sentiment trends, and complaints.
"""

import re
import json
import asyncio
from collections import Counter
from typing import Dict, Any, List, Optional
import google.generativeai as genai

from ..config import settings


class ReviewAnalyzer:
    """
    Analyzes customer reviews for advertising insights.
    Extracts:
    - Star rating distribution
    - Common phrases per rating level
    - Time-based sentiment trends
    - Top complaints and praises by frequency
    - Feature requests and bug reports
    """
    
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if self.api_key:
            genai.configure(api_key=self.api_key)
        self.model_id = "models/gemini-3-flash-preview"
    
    async def analyze_reviews(
        self,
        reviews: List[Dict[str, Any]],
        brand_name: str = "",
        source_type: str = "reviews"
    ) -> Dict[str, Any]:
        """
        Deep analysis of customer reviews.
        
        Args:
            reviews: List of review dicts with rating, content, etc.
            brand_name: Brand name for context
            source_type: trustpilot, google_reviews, app_store, amazon
            
        Returns:
            Comprehensive review insights
        """
        if not reviews:
            return {"total_analyzed": 0}
        
        # Step 1: Rating distribution
        rating_dist = self._analyze_rating_distribution(reviews)
        
        # Step 2: Phrases by rating
        phrases_by_rating = self._extract_phrases_by_rating(reviews)
        
        # Step 3: Top complaints and praises
        complaints, praises = self._extract_complaints_praises(reviews)
        
        # Step 4: LLM deep analysis
        llm_insights = {}
        if self.api_key and len(reviews) >= 5:
            try:
                llm_insights = await self._analyze_with_llm(reviews[:40], brand_name, source_type)
            except Exception as e:
                print(f"       [Reviews] LLM analysis error: {e}")
        
        return {
            "total_analyzed": len(reviews),
            "source_type": source_type,
            "rating_distribution": rating_dist,
            "avg_rating": self._calculate_avg_rating(reviews),
            "phrases_by_rating": phrases_by_rating,
            "top_complaints": complaints[:10],
            "top_praises": praises[:10],
            "sentiment_summary": self._calculate_sentiment_summary(reviews),
            # LLM-enhanced insights
            "recurring_themes": llm_insights.get("recurring_themes", []),
            "feature_requests": llm_insights.get("feature_requests", []),
            "bug_reports": llm_insights.get("bug_reports", []),
            "competitor_mentions": llm_insights.get("competitor_mentions", []),
            "quotable_reviews": llm_insights.get("quotable_reviews", []),
            "improvement_suggestions": llm_insights.get("improvement_suggestions", []),
            "what_customers_love": llm_insights.get("what_customers_love", []),
            "deal_breakers": llm_insights.get("deal_breakers", [])
        }
    
    def _analyze_rating_distribution(self, reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze distribution of ratings."""
        ratings = Counter()
        
        for review in reviews:
            rating = review.get("rating")
            if rating is not None:
                # Normalize to 1-5 scale
                if isinstance(rating, (int, float)):
                    if rating <= 5:
                        normalized = round(rating)
                    else:
                        # Assume 10-point scale
                        normalized = round(rating / 2)
                    ratings[normalized] += 1
        
        total = sum(ratings.values()) or 1
        
        return {
            "5_star": {"count": ratings[5], "pct": round(ratings[5] / total * 100, 1)},
            "4_star": {"count": ratings[4], "pct": round(ratings[4] / total * 100, 1)},
            "3_star": {"count": ratings[3], "pct": round(ratings[3] / total * 100, 1)},
            "2_star": {"count": ratings[2], "pct": round(ratings[2] / total * 100, 1)},
            "1_star": {"count": ratings[1], "pct": round(ratings[1] / total * 100, 1)},
            "positive_pct": round((ratings[4] + ratings[5]) / total * 100, 1),
            "negative_pct": round((ratings[1] + ratings[2]) / total * 100, 1)
        }
    
    def _calculate_avg_rating(self, reviews: List[Dict[str, Any]]) -> float:
        """Calculate average rating."""
        ratings = []
        for review in reviews:
            rating = review.get("rating")
            if rating is not None and isinstance(rating, (int, float)):
                if rating <= 5:
                    ratings.append(rating)
                else:
                    ratings.append(rating / 2)
        
        return round(sum(ratings) / len(ratings), 2) if ratings else 0
    
    def _extract_phrases_by_rating(self, reviews: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Extract common phrases grouped by rating."""
        high_rating_phrases = Counter()
        low_rating_phrases = Counter()
        
        # Common phrase patterns
        phrase_patterns = [
            r'really (\w+)',
            r'very (\w+)',
            r'so (\w+)',
            r'absolutely (\w+)',
            r'(\w+) customer service',
            r'(\w+) quality',
            r'(\w+) experience',
            r'would (\w+) recommend',
            r"(?:doesn't|don't|didn't) (\w+)",
            r'(\w+) issues?',
            r'(\w+) problems?'
        ]
        
        for review in reviews:
            rating = review.get("rating", 3)
            content = review.get("content", "").lower()
            
            if isinstance(rating, (int, float)):
                if rating > 5:
                    rating = rating / 2
                
                for pattern in phrase_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        if len(match) > 2:
                            if rating >= 4:
                                high_rating_phrases[match] += 1
                            elif rating <= 2:
                                low_rating_phrases[match] += 1
        
        return {
            "high_rating_phrases": [phrase for phrase, _ in high_rating_phrases.most_common(10)],
            "low_rating_phrases": [phrase for phrase, _ in low_rating_phrases.most_common(10)]
        }
    
    def _extract_complaints_praises(
        self, 
        reviews: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Extract top complaints and praises."""
        complaints = []
        praises = []
        
        complaint_keywords = ["problem", "issue", "terrible", "awful", "disappointed", 
                            "broken", "waste", "scam", "refund", "worst", "never"]
        praise_keywords = ["love", "amazing", "excellent", "perfect", "best", 
                          "fantastic", "recommend", "great", "awesome", "helpful"]
        
        for review in reviews:
            content = review.get("content", "").lower()
            rating = review.get("rating", 3)
            
            if isinstance(rating, (int, float)):
                if rating > 5:
                    rating = rating / 2
            
            # Extract complaints from low-rated reviews
            if rating is not None and isinstance(rating, (int, float)) and rating <= 2:
                for kw in complaint_keywords:
                    if kw in content:
                        complaints.append({
                            "quote": review.get("content", "")[:200],
                            "rating": rating,
                            "keyword": kw
                        })
                        break
            
            # Extract praises from high-rated reviews
            elif rating is not None and isinstance(rating, (int, float)) and rating >= 4:
                for kw in praise_keywords:
                    if kw in content:
                        praises.append({
                            "quote": review.get("content", "")[:200],
                            "rating": rating,
                            "keyword": kw
                        })
                        break
        
        return complaints[:15], praises[:15]
    
    def _calculate_sentiment_summary(self, reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate overall sentiment summary."""
        positive, negative, neutral = 0, 0, 0
        
        for review in reviews:
            rating = review.get("rating", 3)
            if isinstance(rating, (int, float)):
                if rating > 5:
                    rating = rating / 2
                
                if rating >= 4:
                    positive += 1
                elif rating <= 2:
                    negative += 1
                else:
                    neutral += 1
        
        total = len(reviews) or 1
        return {
            "overall": "Positive" if positive > negative else "Negative" if negative > positive else "Mixed",
            "positive_pct": round(positive / total * 100, 1),
            "neutral_pct": round(neutral / total * 100, 1),
            "negative_pct": round(negative / total * 100, 1)
        }
    
    async def _analyze_with_llm(
        self, 
        reviews: List[Dict[str, Any]],
        brand_name: str,
        source_type: str
    ) -> Dict[str, Any]:
        """Use LLM for deep review analysis."""
        reviews_text = []
        for r in reviews[:25]:
            rating = r.get("rating", "?")
            content = r.get("content", "")[:350]
            reviews_text.append(f"[{rating}★] {content}")
        
        reviews_str = "\n---\n".join(reviews_text)
        
        prompt = f"""Analyze these {source_type} reviews{f' for {brand_name}' if brand_name else ''} for advertising insights.

REVIEWS:
{reviews_str}

Return a JSON object with:

## THEMES & PATTERNS
- "recurring_themes": [list of 5-7 most common themes with frequency: "High/Medium/Low"]
- "what_customers_love": [list of 3-5 specific things customers love, with quotes]
- "deal_breakers": [list of 3-5 issues that make customers leave or give bad reviews]

## ISSUES & REQUESTS
- "feature_requests": [list of features users want that don't exist]
- "bug_reports": [list of technical issues mentioned]
- "improvement_suggestions": [list of specific improvements requested]

## COMPETITIVE INTEL
- "competitor_mentions": [any mentions of competitor products/services with context]

## AD-WORTHY CONTENT
- "quotable_reviews": [5-7 reviews that would work great in advertising, with the quote and why it's effective]

Return ONLY valid JSON."""

        try:
            model = genai.GenerativeModel(self.model_id)
            response = await asyncio.wait_for(
                asyncio.to_thread(model.generate_content, prompt),
                timeout=60.0
            )
            return self._extract_json(response.text) or {}
        except Exception as e:
            print(f"       [Review LLM] Error: {e}")
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
    
    async def aggregate_review_insights(
        self,
        analyses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate insights from multiple review sources."""
        total_reviews = 0
        all_complaints = []
        all_praises = []
        all_themes = []
        rating_sum = 0
        rating_count = 0
        
        for analysis in analyses:
            total_reviews += analysis.get("total_analyzed", 0)
            all_complaints.extend(analysis.get("top_complaints", []))
            all_praises.extend(analysis.get("top_praises", []))
            all_themes.extend(analysis.get("recurring_themes", []))
            
            avg = analysis.get("avg_rating", 0)
            if avg > 0:
                rating_sum += avg
                rating_count += 1
        
        return {
            "total_reviews_analyzed": total_reviews,
            "avg_rating_across_sources": round(rating_sum / rating_count, 2) if rating_count else 0,
            "top_complaints": all_complaints[:10],
            "top_praises": all_praises[:10],
            "recurring_themes": list(set(all_themes))[:10]
        }
