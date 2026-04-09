"""
YouTube Analyzer - Downloads and analyzes YouTube videos and comments.
Uses yt-dlp for video download and Gemini for analysis.
Extracts pain points and FAQs from comments.
"""

import os
import json
import re
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
import google.generativeai as genai

from ..config import settings


class YouTubeAnalyzer:
    """
    Downloads and analyzes YouTube videos and their comments.
    Extracts:
    - Video content analysis with Gemini
    - Comment sentiment analysis
    - Pain points from comments
    - FAQs from comment questions
    """
    
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if self.api_key:
            genai.configure(api_key=self.api_key)
        self.model_id = "models/gemini-3-flash-preview"
        self.output_dir = Path("output/youtube")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def download_video(
        self, 
        video_url: str, 
        video_id: Optional[str] = None
    ) -> Optional[Path]:
        """
        Download a YouTube video using yt-dlp.
        
        Args:
            video_url: YouTube video URL
            video_id: Optional video ID for naming
            
        Returns:
            Path to downloaded video file
        """
        if not video_id:
            # Extract video ID from URL
            match = re.search(r'(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})', video_url)
            video_id = match.group(1) if match else str(hash(video_url))[-8:]
        
        output_path = self.output_dir / f"yt_{video_id}.mp4"
        
        if output_path.exists():
            print(f"       [Download] Video already exists: {video_id}")
            return output_path
        
        try:
            print(f"       [Download] Downloading YouTube video: {video_id}...")
            result = subprocess.run([
                'yt-dlp',
                '-o', str(output_path),
                '--no-warnings',
                '-q',
                '--max-filesize', '100M',  # YouTube videos can be larger
                '-f', 'best[ext=mp4]/best',  # Prefer mp4
                video_url
            ], capture_output=True, text=True, timeout=180)  # 3 min timeout
            
            if output_path.exists():
                print(f"       [Download] Success: {video_id}")
                return output_path
            
            # Check for other extensions
            for ext in ['.mp4', '.webm', '.mkv']:
                alt_path = self.output_dir / f"yt_{video_id}{ext}"
                if alt_path.exists():
                    return alt_path
            
            print(f"       [Download] Failed: {video_id} (no file created)")
            return None
            
        except subprocess.TimeoutExpired:
            print(f"       [Download] Timeout: {video_id}")
            return None
        except Exception as e:
            print(f"       [Download] Error: {e}")
            return None
    
    async def analyze_video(
        self, 
        video_path: str,
        video_title: str = "",
        video_description: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze a YouTube video using Gemini.
        
        Args:
            video_path: Path to the video file
            video_title: Video title for context
            video_description: Video description for context
            
        Returns:
            Dict with analysis results
        """
        if not self.api_key:
            print("       [Analyze] Gemini API key not configured")
            return None
            
        if not os.path.exists(video_path):
            print(f"       [Analyze] Video not found: {video_path}")
            return None
        
        try:
            print(f"       [Analyze] Uploading video to Gemini...")
            video_file = genai.upload_file(video_path, mime_type="video/mp4")
            
            # Wait for processing
            wait_time = 0
            max_wait = 120  # 2 minutes for longer YouTube videos
            while video_file.state.name == "PROCESSING":
                if wait_time >= max_wait:
                    print(f"       [Analyze] Processing timeout")
                    return None
                await asyncio.sleep(3)
                wait_time += 3
                video_file = genai.get_file(video_file.name)
            
            if video_file.state.name != "ACTIVE":
                print(f"       [Analyze] Processing failed: {video_file.state.name}")
                return None
            
            prompt = self._build_video_analysis_prompt(video_title, video_description)
            
            print(f"       [Analyze] Analyzing with Gemini...")
            model = genai.GenerativeModel(self.model_id)
            
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(model.generate_content, [prompt, video_file]),
                    timeout=90.0
                )
            except asyncio.TimeoutError:
                print(f"       [Analyze] Gemini timeout")
                return None
            
            # Parse response
            result = self._extract_json(response.text)
            
            # Cleanup
            try:
                genai.delete_file(video_file.name)
            except:
                pass
            
            return result
            
        except Exception as e:
            print(f"       [Analyze] Error: {e}")
            return None
    
    def _build_video_analysis_prompt(self, title: str = "", description: str = "") -> str:
        """Build analysis prompt for YouTube video content."""
        context = ""
        if title:
            context += f"VIDEO TITLE: {title}\n"
        if description:
            context += f"DESCRIPTION: {description[:500]}\n"
        
        return f"""You are an expert YouTube content analyst. Analyze this video for advertising insights.

{context}

Return a JSON object with:

## 1. TRANSCRIPTION
- "transcription": Complete word-for-word transcription of ALL spoken words
- "key_takeaways": [list of 3-5 main points covered]

## 2. CONTENT ANALYSIS
- "video_type": "Review" | "Tutorial" | "Unboxing" | "Comparison" | "Testimonial" | "Educational" | "Entertainment" | "Vlog" | "Interview"
- "sentiment_toward_product": "Positive" | "Neutral" | "Negative" | "Mixed"
- "credibility_signals": [list: "Expert", "Genuine User", "Sponsored", "Has Proof", "Personal Experience"]
- "production_quality": "Low" | "Medium" | "High" | "Professional"

## 3. BRAND/PRODUCT MENTIONS
- "brand_mentions": [list of brands/products mentioned]
- "brand_sentiment": {{brand: sentiment}} for each mentioned brand
- "product_features_discussed": [list of specific features mentioned]
- "pros_mentioned": [list of positive points about the product]
- "cons_mentioned": [list of negative points about the product]

## 4. ADVERTISING INSIGHTS
- "pain_points_expressed": [list of problems/frustrations mentioned]
- "solutions_highlighted": [list of solutions/benefits shown]
- "target_audience": Who would find this video valuable
- "emotional_triggers": [list: "Trust", "FOMO", "Curiosity", "Fear", "Excitement", "Frustration"]
- "quotable_moments": [list of 3-5 memorable quotes that could work in ads]

## 5. COMPETITOR INSIGHTS
- "competitor_comparisons": [{{competitor: name, verdict: better/worse/equal}}]
- "switching_reasons": If mentioned, why did they switch to/from this product

## 6. CONTENT STRUCTURE
- "hook_effectiveness": 1-5 (how engaging is the opening)
- "call_to_action": Any CTAs mentioned
- "video_segments": [{{segment: name, duration_estimate: seconds}}]

## 7. AD CREATION POTENTIAL
- "clip_worthy_moments": [list of timestamped moments good for ad clips]
- "testimonial_potential": 1-5 (how usable is this as a testimonial)
- "key_message_for_ads": Single sentence that captures the main value

Return ONLY valid JSON. Be comprehensive."""
    
    async def analyze_comments(
        self,
        comments: List[Dict[str, Any]],
        brand_name: str = ""
    ) -> Dict[str, Any]:
        """
        Analyze YouTube comments for sentiment, pain points, and FAQs.
        
        Args:
            comments: List of comment dicts with 'content' field
            brand_name: Brand name for context
            
        Returns:
            Dict with aggregated comment insights
        """
        if not comments:
            return {"total_analyzed": 0}
        
        if not self.api_key:
            # Fallback to simple analysis without LLM
            return self._simple_comment_analysis(comments)
        
        # Prepare comments for analysis (limit to avoid token limits)
        comment_texts = [(c.get("content") or "")[:300] for c in comments[:100] if c]
        
        try:
            prompt = self._build_comment_analysis_prompt(comment_texts, brand_name)
            
            model = genai.GenerativeModel(self.model_id)
            response = await asyncio.wait_for(
                asyncio.to_thread(model.generate_content, prompt),
                timeout=60.0
            )
            
            result = self._extract_json(response.text)
            if result:
                result["total_analyzed"] = len(comments)
                return result
                
        except Exception as e:
            print(f"       [Comments] LLM analysis error: {e}")
        
        # Fallback to simple analysis
        return self._simple_comment_analysis(comments)
    
    def _build_comment_analysis_prompt(self, comments: List[str], brand_name: str) -> str:
        """Build prompt for YouTube comment analysis."""
        comments_text = "\n---\n".join(comments[:50])  # Limit for token efficiency
        
        return f"""Analyze these YouTube video comments{f' about {brand_name}' if brand_name else ''}.

COMMENTS:
{comments_text}

Return a JSON object with:

## SENTIMENT ANALYSIS
- "overall_sentiment": "Positive" | "Neutral" | "Negative" | "Mixed"
- "sentiment_breakdown": {{"positive": %, "neutral": %, "negative": %}}
- "sentiment_trend": Brief description of how sentiment changes through comments

## PAIN POINTS (Critical for Ad Targeting)
- "pain_points": [
    {{"pain_point": "description", "frequency": "High/Medium/Low", "verbatim_quote": "exact quote"}}
  ]
- "frustrations": [list of specific frustrations expressed]
- "unmet_needs": [list of needs not being addressed]

## FREQUENTLY ASKED QUESTIONS
- "faqs": [
    {{"question": "what users are asking", "frequency": "High/Medium/Low", "sample_phrasing": "how they ask it"}}
  ]
- "common_confusions": [list of things users are confused about]

## POSITIVE FEEDBACK
- "praised_features": [list of features users love]
- "testimonial_quotes": [list of quotes usable as testimonials]
- "success_stories": [brief summaries of positive experiences shared]

## COMPETITOR MENTIONS
- "competitor_mentions": [{{competitor: name, context: "what was said"}}]
- "comparison_requests": [list of "product vs X" type requests]

## ENGAGEMENT SIGNALS
- "high_engagement_topics": [topics that generate most replies]
- "controversial_topics": [topics that divide opinion]
- "feature_requests": [list of features users want]

## LANGUAGE PATTERNS (for Ad Copy)
- "common_phrases": [phrases used repeatedly]
- "emotional_language": [emotionally charged words/phrases]
- "persuasive_quotes": [quotes that could influence purchase decisions]

Return ONLY valid JSON."""
    
    def _simple_comment_analysis(self, comments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Simple rule-based comment analysis as fallback."""
        pain_keywords = ["problem", "issue", "frustrat", "annoying", "hate", "wish", "need", "want", "better", "worse"]
        question_pattern = re.compile(r'\?')
        positive_keywords = ["love", "great", "amazing", "best", "perfect", "excellent", "recommend"]
        negative_keywords = ["bad", "terrible", "waste", "scam", "avoid", "disappointed", "broken"]
        
        pain_points = []
        faqs = []
        positive = 0
        negative = 0
        neutral = 0
        
        for comment in comments:
            content = (comment.get("content") or "").lower()
            
            # Simple sentiment
            if any(kw in content for kw in positive_keywords):
                positive += 1
            elif any(kw in content for kw in negative_keywords):
                negative += 1
            else:
                neutral += 1
            
            # Pain points
            if any(kw in content for kw in pain_keywords):
                pain_points.append(content[:200])
            
            # Questions/FAQs
            if question_pattern.search(content):
                faqs.append(content[:200])
        
        total = len(comments)
        return {
            "total_analyzed": total,
            "overall_sentiment": "Positive" if positive > negative else "Negative" if negative > positive else "Neutral",
            "sentiment_breakdown": {
                "positive": round(positive / total * 100) if total else 0,
                "neutral": round(neutral / total * 100) if total else 0,
                "negative": round(negative / total * 100) if total else 0
            },
            "pain_points": [{"pain_point": p[:100], "verbatim_quote": p[:100]} for p in pain_points[:10]],
            "faqs": [{"question": q[:100], "sample_phrasing": q[:100]} for q in faqs[:10]],
            "analysis_method": "simple_rules"  # Indicate this was rule-based
        }
    
    async def analyze_youtube_content(
        self,
        video_url: str,
        comments: List[Dict[str, Any]],
        video_title: str = "",
        video_description: str = "",
        brand_name: str = "",
        analyze_video: bool = True
    ) -> Dict[str, Any]:
        """
        Full YouTube content analysis - video + comments.
        
        Args:
            video_url: YouTube video URL
            comments: List of scraped comments
            video_title: Video title
            video_description: Video description
            brand_name: Brand name for context
            analyze_video: Whether to download and analyze video (expensive)
            
        Returns:
            Combined analysis results
        """
        result = {
            "video_url": video_url,
            "video_title": video_title,
            "video_analysis": None,
            "comment_analysis": None
        }
        
        # Analyze comments (always do this - it's cheaper)
        if comments:
            print(f"    [YouTube] Analyzing {len(comments)} comments...")
            result["comment_analysis"] = await self.analyze_comments(comments, brand_name)
        
        # Video analysis (optional - more expensive)
        if analyze_video:
            video_path = await self.download_video(video_url)
            if video_path:
                result["video_analysis"] = await self.analyze_video(
                    str(video_path), video_title, video_description
                )
        
        return result
    
    async def aggregate_youtube_insights(
        self,
        analyzed_videos: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Aggregate insights from multiple YouTube video analyses.
        
        Args:
            analyzed_videos: List of analysis results from analyze_youtube_content
            
        Returns:
            Aggregated insights across all videos
        """
        all_pain_points = []
        all_faqs = []
        all_pros = []
        all_cons = []
        all_quotes = []
        sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}
        total_comments = 0
        
        for video in analyzed_videos:
            # From comment analysis
            comment_analysis = video.get("comment_analysis", {})
            if comment_analysis:
                total_comments += comment_analysis.get("total_analyzed", 0)
                
                # Aggregate pain points
                for pp in comment_analysis.get("pain_points", []):
                    if isinstance(pp, dict):
                        all_pain_points.append(pp.get("pain_point", ""))
                    else:
                        all_pain_points.append(str(pp))
                
                # Aggregate FAQs
                for faq in comment_analysis.get("faqs", []):
                    if isinstance(faq, dict):
                        all_faqs.append(faq.get("question", ""))
                    else:
                        all_faqs.append(str(faq))
                
                # Sentiment
                breakdown = comment_analysis.get("sentiment_breakdown", {})
                sentiment_counts["positive"] += breakdown.get("positive", 0)
                sentiment_counts["neutral"] += breakdown.get("neutral", 0)
                sentiment_counts["negative"] += breakdown.get("negative", 0)
            
            # From video analysis
            video_analysis = video.get("video_analysis", {})
            if video_analysis:
                all_pros.extend(video_analysis.get("pros_mentioned", []))
                all_cons.extend(video_analysis.get("cons_mentioned", []))
                all_quotes.extend(video_analysis.get("quotable_moments", []))
                all_pain_points.extend(video_analysis.get("pain_points_expressed", []))
        
        # Dedupe and count
        def count_items(items):
            counts = {}
            for item in items:
                if item:
                    item_lower = str(item).lower().strip()
                    counts[item_lower] = counts.get(item_lower, 0) + 1
            return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))
        
        num_videos = len(analyzed_videos) or 1
        
        return {
            "videos_analyzed": len(analyzed_videos),
            "total_comments_analyzed": total_comments,
            "overall_sentiment": {
                "positive": round(sentiment_counts["positive"] / num_videos),
                "neutral": round(sentiment_counts["neutral"] / num_videos),
                "negative": round(sentiment_counts["negative"] / num_videos)
            },
            "top_pain_points": list(count_items(all_pain_points).keys())[:10],
            "top_faqs": list(count_items(all_faqs).keys())[:10],
            "product_pros": list(set(all_pros))[:10],
            "product_cons": list(set(all_cons))[:10],
            "quotable_moments": all_quotes[:10]
        }
    
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
