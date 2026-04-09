"""
Twitter Analyzer - Deep analysis of Twitter/X content.
Extracts engagement patterns, top hooks, sentiment timeline, hashtags, and influencer mentions.
"""

import re
import json
import asyncio
from collections import Counter
from datetime import datetime
from typing import Dict, Any, List, Optional
import google.generativeai as genai

from ..config import settings


class TwitterAnalyzer:
    """
    Analyzes Twitter/X content for advertising insights.
    Extracts:
    - Top performing tweets by engagement
    - Common phrases and hooks that work
    - Sentiment timeline
    - Hashtags and topics
    - Influencer mentions
    """
    
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if self.api_key:
            genai.configure(api_key=self.api_key)
        self.model_id = "models/gemini-3-flash-preview"
    
    async def analyze_tweets(
        self,
        tweets: List[Dict[str, Any]],
        brand_name: str = ""
    ) -> Dict[str, Any]:
        """
        Deep analysis of scraped tweets.
        
        Args:
            tweets: List of tweet dicts with content, likes, etc.
            brand_name: Brand name for context
            
        Returns:
            Comprehensive Twitter insights
        """
        if not tweets:
            return {"total_analyzed": 0}
        
        # Step 1: Sort by engagement and get top performers
        top_tweets = self._get_top_performing_tweets(tweets, limit=10)
        
        # Step 2: Extract hashtags and topics
        hashtags, topics = self._extract_hashtags_and_topics(tweets)
        
        # Step 3: Find influencer mentions
        influencers = self._find_influencer_mentions(tweets)
        
        # Step 4: Simple sentiment analysis (rule-based fallback)
        sentiment_data = self._analyze_sentiment_timeline(tweets)
        
        # Step 5: LLM analysis for deep insights
        llm_insights = {}
        if self.api_key and len(tweets) >= 5:
            try:
                llm_insights = await self._analyze_with_llm(tweets[:50], brand_name)
            except Exception as e:
                print(f"       [Twitter] LLM analysis error: {e}")
        
        return {
            "total_analyzed": len(tweets),
            "top_performing_tweets": top_tweets,
            "hashtags": dict(hashtags.most_common(15)),
            "topics": dict(topics.most_common(10)),
            "influencer_mentions": influencers[:10],
            "sentiment": sentiment_data,
            "engagement_stats": self._calculate_engagement_stats(tweets),
            # LLM-enhanced insights
            "common_hooks": llm_insights.get("common_hooks", []),
            "winning_patterns": llm_insights.get("winning_patterns", []),
            "content_themes": llm_insights.get("content_themes", []),
            "quotable_tweets": llm_insights.get("quotable_tweets", []),
            "language_patterns": llm_insights.get("language_patterns", {}),
            "audience_insights": llm_insights.get("audience_insights", [])
        }
    
    def _get_top_performing_tweets(
        self, 
        tweets: List[Dict[str, Any]], 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Extract top performing tweets by engagement."""
        # Calculate engagement score for each tweet
        scored_tweets = []
        for tweet in tweets:
            likes = tweet.get("likes", 0) or 0
            retweets = tweet.get("shares", 0) or tweet.get("retweets", 0) or 0
            replies = tweet.get("comments_count", 0) or tweet.get("replies", 0) or 0
            
            # Engagement score: likes + 2*retweets + 1.5*replies
            score = likes + (2 * retweets) + (1.5 * replies)
            
            scored_tweets.append({
                "content": tweet.get("content", "")[:500],
                "author": tweet.get("author", ""),
                "likes": likes,
                "retweets": retweets,
                "replies": replies,
                "engagement_score": score,
                "source_url": tweet.get("source_url", ""),
                "date": tweet.get("date") or tweet.get("posted_at")
            })
        
        # Sort by engagement score
        sorted_tweets = sorted(scored_tweets, key=lambda x: x["engagement_score"], reverse=True)
        return sorted_tweets[:limit]
    
    def _extract_hashtags_and_topics(
        self, 
        tweets: List[Dict[str, Any]]
    ) -> tuple[Counter, Counter]:
        """Extract hashtags and identify topics from tweets."""
        hashtags = Counter()
        topics = Counter()
        
        # Topic keywords by category
        topic_patterns = {
            "pricing": ["price", "cost", "expensive", "cheap", "worth", "value", "$", "discount"],
            "quality": ["quality", "good", "bad", "great", "terrible", "amazing", "poor"],
            "support": ["support", "customer service", "help", "response", "team"],
            "features": ["feature", "update", "new", "missing", "needs", "wish"],
            "comparison": ["vs", "versus", "compared", "better than", "worse than", "alternative"],
            "recommendation": ["recommend", "suggest", "try", "use", "best", "favorite"],
            "problem": ["issue", "problem", "bug", "error", "broken", "doesn't work", "can't"],
            "praise": ["love", "amazing", "awesome", "perfect", "excellent", "10/10"]
        }
        
        for tweet in tweets:
            content = tweet.get("content", "").lower()
            
            # Extract hashtags
            found_hashtags = re.findall(r'#(\w+)', content)
            hashtags.update(found_hashtags)
            
            # Identify topics
            for topic, keywords in topic_patterns.items():
                if any(kw in content for kw in keywords):
                    topics[topic] += 1
        
        return hashtags, topics
    
    def _find_influencer_mentions(
        self, 
        tweets: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Find mentions of influencers and high-engagement accounts."""
        mentions = Counter()
        mention_details = {}
        
        for tweet in tweets:
            content = tweet.get("content", "")
            author = tweet.get("author", "")
            likes = tweet.get("likes", 0) or 0
            
            # Find @mentions
            found_mentions = re.findall(r'@(\w+)', content)
            for mention in found_mentions:
                mentions[mention] += 1
                if mention not in mention_details:
                    mention_details[mention] = {"total_engagement": 0, "contexts": []}
                mention_details[mention]["total_engagement"] += likes
                if len(mention_details[mention]["contexts"]) < 3:
                    mention_details[mention]["contexts"].append(content[:100])
            
            # Track high-engagement authors as potential influencers
            if likes > 100:
                mentions[author] += 1
                if author not in mention_details:
                    mention_details[author] = {"total_engagement": 0, "contexts": [], "is_author": True}
                mention_details[author]["total_engagement"] += likes
        
        # Return top influencers
        result = []
        for name, count in mentions.most_common(20):
            if name and count > 1:
                result.append({
                    "username": name,
                    "mention_count": count,
                    "total_engagement": mention_details.get(name, {}).get("total_engagement", 0),
                    "is_content_creator": mention_details.get(name, {}).get("is_author", False),
                    "sample_context": mention_details.get(name, {}).get("contexts", [])[:1]
                })
        
        return result
    
    def _analyze_sentiment_timeline(
        self, 
        tweets: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze sentiment distribution and trends."""
        positive_keywords = ["love", "great", "amazing", "best", "perfect", "excellent", "awesome", "recommend", "happy", "thanks"]
        negative_keywords = ["hate", "bad", "terrible", "worst", "awful", "disappointed", "angry", "frustrated", "scam", "avoid"]
        
        positive = 0
        negative = 0
        neutral = 0
        
        for tweet in tweets:
            content = tweet.get("content", "").lower()
            
            pos_count = sum(1 for kw in positive_keywords if kw in content)
            neg_count = sum(1 for kw in negative_keywords if kw in content)
            
            if pos_count > neg_count:
                positive += 1
            elif neg_count > pos_count:
                negative += 1
            else:
                neutral += 1
        
        total = len(tweets) or 1
        return {
            "overall": "Positive" if positive > negative else "Negative" if negative > positive else "Neutral",
            "breakdown": {
                "positive_pct": round(positive / total * 100, 1),
                "neutral_pct": round(neutral / total * 100, 1),
                "negative_pct": round(negative / total * 100, 1)
            },
            "positive_count": positive,
            "negative_count": negative,
            "neutral_count": neutral
        }
    
    def _calculate_engagement_stats(
        self, 
        tweets: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate engagement statistics."""
        likes = [t.get("likes", 0) or 0 for t in tweets]
        retweets = [t.get("shares", 0) or t.get("retweets", 0) or 0 for t in tweets]
        
        return {
            "total_likes": sum(likes),
            "avg_likes": round(sum(likes) / len(likes), 1) if likes else 0,
            "max_likes": max(likes) if likes else 0,
            "total_retweets": sum(retweets),
            "avg_retweets": round(sum(retweets) / len(retweets), 1) if retweets else 0,
            "max_retweets": max(retweets) if retweets else 0
        }
    
    async def _analyze_with_llm(
        self, 
        tweets: List[Dict[str, Any]],
        brand_name: str
    ) -> Dict[str, Any]:
        """Use LLM for deep content analysis."""
        # Prepare tweet content for analysis
        tweet_texts = []
        for t in tweets[:30]:  # Limit for token efficiency
            engagement = t.get("likes", 0) or 0
            content = t.get("content", "")[:300]
            tweet_texts.append(f"[{engagement} likes] {content}")
        
        tweets_str = "\n---\n".join(tweet_texts)
        
        prompt = f"""Analyze these tweets{f' about {brand_name}' if brand_name else ''} for advertising insights.

TWEETS:
{tweets_str}

Return a JSON object with:

## HOOKS & PATTERNS
- "common_hooks": [list of 5-7 opening patterns that get engagement, e.g., "Did you know...", "The truth about...", question formats]
- "winning_patterns": [list of 3-5 content patterns that perform well with brief explanations]

## THEMES & LANGUAGE
- "content_themes": [list of 5-7 recurring themes/topics being discussed]
- "language_patterns": {{
    "common_phrases": [3-5 frequently used phrases],
    "emotional_words": [words that trigger engagement],
    "call_to_actions": [CTAs used in tweets]
  }}

## QUOTABLE CONTENT
- "quotable_tweets": [3-5 tweets that would work well in ads, include the text and why it works]

## AUDIENCE INSIGHTS
- "audience_insights": [3-5 inferences about the audience based on how they talk, what they care about]

Return ONLY valid JSON."""

        try:
            model = genai.GenerativeModel(self.model_id)
            response = await asyncio.wait_for(
                asyncio.to_thread(model.generate_content, prompt),
                timeout=60.0
            )
            return self._extract_json(response.text) or {}
        except Exception as e:
            print(f"       [Twitter LLM] Error: {e}")
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
    
    async def aggregate_twitter_insights(
        self,
        analyses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate insights from multiple Twitter analyses."""
        all_hooks = []
        all_hashtags = Counter()
        all_topics = Counter()
        total_tweets = 0
        total_engagement = 0
        
        for analysis in analyses:
            total_tweets += analysis.get("total_analyzed", 0)
            all_hooks.extend(analysis.get("common_hooks", []))
            
            for tag, count in analysis.get("hashtags", {}).items():
                all_hashtags[tag] += count
            
            for topic, count in analysis.get("topics", {}).items():
                all_topics[topic] += count
            
            stats = analysis.get("engagement_stats", {})
            total_engagement += stats.get("total_likes", 0)
        
        return {
            "total_tweets_analyzed": total_tweets,
            "total_engagement": total_engagement,
            "top_hashtags": dict(all_hashtags.most_common(10)),
            "key_topics": dict(all_topics.most_common(8)),
            "winning_hooks": list(set(all_hooks))[:10]
        }
