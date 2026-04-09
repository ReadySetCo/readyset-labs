# -*- coding: utf-8 -*-
"""
Social Video Analyzer - Analyzes TikTok and YouTube videos with Gemini.
Downloads videos and extracts insights for ad creative development.
"""

import os
import asyncio
import tempfile
import httpx
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

import google.generativeai as genai

from ..config import settings


class SocialVideoAnalyzer:
    """Analyzes social media videos using Gemini for creative insights."""
    
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel("gemini-3-flash-preview")
        else:
            self.model = None
        
        self.temp_dir = Path(tempfile.gettempdir()) / "social_videos"
        self.temp_dir.mkdir(exist_ok=True)
        
        # Analysis limits
        self.max_videos_per_source = 20  # Max videos to analyze per source
        self.video_timeout = 60  # Seconds per video
    
    async def analyze_social_videos(
        self,
        scraped_data: List[Dict[str, Any]],
        brand_name: str = ""
    ) -> Dict[str, Any]:
        """
        Analyze videos from scraped social media data.
        
        Args:
            scraped_data: List of scraped items (may contain videos)
            brand_name: Brand name for context
            
        Returns:
            Dict with video insights and patterns
        """
        if not self.model:
            print("       [SocialVideoAnalyzer] No Gemini API key - skipping video analysis")
            return {"videos_analyzed": 0, "insights": []}
        
        # Extract videos from scraped data
        videos = []
        for item in scraped_data:
            if item.get("is_video") and item.get("video_url"):
                videos.append({
                    "url": item["video_url"],
                    "source": item.get("source_type", "unknown"),
                    "title": item.get("title", "")[:100],
                    "engagement": item.get("likes", 0) + item.get("comments_count", 0),
                    "author": item.get("author", "")
                })
        
        if not videos:
            print("       [SocialVideoAnalyzer] No videos with URLs found")
            return {"videos_analyzed": 0, "insights": []}
        
        # Sort by engagement and take top videos
        videos.sort(key=lambda x: x["engagement"], reverse=True)
        videos_to_analyze = videos[:self.max_videos_per_source]
        
        print(f"       [SocialVideoAnalyzer] Found {len(videos)} videos, analyzing top {len(videos_to_analyze)}...")
        
        analyzed = []
        for i, video in enumerate(videos_to_analyze):
            try:
                print(f"          [{i+1}/{len(videos_to_analyze)}] Analyzing {video['source']} video...")
                analysis = await self._analyze_single_video(video, brand_name)
                if analysis:
                    analyzed.append(analysis)
            except Exception as e:
                print(f"          [!] Video {i+1} failed: {str(e)[:50]}")
        
        # Aggregate insights
        aggregated = self._aggregate_video_insights(analyzed)
        aggregated["videos_analyzed"] = len(analyzed)
        
        print(f"       [SocialVideoAnalyzer] Analyzed {len(analyzed)} videos successfully")
        return aggregated
    
    async def _analyze_single_video(
        self,
        video: Dict[str, Any],
        brand_name: str
    ) -> Optional[Dict[str, Any]]:
        """Analyze a single video with Gemini."""
        # For TikTok/YouTube, we analyze based on URL + metadata
        # Full video download would be expensive, so we do lightweight analysis
        
        prompt = f"""Analyze this social media video for advertising insights.

VIDEO INFO:
- Source: {video['source']}
- Title/Caption: {video['title']}
- Author: {video['author']}
- Engagement: {video['engagement']} (likes + comments)
- URL: {video['url']}

BRAND CONTEXT: {brand_name or 'General DTC brand'}

Based on what's likely in this viral video, provide insights:

Return JSON:
{{
    "likely_format": "testimonial/transformation/tutorial/unboxing/challenge/other",
    "estimated_hook_type": "question/statement/shock/curiosity/problem",
    "target_audience": "Who this video likely appeals to",
    "content_pattern": "Brief description of the content pattern",
    "why_it_works": "Why this video likely performs well",
    "replicable_elements": ["Elements that could be replicated for ads"],
    "estimated_framework": "PAS/AIDA/BAB/Testimonial/How-To",
    "engagement_signals": "What the high engagement suggests"
}}"""

        try:
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.model.generate_content(prompt).text
                ),
                timeout=self.video_timeout
            )
            
            # Parse JSON from response
            import json
            import re
            
            # Try to extract JSON
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                analysis = json.loads(json_match.group())
                analysis["source"] = video["source"]
                analysis["video_url"] = video["url"]
                analysis["title"] = video["title"]
                analysis["engagement"] = video["engagement"]
                return analysis
            
        except asyncio.TimeoutError:
            print(f"          [!] Timeout analyzing video")
        except Exception as e:
            print(f"          [!] Analysis error: {str(e)[:50]}")
        
        return None
    
    def _aggregate_video_insights(
        self,
        analyzed_videos: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate insights from multiple video analyses."""
        if not analyzed_videos:
            return {"insights": [], "patterns": []}
        
        # Count formats, hooks, frameworks
        formats = {}
        hooks = {}
        frameworks = {}
        all_elements = []
        
        for video in analyzed_videos:
            fmt = video.get("likely_format", "unknown")
            formats[fmt] = formats.get(fmt, 0) + 1
            
            hook = video.get("estimated_hook_type", "unknown")
            hooks[hook] = hooks.get(hook, 0) + 1
            
            fw = video.get("estimated_framework", "unknown")
            frameworks[fw] = frameworks.get(fw, 0) + 1
            
            elements = video.get("replicable_elements", [])
            if isinstance(elements, list):
                all_elements.extend(elements)
        
        # Find top patterns
        top_format = max(formats, key=formats.get) if formats else "unknown"
        top_hook = max(hooks, key=hooks.get) if hooks else "unknown"
        top_framework = max(frameworks, key=frameworks.get) if frameworks else "unknown"
        
        # Dedupe elements
        unique_elements = list(set(all_elements))[:10]
        
        return {
            "insights": analyzed_videos,
            "top_patterns": {
                "format": top_format,
                "hook_type": top_hook,
                "framework": top_framework
            },
            "replicable_elements": unique_elements,
            "format_distribution": formats,
            "hook_distribution": hooks,
            "framework_distribution": frameworks
        }
    
    async def analyze_youtube_comments(
        self,
        comments: List[Dict[str, Any]],
        brand_name: str = ""
    ) -> Dict[str, Any]:
        """Analyze YouTube comments for pain points and FAQs."""
        if not self.model or not comments:
            return {"pain_points": [], "faqs": [], "sentiment": "neutral"}
        
        # Take top comments by engagement
        sorted_comments = sorted(
            comments, 
            key=lambda x: x.get("likes", 0), 
            reverse=True
        )[:50]
        
        comment_texts = [c.get("content", "")[:200] for c in sorted_comments if c.get("content")]
        
        if not comment_texts:
            return {"pain_points": [], "faqs": [], "sentiment": "neutral"}
        
        prompt = f"""Analyze these YouTube comments for customer insights.

BRAND: {brand_name or 'Unknown brand'}

COMMENTS:
{chr(10).join(['- ' + c for c in comment_texts[:30]])}

Extract insights as JSON:
{{
    "pain_points": ["Pain points mentioned in comments"],
    "faqs": ["Common questions asked"],
    "sentiment": "positive/negative/mixed/neutral",
    "verbatim_quotes": ["Useful verbatim quotes for ads"],
    "objections": ["Objections or concerns raised"],
    "praise_points": ["Things people love"]
}}"""

        try:
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.model.generate_content(prompt).text
                ),
                timeout=60
            )
            
            import json
            import re
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                return json.loads(json_match.group())
                
        except Exception as e:
            print(f"       [!] Comment analysis error: {e}")
        
        return {"pain_points": [], "faqs": [], "sentiment": "neutral"}
