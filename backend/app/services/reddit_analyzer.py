"""
Reddit Analyzer - Deep analysis of Reddit threads and comments.
Extracts sentiment by subreddit, top comments, complaints/praises, competitor mentions, and wish patterns.
"""

import re
import json
import asyncio
from collections import Counter
from typing import Dict, Any, List, Optional
import google.generativeai as genai

from ..config import settings


class RedditAnalyzer:
    """
    Analyzes Reddit content for advertising insights.
    Extracts:
    - Sentiment by subreddit
    - Top upvoted comments as verbatims
    - Recurring complaints and praises
    - Competitor mentions with context
    - "I wish..." and "I hate..." patterns
    """
    
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if self.api_key:
            genai.configure(api_key=self.api_key)
        self.model_id = "models/gemini-3-flash-preview"
    
    async def analyze_reddit_content(
        self,
        posts: List[Dict[str, Any]],
        brand_name: str = ""
    ) -> Dict[str, Any]:
        """
        Deep analysis of Reddit posts and comments.
        
        Args:
            posts: List of Reddit post/comment dicts
            brand_name: Brand name for context
            
        Returns:
            Comprehensive Reddit insights
        """
        if not posts:
            return {"total_analyzed": 0}
        
        # Step 1: Sentiment by subreddit
        subreddit_sentiment = self._analyze_by_subreddit(posts)
        
        # Step 2: Extract top upvoted content
        top_content = self._get_top_upvoted(posts, limit=10)
        
        # Step 3: Extract wish/hate patterns
        wish_patterns = self._extract_patterns(posts)
        
        # Step 4: Find competitor mentions
        competitor_mentions = self._find_competitor_mentions(posts, brand_name)
        
        # Step 5: LLM deep analysis
        llm_insights = {}
        if self.api_key and len(posts) >= 5:
            try:
                llm_insights = await self._analyze_with_llm(posts[:40], brand_name)
            except Exception as e:
                print(f"       [Reddit] LLM analysis error: {e}")
        
        return {
            "total_analyzed": len(posts),
            "sentiment_by_subreddit": subreddit_sentiment,
            "top_upvoted_content": top_content,
            "wish_patterns": wish_patterns.get("wishes", []),
            "hate_patterns": wish_patterns.get("hates", []),
            "need_patterns": wish_patterns.get("needs", []),
            "competitor_mentions": competitor_mentions,
            "overall_sentiment": self._calculate_overall_sentiment(posts),
            # LLM-enhanced insights
            "recurring_complaints": llm_insights.get("recurring_complaints", []),
            "recurring_praises": llm_insights.get("recurring_praises", []),
            "verbatim_quotes": llm_insights.get("verbatim_quotes", []),
            "pain_points": llm_insights.get("pain_points", []),
            "feature_requests": llm_insights.get("feature_requests", []),
            "buying_signals": llm_insights.get("buying_signals", []),
            "community_insights": llm_insights.get("community_insights", [])
        }
    
    def _analyze_by_subreddit(self, posts: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Analyze sentiment grouped by subreddit."""
        subreddits = {}
        
        for post in posts:
            # Extract subreddit from URL or raw_data
            url = post.get("source_url", "")
            subreddit = None
            
            match = re.search(r'reddit\.com/r/([^/]+)', url)
            if match:
                subreddit = match.group(1)
            
            if not subreddit:
                raw_data = post.get("raw_data", {})
                if isinstance(raw_data, dict):
                    subreddit = raw_data.get("subreddit", "unknown")
            
            if not subreddit:
                subreddit = "unknown"
            
            if subreddit not in subreddits:
                subreddits[subreddit] = {
                    "count": 0,
                    "positive": 0,
                    "negative": 0,
                    "neutral": 0,
                    "total_score": 0
                }
            
            subreddits[subreddit]["count"] += 1
            subreddits[subreddit]["total_score"] += post.get("likes", 0) or 0
            
            # Simple sentiment from content
            sentiment = self._simple_sentiment(post.get("content", ""))
            subreddits[subreddit][sentiment] += 1
        
        # Calculate percentages
        for sub, data in subreddits.items():
            total = data["count"] or 1
            data["positive_pct"] = round(data["positive"] / total * 100, 1)
            data["negative_pct"] = round(data["negative"] / total * 100, 1)
            data["avg_score"] = round(data["total_score"] / total, 1)
            data["sentiment"] = "Positive" if data["positive"] > data["negative"] else \
                               "Negative" if data["negative"] > data["positive"] else "Neutral"
        
        return subreddits
    
    def _get_top_upvoted(self, posts: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
        """Extract top upvoted posts/comments."""
        scored = []
        for post in posts:
            score = post.get("likes", 0) or 0
            scored.append({
                "content": post.get("content", "")[:500],
                "title": post.get("title", ""),
                "score": score,
                "author": post.get("author", ""),
                "source_url": post.get("source_url", "")
            })
        
        sorted_posts = sorted(scored, key=lambda x: x["score"], reverse=True)
        return sorted_posts[:limit]
    
    def _extract_patterns(self, posts: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Extract 'I wish', 'I hate', 'I need' patterns."""
        patterns = {
            "wishes": [],
            "hates": [],
            "needs": []
        }
        
        wish_regex = re.compile(r'(?:i\s+wish|wish\s+(?:they|it|there)\s+(?:would|could|had))[^.!?\n]{10,100}', re.IGNORECASE)
        hate_regex = re.compile(r'(?:i\s+hate|hate\s+(?:how|that|when))[^.!?\n]{10,100}', re.IGNORECASE)
        need_regex = re.compile(r'(?:i\s+need|we\s+need|really\s+need)[^.!?\n]{10,100}', re.IGNORECASE)
        
        for post in posts:
            content = post.get("content", "")
            score = post.get("likes", 0) or 0
            
            for match in wish_regex.findall(content):
                patterns["wishes"].append({"quote": match.strip(), "score": score})
            
            for match in hate_regex.findall(content):
                patterns["hates"].append({"quote": match.strip(), "score": score})
            
            for match in need_regex.findall(content):
                patterns["needs"].append({"quote": match.strip(), "score": score})
        
        # Sort by score and limit
        for key in patterns:
            patterns[key] = sorted(patterns[key], key=lambda x: x["score"], reverse=True)[:10]
        
        return patterns
    
    def _find_competitor_mentions(
        self, 
        posts: List[Dict[str, Any]], 
        brand_name: str
    ) -> List[Dict[str, Any]]:
        """Find mentions of competitors in context."""
        competitor_patterns = [
            r'(?:instead\s+of|switched\s+(?:to|from)|compared\s+to|better\s+than|worse\s+than)\s+(\w+)',
            r'(\w+)\s+(?:vs\.?|versus)\s+' + re.escape(brand_name) if brand_name else r'',
            r're.escape(brand_name)\s+(?:vs\.?|versus)\s+(\w+)' if brand_name else r'',
            r'alternative\s+(?:to|for)\s+(\w+)'
        ]
        
        mentions = Counter()
        contexts = {}
        
        for post in posts:
            content = post.get("content", "").lower()
            
            for pattern in competitor_patterns:
                if not pattern:
                    continue
                try:
                    for match in re.findall(pattern, content, re.IGNORECASE):
                        if isinstance(match, str) and len(match) > 2 and match.lower() != brand_name.lower():
                            mentions[match.lower()] += 1
                            if match.lower() not in contexts:
                                contexts[match.lower()] = content[:200]
                except:
                    continue
        
        result = []
        for name, count in mentions.most_common(10):
            if count >= 1:
                result.append({
                    "competitor": name,
                    "mention_count": count,
                    "sample_context": contexts.get(name, "")[:150]
                })
        
        return result
    
    def _calculate_overall_sentiment(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate overall sentiment distribution."""
        pos, neg, neu = 0, 0, 0
        
        for post in posts:
            sentiment = self._simple_sentiment(post.get("content", ""))
            if sentiment == "positive":
                pos += 1
            elif sentiment == "negative":
                neg += 1
            else:
                neu += 1
        
        total = len(posts) or 1
        return {
            "overall": "Positive" if pos > neg else "Negative" if neg > pos else "Neutral",
            "positive_pct": round(pos / total * 100, 1),
            "neutral_pct": round(neu / total * 100, 1),
            "negative_pct": round(neg / total * 100, 1)
        }
    
    def _simple_sentiment(self, text: str) -> str:
        """Simple rule-based sentiment."""
        text = text.lower()
        pos_words = ["love", "great", "amazing", "best", "perfect", "awesome", "excellent", "recommend", "helpful"]
        neg_words = ["hate", "bad", "terrible", "worst", "awful", "disappointed", "frustrated", "annoying", "scam"]
        
        pos_count = sum(1 for w in pos_words if w in text)
        neg_count = sum(1 for w in neg_words if w in text)
        
        if pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        return "neutral"
    
    async def _analyze_with_llm(
        self, 
        posts: List[Dict[str, Any]],
        brand_name: str
    ) -> Dict[str, Any]:
        """Use LLM for deep content analysis."""
        posts_text = []
        for p in posts[:25]:
            score = p.get("likes", 0) or 0
            content = p.get("content", "")[:400]
            posts_text.append(f"[{score} upvotes] {content}")
        
        posts_str = "\n---\n".join(posts_text)
        
        prompt = f"""Analyze these Reddit posts/comments{f' about {brand_name}' if brand_name else ''} for advertising insights.

REDDIT CONTENT:
{posts_str}

Return a JSON object with:

## COMPLAINTS & PRAISES
- "recurring_complaints": [list of 5-7 common complaints with frequency: "High/Medium/Low"]
- "recurring_praises": [list of 5-7 common praises with frequency]

## VERBATIM QUOTES (for ads)
- "verbatim_quotes": [5-7 powerful quotes that could be used in advertising, include the quote and why it's effective]

## PAIN POINTS
- "pain_points": [list of 5-7 specific problems users express, with severity: "Critical/Major/Minor"]

## OPPORTUNITIES
- "feature_requests": [list of features/improvements users want]
- "buying_signals": [list of phrases indicating purchase intent or consideration]

## COMMUNITY INSIGHTS
- "community_insights": [3-5 observations about this community's values, concerns, and language patterns]

## COMMUNITY DIALECT (slang, shorthand, insider phrases)
- "community_dialect": [5-10 slang terms, shorthand, insider phrases, or recurring references that appear across multiple posts. These are the words this audience uses WITH EACH OTHER — not marketing language. For each: the exact phrase, what it means, and how it could be used in ad copy to signal cultural proximity.]

## WEAK SIGNALS (low frequency, high creative potential)
- "weak_signals": [3-5 pain points or desires that appear only once or twice but have high hook potential. For each: the exact quote, why it has creative potential despite low frequency, and 1-2 hook variations built from it. A pain point mentioned once might be the angle nobody is running.]

Return ONLY valid JSON."""

        try:
            model = genai.GenerativeModel(self.model_id)
            response = await asyncio.wait_for(
                asyncio.to_thread(model.generate_content, prompt),
                timeout=60.0
            )
            return self._extract_json(response.text) or {}
        except Exception as e:
            print(f"       [Reddit LLM] Error: {e}")
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
